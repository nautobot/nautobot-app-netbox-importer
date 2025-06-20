"""Generic Field Importers definitions for Nautobot Importer."""

from collections import defaultdict
from typing import Any, Dict, Optional
from uuid import UUID

from nautobot_netbox_importer.generator.base import (
    EMPTY_VALUES,
    INTERNAL_INTEGER_FIELDS,
    INTERNAL_STRING_FIELDS,
    ContentTypeStr,
    Uid,
)
from nautobot_netbox_importer.generator.nautobot import DiffSyncBaseModel
from nautobot_netbox_importer.generator.source import (
    FallbackValueIssue,
    FieldName,
    ImporterPass,
    InternalFieldType,
    InvalidChoiceValueIssue,
    PreImportRecordResult,
    RecordData,
    SourceAdapter,
    SourceContentType,
    SourceField,
    SourceFieldDefinition,
    SourceFieldImporterFallback,
    SourceModelWrapper,
)

_AUTO_INCREMENTS = defaultdict(int)


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
                    raise FallbackValueIssue(field, value) from error
                raise

        field.set_importer(fallback_importer, override=True)

    return define_fallback


def relation(related_source: SourceContentType, nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a relation field definition.

    Use when there is a different source content type that should be mapped to Nautobot relation.
    """

    def define_relation(field: SourceField) -> None:
        field.set_nautobot_field(nautobot_name)
        if field.nautobot.internal_type == InternalFieldType.MANY_TO_MANY_FIELD:
            field.set_m2m_importer(related_source)
        else:
            field.set_relation_importer(related_source)

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

    def cache_roles(source: RecordData, importer_pass: ImporterPass) -> PreImportRecordResult:
        if importer_pass == ImporterPass.DEFINE_STRUCTURE:
            name = source.get("name", "").capitalize()
            if not name:
                raise ValueError("Role name is required")
            uid = _ROLE_NAME_TO_UID_CACHE.get(name, None)
            nautobot_uid = role_wrapper.cache_record_uids(source, uid)
            if not uid:
                _ROLE_NAME_TO_UID_CACHE[name] = nautobot_uid

        return PreImportRecordResult.USE_RECORD

    role_wrapper = adapter.configure_model(
        source_content_type,
        nautobot_content_type="extras.role",
        pre_import_record=cache_roles,
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


def constant(
    value: Any,
    nautobot_name: FieldName = "",
    reference: Optional[SourceModelWrapper] = None,
) -> SourceFieldDefinition:
    """Create a constant field definition for target record.

    Map a constant value to a specific field in the target model.

    Args:
        value: Constant value to be set in the target field.
        nautobot_name: Optional name for the Nautobot field.
        reference: Optional source model wrapper for reference tracking.

    Returns:
        A function that defines a constant field importer.
    """

    def define_constant(field: SourceField) -> None:
        def constant_importer(_: RecordData, target: DiffSyncBaseModel) -> None:
            field.set_nautobot_value(target, value)
            if reference:
                field.wrapper.add_reference(reference, value)

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


def auto_increment(prefix="", nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Auto increment field value, if the source value is empty.

    Use to set the field value to a unique auto incremented value.

    Supports string and integer fields.

    Args:
        prefix (str): Optional prefix to be added to the auto incremented value. Valid for string fields only.
        nautobot_name (str): Optional name for the Nautobot field.

    Returns:
        A function that defines an auto increment field importer.
    """

    def define_auto_increment(field: SourceField) -> None:
        key = f"{field.wrapper.content_type}.{field.name}_prefix"

        original_importer = field.set_importer(nautobot_name=nautobot_name)
        if not original_importer:
            return

        if field.nautobot.internal_type in INTERNAL_INTEGER_FIELDS:
            if prefix:
                raise ValueError("Prefix is not supported for integer fields")
        elif field.nautobot.internal_type not in INTERNAL_STRING_FIELDS:
            raise ValueError(f"Field {field.name} is not a string or integer field")

        def auto_increment_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = field.get_source_value(source)
            if value not in EMPTY_VALUES:
                original_importer(source, target)
                return

            _AUTO_INCREMENTS[key] += 1
            value = _AUTO_INCREMENTS[key]
            if field.nautobot.internal_type in INTERNAL_STRING_FIELDS:
                value = f"{prefix}{value}"

            field.set_nautobot_value(target, value)

        field.set_importer(auto_increment_importer, nautobot_name=nautobot_name, override=True)

    return define_auto_increment
