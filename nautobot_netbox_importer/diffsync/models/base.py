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

    def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
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

    field.set_importer(importer)


def _define_tagged_object(field: SourceField) -> None:
    field.set_nautobot_field(field.name)

    def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        content_type = source.get("content_type", None)
        object_id = source.get(field.name, None)
        if not object_id or not content_type:
            return

        related_wrapper = field.wrapper.adapter.get_or_create_wrapper(content_type)
        result = related_wrapper.get_pk_from_uid(object_id)
        setattr(target, field.nautobot.name, result)
        related_wrapper.add_reference(result, field.wrapper)

    field.set_importer(importer)


def _setup_object_change(adapter: SourceAdapter) -> None:
    """Map NetBox object change to Nautobot.

    JSON file with object changes need to have all content types exported first to properly map the content types.
    """

    def define_changed_object(field: SourceField) -> None:
        field.set_nautobot_field(field.name)
        object_field = field.handle_sibling("changed_object_id", nautobot_name="changed_object_id")

        def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            content_type = source[field.name]
            object_id = source[object_field.name]
            related_wrapper = adapter.get_or_create_wrapper(content_type)
            setattr(target, field.nautobot.name, related_wrapper.nautobot.content_type_instance.pk)
            setattr(target, object_field.nautobot.name, related_wrapper.get_pk_from_uid(object_id))

        field.set_importer(importer)

    def define_user(field: SourceField) -> None:
        field.set_nautobot_field(field.name)
        user_field = field.handle_sibling("user", nautobot_name="user_id")
        user_wrapper = adapter.get_or_create_wrapper("auth.user")

        def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            user_name = source[field.name]
            setattr(target, field.nautobot.name, user_name)
            setattr(target, user_field.nautobot.name, user_wrapper.get_pk_from_identifiers([user_name]))

        field.set_importer(importer)

    adapter.configure_model(
        "extras.objectchange",
        fields={
            "user_name": define_user,
            "changed_object_type": define_changed_object,
            "postchange_data": "object_data",
            "time": fields.force(),
        },
    )


def _setup_content_types(adapter: SourceAdapter) -> None:
    """Map NetBox content types to Nautobot.

    Automatically calculate NetBox content type IDs, if not provided, based on the order of the content types.
    """
    netbox = {"id": 0}

    def cache_content_type(field: SourceField) -> None:
        field.set_nautobot_field(field.name)

        def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
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

        field.set_importer(importer)

    adapter.configure_model(
        "contenttypes.contenttype",
        identifiers=["app_label", "model"],
        flags=DiffSyncModelFlags.IGNORE,
        nautobot_flags=DiffSyncModelFlags.IGNORE,
        fields={
            "app_label": cache_content_type,
        },
    )


def setup_base(adapter: SourceAdapter) -> None:
    """Map NetBox base models to Nautobot."""
    adapter.disable_model("sessions.session", "Nautobot has own sessions, sessions should never cross apps.")
    adapter.disable_model("admin.logentry", "Not directly used in Nautobot.")
    adapter.disable_model("users.userconfig", "May not have a 1 to 1 translation to Nautobot.")
    adapter.disable_model("auth.permission", "Handled via a Nautobot model and may not be a 1 to 1.")

    _setup_content_types(adapter)
    _setup_object_change(adapter)

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
