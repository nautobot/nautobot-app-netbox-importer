"""Generic Field Importers definitions for Nautobot Importer."""
from typing import Any
from typing import Optional

from .base import EMPTY_VALUES
from .nautobot import DiffSyncBaseModel
from .source import FieldName
from .source import RecordData
from .source import SourceAdapter
from .source import SourceField
from .source import SourceFieldDefinition


def role(adapter: SourceAdapter, source_content_type: str) -> SourceFieldDefinition:
    """Create a role field definition.

    Use, when there is a different source role content type, that should be mapped to Nautobot "extras.role".
    Creates a new wrapper for the `source_content_type`, if it does not exist.
    """
    if source_content_type in adapter.wrappers:
        role_wrapper = adapter.wrappers[source_content_type]
    else:
        role_wrapper = adapter.configure_model(
            source_content_type,
            nautobot_content_type="extras.role",
            fields={"color": "color", "content_types": "content_types"},
        )

    def definition(field: SourceField) -> None:
        field.set_nautobot_field("role")

        def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(field.name, None)
            if value in EMPTY_VALUES:
                return

            uuid = role_wrapper.get_pk_from_uid(value)  # type: ignore
            setattr(target, field.nautobot.name, uuid)
            role_wrapper.add_reference(uuid, field.wrapper)

        field.set_importer(importer)

    return definition


def source_constant(value: Any, nautobot_name: Optional[FieldName] = None) -> SourceFieldDefinition:
    """Create a source constant field definition.

    Use, to pre-fill constant value for the field. Calls default importer after setting the value.
    """

    def definition(field: SourceField) -> None:
        field.set_default_importer(nautobot_name or field.name)
        original_importer = field.importer
        if not original_importer:
            return

        def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            source[field.name] = value
            original_importer(source, target)

        field.set_importer(importer, override=True)

    return definition


def constant(value: Any, nautobot_name: Optional[FieldName] = None) -> SourceFieldDefinition:
    """Create a constant field definition.

    Use to fill target constant value for the field.
    """

    def definition(field: SourceField) -> None:
        field.set_nautobot_field(nautobot_name or field.name)

        def importer(_: RecordData, target: DiffSyncBaseModel) -> None:
            setattr(target, field.nautobot.name, value)

        field.set_importer(importer)

    return definition


def pass_through(nautobot_name: Optional[FieldName] = None) -> SourceFieldDefinition:
    """Create a pass-through field definition.

    Use to pass-through the value from source to target without changing it by the default importer.
    """

    def definition(field: SourceField) -> None:
        field.set_nautobot_field(nautobot_name or field.name)

        def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(field.name, None)
            if value:
                setattr(target, field.nautobot.name, value)

        field.set_importer(importer)

    return definition


def force(nautobot_name: Optional[FieldName] = None) -> SourceFieldDefinition:
    """Mark Nautobot field as forced.

    Use to force the field to be saved in Nautobot in the second save attempt after the initial save to override the
    default value set by Nautobot.
    """

    def definition(field: SourceField) -> None:
        field.set_default_importer(nautobot_name or field.name)
        field.nautobot.force = True

    return definition


def disable(reason: str) -> SourceFieldDefinition:
    """Disable the field.

    Use to disable the field import with the given reason.
    """

    def definition(field: SourceField) -> None:
        field.disable(reason)

    return definition
