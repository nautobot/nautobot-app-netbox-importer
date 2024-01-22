"""NetBox to Nautobot Base Models Mapping."""
import json

from diffsync.enum import DiffSyncModelFlags

from nautobot_netbox_importer.generator import EMPTY_VALUES
from nautobot_netbox_importer.generator import DiffSyncBaseModel
from nautobot_netbox_importer.generator import RecordData
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import fields


def _define_choices(field: SourceField) -> None:
    choices_wrapper = field.wrapper.adapter.get_or_create_wrapper("extras.customfieldchoice")

    def choices_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
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
                    "custom_field": getattr(target, "id"),
                    "value": choice,
                },
            )

    field.set_importer(choices_importer)


def _define_tagged_object(field: SourceField) -> None:
    wrapper = field.wrapper
    adapter = wrapper.adapter
    tag_wrapper = adapter.get_or_create_wrapper("extras.tag")

    def tagged_object_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        object_id = source.get(field.name, None)
        if not object_id:
            return

        tag = source.get(tag_field.name, None)
        content_type = source.get(content_type_field.name, None)
        if not tag or not content_type:
            raise ValueError(f"Missing content_type or tag for tagged object {object_id}")

        tag_uuid = tag_wrapper.get_pk_from_uid(tag)
        related_wrapper = adapter.get_or_create_wrapper(content_type)
        result = related_wrapper.get_pk_from_uid(object_id)
        setattr(target, field.nautobot.name, result)
        setattr(target, tag_field.nautobot.name, tag_uuid)
        setattr(target, content_type_field.nautobot.name, related_wrapper.nautobot.content_type_instance.pk)
        related_wrapper.add_reference(tag_wrapper, tag_uuid)

    field.set_nautobot_field(field.name)
    field.set_importer(tagged_object_importer)
    tag_field = field.handle_sibling("tag", "tag")
    content_type_field = field.handle_sibling("content_type", "content_type")


def _setup_content_types(adapter: SourceAdapter) -> None:
    """Map NetBox content types to Nautobot.

    Automatically calculate NetBox content type IDs, if not provided, based on the order of the content types.
    """
    netbox = {"id": 0}

    def define_app_label(field: SourceField) -> None:
        field.set_nautobot_field(field.name)

        def content_types_mapper_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            app_label = source["app_label"]
            model = source["model"]
            netbox["id"] += 1
            uid = source.get("id", None)
            if uid:
                if uid != netbox["id"]:
                    raise ValueError(f"Content type id mismatch: {uid} != {netbox['id']}")
            else:
                uid = netbox["id"]

            wrapper = adapter.get_or_create_wrapper(f"{app_label}.{model}")
            adapter.content_type_ids_mapping[uid] = wrapper
            setattr(target, field.nautobot.name, app_label)

        field.set_importer(content_types_mapper_importer)

    adapter.configure_model(
        "contenttypes.ContentType",
        identifiers=["app_label", "model"],
        flags=DiffSyncModelFlags.IGNORE,
        nautobot_flags=DiffSyncModelFlags.IGNORE,
        fields={
            "app_label": define_app_label,
        },
    )


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox base models to Nautobot."""
    adapter.disable_model("sessions.session", "Nautobot has own sessions, sessions should never cross apps.")
    adapter.disable_model("admin.logentry", "Not directly used in Nautobot.")
    adapter.disable_model("users.userconfig", "May not have a 1 to 1 translation to Nautobot.")
    adapter.disable_model("auth.permission", "Handled via a Nautobot model and may not be a 1 to 1.")

    _setup_content_types(adapter)

    adapter.configure_model(
        "extras.Status",
        identifiers=["name"],
        default_reference={
            "name": "Unknown",
        },
    )
    adapter.configure_model("extras.role")
    adapter.configure_model(
        "extras.CustomField",
        fields={
            "name": "key",
            "choices": _define_choices,
            "choice_set": _define_choices,
        },
    )
    adapter.configure_model(
        "extras.CustomFieldChoice",
        fields={
            "custom_field": "custom_field",
            "value": "value",
        },
    )
    adapter.configure_model(
        "extras.TaggedItem",
        fields={
            "object_id": _define_tagged_object,
        },
    )
    adapter.configure_model(
        "auth.User",
        nautobot_content_type="users.User",
        identifiers=["username"],
        fields={
            "last_login": fields.disable("Should not be attempted to migrate"),
            "password": fields.disable("Should not be attempted to migrate"),
            "user_permissions": fields.disable("Permissions import is not implemented yet"),
        },
    )
    adapter.configure_model(
        "auth.Group",
        identifiers=["name"],
        fields={
            "permissions": fields.disable("Permissions import is not implemented yet"),
        },
    )
    adapter.configure_model(
        "tenancy.Tenant",
        fields={
            "group": "tenant_group",
        },
    )
    adapter.configure_model(
        "extras.JournalEntry",
        nautobot_content_type="extras.Note",
    )
    adapter.configure_model(
        "extras.ObjectChange",
        disable_related_reference=True,
        fields={
            "postchange_data": "object_data",
            # TBD: This should be defined on Nautobot side
            "time": fields.force(),
        },
    )
