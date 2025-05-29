"""NetBox to Nautobot Tags related Models Mapping."""

from packaging.version import Version

from nautobot_netbox_importer.base import RecordData, Uid
from nautobot_netbox_importer.diffsync.adapters import NetBoxAdapter
from nautobot_netbox_importer.generator import DiffSyncBaseModel, SourceAdapter, SourceField
from nautobot_netbox_importer.generator.base import source_pk_to_uuid


def _setup_v4(adapter: SourceAdapter) -> None:
    def get_tag_pk_from_data(source: RecordData) -> Uid:
        """Get the primary key from the data."""
        name = name_field.get_source_value(source)
        if not name:
            raise ValueError("Missing name for tag")

        return source_pk_to_uuid("extras.tag", name)

    def get_tagged_item_pk_from_data(source: RecordData) -> Uid:
        """Get the primary key from the data."""
        content_type = content_type_field.get_source_value(source)
        object_id = object_id_field.get_source_value(source)
        tag = tag_field.get_source_value(source)
        if isinstance(tag, list):
            tag = tag[0]

        return source_pk_to_uuid("extras.taggeditem", f"{':'.join(content_type)}.{object_id}.{tag}")

    def define_object(field: SourceField) -> None:
        def tagged_object_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            object_id = field.get_source_value(source)
            if not object_id:
                return

            tag = tag_field.get_source_value(source)
            if isinstance(tag, list):
                if len(tag) == 0:
                    return

                if len(tag) > 1:
                    tag_field.add_issue(
                        "MultipleTags",
                        f"Multiple tags found, importing only the first one: {tag}",
                        target=target,
                    )

                tag = tag[0]

            content_type = content_type_field.get_source_value(source)
            if not tag or not content_type:
                raise ValueError(f"Missing content_type or tag for tagged object {object_id}")

            tag_uuid = source_pk_to_uuid("extras.tag", tag)
            related_wrapper = adapter.get_or_create_wrapper(content_type)
            result = related_wrapper.get_pk_from_uid(object_id)
            field.set_nautobot_value(target, result)
            tag_field.set_nautobot_value(target, tag_uuid)
            content_type_field.set_nautobot_value(target, related_wrapper.nautobot.content_type_instance.pk)
            related_wrapper.add_reference(tag_wrapper, tag_uuid)

        field.set_importer(tagged_object_importer)
        field.handle_sibling("tag", "tag")
        field.handle_sibling("content_type", "content_type")

    tag_wrapper = adapter.configure_model(
        "extras.Tag",
        get_pk_from_data=get_tag_pk_from_data,
        fields={
            "name": "",
            "object_types": "content_types",
        },
    )
    name_field = tag_wrapper.fields["name"]

    tagged_item_wrapper = adapter.configure_model(
        "extras.TaggedItem",
        get_pk_from_data=get_tagged_item_pk_from_data,
        fields={
            "content_type": "",
            "object_id": define_object,
            "tag": "",
        },
    )
    content_type_field = tagged_item_wrapper.fields["content_type"]
    object_id_field = tagged_item_wrapper.fields["object_id"]
    tag_field = tagged_item_wrapper.fields["tag"]


def _setup_v3(adapter: SourceAdapter) -> None:
    def define_tagged_object(field: SourceField) -> None:
        wrapper = field.wrapper
        adapter = wrapper.adapter
        tag_wrapper = adapter.get_or_create_wrapper("extras.tag")

        def tagged_object_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            object_id = field.get_source_value(source)
            if not object_id:
                return

            tag = tag_field.get_source_value(source)
            content_type = content_type_field.get_source_value(source)
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

    adapter.configure_model(
        "extras.tag",
        fields={
            "object_types": "content_types",
        },
    )
    adapter.configure_model(
        "extras.TaggedItem",
        fields={
            "object_id": define_tagged_object,
        },
    )


def setup(adapter: NetBoxAdapter) -> None:
    """Map NetBox tags related models to Nautobot."""
    if adapter.options.netbox_version < Version("4"):
        _setup_v3(adapter)
    else:
        _setup_v4(adapter)
