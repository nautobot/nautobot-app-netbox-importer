"""NetBox to Nautobot Base Models Mapping."""

from diffsync.enum import DiffSyncModelFlags

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.generator import DiffSyncBaseModel, SourceAdapter, SourceField


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox content types to Nautobot.

    It's vital to map NetBox content types to Nautobot content types properly.

    Automatically calculate NetBox content type IDs, if not provided, based on the order of the content types.
    """
    netbox = {"id": 0}

    def define_app_label(field: SourceField) -> None:
        def content_types_mapper_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            app_label = source["app_label"]
            model = source["model"]
            netbox["id"] += 1
            uid = id_field.get_source_value(source)
            if uid:
                if uid != netbox["id"]:
                    raise ValueError(f"Content type id mismatch: {uid} != {netbox['id']}")
            else:
                uid = netbox["id"]

            wrapper = adapter.get_or_create_wrapper(f"{app_label}.{model}")
            adapter.content_type_ids_mapping[uid] = wrapper
            field.set_nautobot_value(target, app_label)

        field.set_importer(content_types_mapper_importer)

    content_type_wrapper = adapter.configure_model(
        "contenttypes.ContentType",
        identifiers=["app_label", "model"],
        flags=DiffSyncModelFlags.IGNORE,
        nautobot_flags=DiffSyncModelFlags.IGNORE,
        fields={
            "app_label": define_app_label,
        },
    )

    id_field = content_type_wrapper.fields["id"]
