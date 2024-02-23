"""Generic Field Importers definitions for Nautobot Importer."""

from typing import Any
from typing import Optional

from .base import EMPTY_VALUES
from .base import ContentTypeStr
from .nautobot import DiffSyncBaseModel
from .source import FieldName
from .source import InvalidChoiceValueIssue
from .source import RecordData
from .source import SourceAdapter
from .source import SourceContentType
from .source import SourceField
from .source import SourceFieldDefinition
from .source import SourceFieldImporterFallback
from .source import SourceFieldImporterIssue


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
                    setattr(target, field.nautobot.name, value)
                    if isinstance(error, InvalidChoiceValueIssue):
                        raise InvalidChoiceValueIssue(field, field.get_source_value(source), value) from error
                    raise SourceFieldImporterIssue(
                        f"Failed to import field: {error} | Fallback value: {value}",
                        field,
                    ) from error
                raise

        field.set_importer(fallback_importer, override=True)

    return define_fallback


def truncate_to_integer(nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a truncate integer field definition.

    Use to truncate the value to an integer before importing it to Nautobot.
    """

    def define_truncate_to_integer(field: SourceField) -> None:
        def truncate_to_integer_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = field.get_source_value(source)
            if value in EMPTY_VALUES:
                return

            if not isinstance(value, int):
                value = int(float(value))

            setattr(target, field.nautobot.name, value)

        field.set_importer(truncate_to_integer_importer, nautobot_name)

    return define_truncate_to_integer


def relation(related_source: SourceContentType, nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a relation field definition.

    Use when there is a different source content type that should be mapped to Nautobot relation.
    """

    def define_relation(field: SourceField) -> None:
        field.set_nautobot_field(nautobot_name)
        field.set_relation_importer(field.wrapper.adapter.get_or_create_wrapper(related_source))

    return define_relation


def role(adapter: SourceAdapter, source_content_type: ContentTypeStr) -> SourceFieldDefinition:
    """Create a role field definition.

    Use, when there is a different source role content type, that should be mapped to Nautobot "extras.role".
    Creates a new wrapper for the `source_content_type`, if it does not exist.
    """
    role_wrapper = adapter.configure_model(
        source_content_type,
        nautobot_content_type="extras.role",
        fields={
            # Include color to allow setting the default Nautobot value, import fails without it.
            "color": "color",
        },
    )

    return relation(role_wrapper, "role")


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
            setattr(target, field.nautobot.name, value)

        field.set_importer(constant_importer, nautobot_name)

    return define_constant


def pass_through(nautobot_name: FieldName = "") -> SourceFieldDefinition:
    """Create a pass-through field definition.

    Use to pass-through the value from source to target without changing it by the default importer.
    """

    def define_passthrough(field: SourceField) -> None:
        def pass_through_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(field.name, None)
            if value:
                setattr(target, field.nautobot.name, value)

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
