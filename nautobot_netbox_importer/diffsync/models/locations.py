"""NetBox Specific Locations handling."""
from nautobot_netbox_importer.generator import DiffSyncBaseModel
from nautobot_netbox_importer.generator import RecordData
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import fields


def define_location(field: SourceField) -> None:
    """Define location field for NetBox importer."""
    field.set_nautobot_field(field.name)
    field.handle_sibling("site")
    field.handle_sibling("region")

    wrapper = field.wrapper

    location_wrapper = wrapper.adapter.wrappers["dcim.location"]
    site_wrapper = wrapper.adapter.wrappers["dcim.site"]
    region_wrapper = wrapper.adapter.wrappers["dcim.region"]

    def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        location = source.get(field.name, None)
        site = source.get("site", None)
        region = source.get("region", None)

        # Location is the most specific, then site, the last is region
        if location:
            result = location_wrapper.get_pk_from_uid(location)
            location_wrapper.add_reference(result, wrapper)
        elif site:
            result = site_wrapper.get_pk_from_uid(site)
            site_wrapper.add_reference(result, wrapper)
        elif region:
            result = region_wrapper.get_pk_from_uid(region)
            region_wrapper.add_reference(result, wrapper)
        else:
            return

        setattr(target, field.nautobot.name, result)

    field.set_importer(importer)


def _define_site_region(field: SourceField) -> None:
    field.set_nautobot_field("parent")

    region_wrapper = field.wrapper.adapter.wrappers["dcim.region"]

    def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        value = source.get(field.name, None)
        if not value:
            return

        result = region_wrapper.get_pk_from_uid(value)
        region_wrapper.add_reference(result, field.wrapper)
        setattr(target, field.nautobot.name, result)

    field.set_importer(importer)


def _define_location_parent(field: SourceField) -> None:
    field.set_nautobot_field(field.name)
    field.handle_sibling("site")

    site_wrapper = field.wrapper.adapter.wrappers["dcim.site"]

    def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        parent = source.get(field.name, None)
        site = source.get("site", None)

        if parent:
            result = field.wrapper.get_pk_from_uid(parent)
            field.wrapper.add_reference(result, field.wrapper)
        elif site:
            result = site_wrapper.get_pk_from_uid(site)
            site_wrapper.add_reference(result, field.wrapper)
        else:
            return

        setattr(target, field.nautobot.name, result)

    field.set_importer(importer)


def _define_site_group(field: SourceField) -> None:
    site_group_wrapper = field.wrapper.adapter.wrappers["dcim.sitegroup"]
    location_type_wrapper = field.wrapper.adapter.wrappers["dcim.locationtype"]
    site_type_uid = location_type_wrapper.get_pk_from_uid("Site")

    field.set_nautobot_field("location_type")

    def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        group = source.get(field.name, None)
        if group:
            result = site_group_wrapper.get_pk_from_uid(group)
            site_group_wrapper.add_reference(result, field.wrapper)
        else:
            result = site_type_uid
            location_type_wrapper.add_reference(result, field.wrapper)

        setattr(target, field.nautobot.name, result)

    field.set_importer(importer)


def setup(adapter: SourceAdapter) -> None:
    """Setup locations for NetBox importer."""
    options = getattr(adapter, "options", {})
    sitegroup_parent_always_region = getattr(options, "sitegroup_parent_always_region", False)

    location_type_wrapper = adapter.configure_model("dcim.locationtype")

    region_type_uid = location_type_wrapper.cache_record(
        {
            "id": "Region",
            "name": "Region",
            "nestable": True,
            "content_types": None,
        }
    )
    site_type_uid = location_type_wrapper.cache_record(
        {
            "id": "Site",
            "name": "Site",
            "nestable": False,
            "parent": region_type_uid,
        }
    )
    location_type_uid = location_type_wrapper.cache_record(
        {
            "id": "Location",
            "name": "Location",
            "nestable": True,
            "parent": site_type_uid,
        }
    )

    adapter.configure_model(
        "dcim.sitegroup",
        nautobot_content_type="dcim.locationtype",
        fields={
            "parent": fields.constant(region_type_uid) if sitegroup_parent_always_region else "parent",
            "nestable": fields.constant(True),
        },
    )

    adapter.configure_model(
        "dcim.region",
        nautobot_content_type="dcim.location",
        fields={
            "status": "status",
            "location_type": fields.constant(region_type_uid),
        },
    )

    adapter.configure_model(
        "dcim.site",
        nautobot_content_type="dcim.location",
        fields={
            "region": _define_site_region,
            "group": _define_site_group,
        },
    )

    adapter.configure_model(
        "dcim.location",
        fields={
            "status": "status",
            "location_type": fields.constant(location_type_uid),
            "parent": _define_location_parent,
        },
    )

    for name in ["region", "site", "location"]:
        wrapper = adapter.wrappers[f"dcim.{name}"]
        location_type_wrapper.add_reference(location_type_wrapper.get_pk_from_uid(name.capitalize()), wrapper)
        wrapper.set_references_forwarding("dcim.locationtype", "location_type_id")
