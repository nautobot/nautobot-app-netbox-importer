"""Generic Field Importers definitions for Nautobot Importer."""

from typing import Any
from typing import Dict
from typing import Optional
from uuid import UUID

from .base import EMPTY_VALUES
from .base import ContentTypeStr
from .base import Uid
from .nautobot import DiffSyncBaseModel
from .source import FieldName
from .source import ImporterPass
from .source import InvalidChoiceValueIssue
from .source import PreImportResult
from .source import RecordData
from .source import SourceAdapter
from .source import SourceContentType
from .source import SourceField
from .source import SourceFieldDefinition
from .source import SourceFieldImporterFallback
from .source import SourceFieldImporterIssue


def default(default_value: Any, nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a default field definition.

    Use to set a default value for the field, if there is no value in the source data.
    """

    def define_default(field: SourceField) -> None:
        field.set_importer(nautobot_name=nautobot_name)
        field.default_value = default_value

    return define_default


def fallback(
    value: Any = None,
    callback: Optional[SourceFieldImporterFallback] = None,
    nautobot_name: FieldName = "",
) -> SourceFieldDefinition:
    """Create a fallback field definition.

    Use to set a fallback value or callback for the field, if there is an error during the default importer.
    """
    if (value is None) == (callback is None):
        raise ValueError("Exactly one of `value` or `callback` must be set.")

    def define_fallback(field: SourceField) -> None:
        original_importer = field.set_importer(nautobot_name=nautobot_name)
        if not original_importer:
            return

        def fallback_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            try:
                original_importer(source, target)
            except Exception as error:
                if callback:
                    callback(field, source, target, error)
                if value:
                    field.set_nautobot_value(target, value)
                    if isinstance(error, InvalidChoiceValueIssue):
                        raise InvalidChoiceValueIssue(field, field.get_source_value(source), value) from error
                    raise SourceFieldImporterIssue(
                        f"Failed to import field: {error} | Fallback value: {value}",
                        field,
                    ) from error
                raise

        field.set_importer(fallback_importer, override=True)

    return define_fallback


def relation(related_source: SourceContentType, nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a relation field definition.

    Use when there is a different source content type that should be mapped to Nautobot relation.
    """

    def define_relation(field: SourceField) -> None:
        field.set_nautobot_field(nautobot_name)
        field.set_relation_importer(field.wrapper.adapter.get_or_create_wrapper(related_source))

    return define_relation


_ROLE_NAME_TO_UID_CACHE: Dict[str, Uid] = {}


def role(
    adapter: SourceAdapter,
    source_content_type: ContentTypeStr,
    nautobot_name: FieldName = "role",
) -> SourceFieldDefinition:
    """Create a role field definition.

    Use, when there is a different source role content type that should be mapped to the Nautobot "extras.Role".
    It creates a new wrapper for the `source_content_type` if it does not already exist.

    It covers multiple options for how roles can be referenced in the source data:
        - by primary key
        - by role name

    It also handles the scenario where the same role names are used in different role models,
    e.g., RackRole with `name = "Network"` and DeviceRole with `name = "Network"` to avoid duplicates.
    """

    def cache_roles(source: RecordData, importer_pass: ImporterPass) -> PreImportResult:
        if importer_pass == ImporterPass.DEFINE_STRUCTURE:
            name = source.get("name", "").capitalize()
            if not name:
                raise ValueError("Role name is required")
            uid = _ROLE_NAME_TO_UID_CACHE.get(name, None)
            nautobot_uid = role_wrapper.cache_record_uids(source, uid)
            if not uid:
                _ROLE_NAME_TO_UID_CACHE[name] = nautobot_uid

        return PreImportResult.USE_RECORD

    role_wrapper = adapter.configure_model(
        source_content_type,
        nautobot_content_type="extras.role",
        pre_import=cache_roles,
        identifiers=("name",),
        fields={
            # Include color to allow setting the default Nautobot value, import fails without it.
            "color": "color",
        },
    )

    def define_role(field: SourceField) -> None:
        def role_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = field.get_source_value(source)
            if value in EMPTY_VALUES:
                return

            if isinstance(value, (int, UUID)):
                # Role is referenced by primary key
                uid = role_wrapper.get_pk_from_uid(value)
            elif isinstance(value, str):
                # Role is referenced by name
                value = value.capitalize()
                if value in _ROLE_NAME_TO_UID_CACHE:
                    uid = _ROLE_NAME_TO_UID_CACHE[value]
                else:
                    uid = role_wrapper.get_pk_from_identifiers([value])
                    _ROLE_NAME_TO_UID_CACHE[value] = uid
                role_wrapper.import_record({"id": uid, "name": value})
            else:
                raise ValueError(f"Invalid role value {value}")

            field.set_nautobot_value(target, uid)
            field.wrapper.add_reference(role_wrapper, uid)

        field.set_importer(role_importer, nautobot_name)

    return define_role


def source_constant(value: Any, nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a source constant field definition.

    Use, to pre-fill constant value for the field. Calls default importer after setting the value.
    """

    def define_source_constant(field: SourceField) -> None:
        original_importer = field.set_importer(nautobot_name=nautobot_name)
        if not original_importer:
            return

        def source_constant_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            source[field.name] = value
            original_importer(source, target)

        field.set_importer(source_constant_importer, override=True)

    return define_source_constant


def constant(value: Any, nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a constant field definition.

    Use to fill target constant value for the field.
    """

    def define_constant(field: SourceField) -> None:
        def constant_importer(_: RecordData, target: DiffSyncBaseModel) -> None:
            field.set_nautobot_value(target, value)

        field.set_importer(constant_importer, nautobot_name)

    return define_constant


def pass_through(nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a pass-through field definition.

    Use to pass-through the value from source to target without changing it by the default importer.
    """

    def define_passthrough(field: SourceField) -> None:
        def pass_through_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(field.name, None)
            field.set_nautobot_value(target, value)

        field.set_importer(pass_through_importer, nautobot_name)

    return define_passthrough


def force(nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Mark Nautobot field as forced.

    Use to force the field to be saved in Nautobot in the second save attempt after the initial save to override the
    default value set by Nautobot.
    """

    def define_force(field: SourceField) -> None:
        field.set_importer(nautobot_name=nautobot_name)
        field.nautobot.force = True

    return define_force


def disable(reason: str) -> SourceFieldDefinition:
    """Disable the field.

    Use to disable the field import with the given reason.
    """

    def define_disable(field: SourceField) -> None:
        field.disable(reason)

    return define_disable
