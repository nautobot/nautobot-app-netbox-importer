"""NetBox to Nautobot Base Models Mapping."""
import json

from nautobot_netbox_importer.generator import EMPTY_VALUES
from nautobot_netbox_importer.generator import RecordData
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField


def _define_choices(field: SourceField) -> None:
    choices_wrapper = field.wrapper.adapter.get_or_create_wrapper("extras.customfieldchoice")

    def importer(source: RecordData, target: RecordData) -> None:
        choices = source.get(field.name, None)
        if choices in EMPTY_VALUES:
            return
        if isinstance(choices, str):
            choices = json.loads(choices)
        if choices in EMPTY_VALUES:
            return

        if not isinstance(choices, list):
            raise ValueError(f"Choices must be a list of strings, got {type(choices)}")

        for choice in choices:
            choices_wrapper.import_record(
                {
                    "id": choice,
                    "custom_field": target["id"],
                    "value": choice,
                },
            )

    field.set_importer(importer)


def _define_tagged_object(field: SourceField) -> None:
    field.set_nautobot_field(field.name)

    def importer(source: RecordData, target: RecordData) -> None:
        content_type = source.get("content_type", None)
        object_id = source.get(field.name, None)
        if not object_id or not content_type:
            target[field.nautobot.name] = None
            return

        related_wrapper = field.wrapper.adapter.get_or_create_wrapper(content_type)
        result = related_wrapper.get_pk_from_uid(object_id)
        target[field.nautobot.name] = result
        related_wrapper.add_reference(result, field.wrapper)

    field.set_importer(importer)


def setup_base(adapter: SourceAdapter) -> None:
    """Map NetBox base models to Nautobot."""
    adapter.disable_model("contenttypes.contenttype", "Nautobot has own content types; Handled via migrations")
    adapter.disable_model("sessions.session", "Nautobot has own sessions, sessions should never cross apps")
    adapter.disable_model("admin.logentry", "Not directly used in Nautobot")
    adapter.disable_model("users.userconfig", "May not have a 1 to 1 translation to Nautobot")
    adapter.disable_model("auth.permission", "Handled via a Nautobot model and may not be a 1 to 1")

    adapter.configure_model(
        "extras.status",
        identifiers=["name"],
        default_reference={
            "name": "Unknown",
            "content_types": [],
        },
    )
    adapter.configure_model("extras.role")
    adapter.configure_model(
        "extras.customfield",
        fields={
            "name": "key",
            "choices": _define_choices,
        },
    )
    adapter.configure_model(
        "extras.customfieldchoice",
        fields={
            "custom_field": "custom_field",
            "value": "value",
        },
    )
    adapter.configure_model(
        "extras.taggeditem",
        fields={
            "object_id": _define_tagged_object,
        },
    )
    adapter.configure_model(
        "auth.user",
        nautobot_content_type="users.user",
        identifiers=["username"],
        fields={
            "last_login": None,  # Should not be attempted to migrated
            "password": None,  # Should not be attempted to migrated
            "user_permissions": None,
        },
    )
    adapter.configure_model(
        "auth.group",
        identifiers=["name"],
        fields={
            "permissions": None,
        },
    )
    adapter.configure_model(
        "tenancy.tenant",
        fields={
            "group": "tenant_group",
        },
    )
