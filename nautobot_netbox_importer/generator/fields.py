"""Generic Field Importers definitions for Nautobot Importer."""

from typing import Any
from typing import Optional

from .base import ContentTypeStr
from .nautobot import DiffSyncBaseModel
from .source import FieldName
from .source import RecordData
from .source import SourceAdapter
from .source import SourceContentType
from .source import SourceField
from .source import SourceFieldDefinition


def relation(related_source: SourceContentType, nautobot_field_name: FieldName = "") -> SourceFieldDefinition:
    """Create a relation field definition.

    Use when there is a different source content type that should be mapped to Nautobot relation.
    """

    def define_relation(field: SourceField) -> None:
        field.set_nautobot_field(nautobot_field_name or field.name)
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


def source_constant(value: Any, nautobot_name: Optional[FieldName] = None) -> SourceFieldDefinition:
    """Create a source constant field definition.

    Use, to pre-fill constant value for the field. Calls default importer after setting the value.
    """

    def define_source_constant(field: SourceField) -> None:
        field.set_default_importer(nautobot_name or field.name)
        original_importer = field.importer
        if not original_importer:
            return

        def source_constant_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            source[field.name] = value
            original_importer(source, target)

        field.set_importer(source_constant_importer, override=True)

    return define_source_constant


def constant(value: Any, nautobot_name: Optional[FieldName] = None) -> SourceFieldDefinition:
    """Create a constant field definition.

    Use to fill target constant value for the field.
    """

    def define_constant(field: SourceField) -> None:
        field.set_nautobot_field(nautobot_name or field.name)

        def constant_importer(_: RecordData, target: DiffSyncBaseModel) -> None:
            setattr(target, field.nautobot.name, value)

        field.set_importer(constant_importer)

    return define_constant


def pass_through(nautobot_name: Optional[FieldName] = None) -> SourceFieldDefinition:
    """Create a pass-through field definition.

    Use to pass-through the value from source to target without changing it by the default importer.
    """

    def define_passthrough(field: SourceField) -> None:
        field.set_nautobot_field(nautobot_name or field.name)

        def pass_through_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(field.name, None)
            if value:
                setattr(target, field.nautobot.name, value)

        field.set_importer(pass_through_importer)

    return define_passthrough


def force(nautobot_name: Optional[FieldName] = None) -> SourceFieldDefinition:
    """Mark Nautobot field as forced.

    Use to force the field to be saved in Nautobot in the second save attempt after the initial save to override the
    default value set by Nautobot.
    """

    def define_force(field: SourceField) -> None:
        field.set_default_importer(nautobot_name or field.name)
        field.nautobot.force = True

    return define_force


def disable(reason: str) -> SourceFieldDefinition:
    """Disable the field.

    Use to disable the field import with the given reason.
    """

    def define_disable(field: SourceField) -> None:
        field.disable(reason)

    return define_disable
