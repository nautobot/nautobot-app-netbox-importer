"""NetBox to Nautobot Base Models Mapping."""

from diffsync.enum import DiffSyncModelFlags

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.generator import DiffSyncBaseModel
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import fields


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
        field.set_nautobot_value(target, result)
        tag_field.set_nautobot_value(target, tag_uuid)
        content_type_field.set_nautobot_value(target, related_wrapper.nautobot.content_type_instance.pk)
        related_wrapper.add_reference(tag_wrapper, tag_uuid)

    field.set_importer(tagged_object_importer)
    tag_field = field.handle_sibling("tag", "tag")
    content_type_field = field.handle_sibling("content_type", "content_type")


def _setup_content_types(adapter: SourceAdapter) -> None:
    """Map NetBox content types to Nautobot.

    Automatically calculate NetBox content type IDs, if not provided, based on the order of the content types.
    """
    netbox = {"id": 0}

    def define_app_label(field: SourceField) -> None:
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
            field.set_nautobot_value(target, app_label)

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
        "extras.tag",
        fields={
            "object_types": "content_types",
        },
    )
    adapter.configure_model(
        "extras.TaggedItem",
        fields={
            "object_id": _define_tagged_object,
        },
    )
    adapter.configure_model(
        # pylint: disable=hard-coded-auth-user
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
