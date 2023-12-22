"""NetBox Specific Locations handling."""
from nautobot_netbox_importer.generator import RecordData
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import fields


def define_location(field: SourceField) -> None:
    """Define location field for NetBox importer."""
    field.set_nautobot_field(field.name)
    field.handle_siblings("region", "site")

    wrapper = field.wrapper

    location_wrapper = wrapper.adapter.wrappers["dcim.location"]
    site_wrapper = wrapper.adapter.wrappers["dcim.site"]
    region_wrapper = wrapper.adapter.wrappers["dcim.region"]

    def importer(source: RecordData, target: RecordData) -> None:
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

        target[field.nautobot.name] = result

    field.set_importer(importer)


def _define_site_region(field: SourceField) -> None:
    field.set_nautobot_field("parent")

    region_wrapper = field.wrapper.adapter.wrappers["dcim.region"]

    def importer(source: RecordData, target: RecordData) -> None:
        value = source.get(field.name, None)
        if not value:
            return

        result = region_wrapper.get_pk_from_uid(value)
        region_wrapper.add_reference(result, field.wrapper)
        target[field.nautobot.name] = result

    field.set_importer(importer)


def _define_location_parent(field: SourceField) -> None:
    field.set_nautobot_field(field.name)
    field.handle_siblings("site")

    site_wrapper = field.wrapper.adapter.wrappers["dcim.site"]

    def importer(source: RecordData, target: RecordData) -> None:
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

        target[field.nautobot.name] = result

    field.set_importer(importer)


def _define_site_group(field: SourceField) -> None:
    site_group_wrapper = field.wrapper.adapter.wrappers["dcim.sitegroup"]
    location_type_wrapper = field.wrapper.adapter.wrappers["dcim.locationtype"]
    site_type_uid = location_type_wrapper.get_pk_from_uid("Site")

    field.set_nautobot_field("location_type")

    def importer(source: RecordData, target: RecordData) -> None:
        group = source.get(field.name, None)
        if group:
            result = site_group_wrapper.get_pk_from_uid(group)
            site_group_wrapper.add_reference(result, field.wrapper)
        else:
            result = site_type_uid
            location_type_wrapper.add_reference(result, field.wrapper)

        target[field.nautobot.name] = result

    field.set_importer(importer)


def setup_locations(adapter: SourceAdapter, sitegroup_parent_always_region) -> None:
    """Setup locations for NetBox importer."""
    location_type_wrapper = adapter.configure_model(
        "dcim.locationtype",
        fields={
            # TBD: Verify necessity
            "parent": fields.pass_through(),
        },
        default_reference={
            "id": "Unknown",
            "name": "Unknown",
            "nestable": True,
            "content_types": [],
        },
    )

    region_type_uid = location_type_wrapper.cache_record({"id": "Region", "name": "Region", "nestable": True})
    site_type_uid = location_type_wrapper.cache_record(
        {"id": "Site", "name": "Site", "nestable": False, "parent": region_type_uid}
    )
    location_type_uid = location_type_wrapper.cache_record(
        {"id": "Location", "name": "Location", "nestable": True, "parent": site_type_uid}
    )

    adapter.configure_model(
        # EXAMPLE DATA:{
        #   "model": "dcim.sitegroup",
        #   "pk": 1,
        #   "fields": {
        #     "parent": null,
        #     "name": "Customer Sites",
        #     "description": "",
        #   }
        # },
        "dcim.sitegroup",
        nautobot_content_type="dcim.locationtype",
        fields={
            "parent": fields.constant(region_type_uid) if sitegroup_parent_always_region else "parent",
            "nestable": fields.constant(True),
        },
    )

    adapter.configure_model(
        # EXAMPLE DATA:{
        #   "model": "dcim.region",
        #   "pk": 1,
        #   "fields": {
        #     "parent": null,
        #     "name": "North America",
        #     "description": "",
        #   }
        # },
        "dcim.region",
        nautobot_content_type="dcim.location",
        fields={
            "status": "status",
            # "parent": _define_region_parent,
            "location_type": fields.constant(region_type_uid),
        },
    )

    adapter.configure_model(
        # EXAMPLE DATA:{
        #   "model": "dcim.site",
        #   "pk": 1,
        #   "fields": {
        #     "description": "",
        #     "comments": "",
        #     "name": "DM-NYC",
        #     "status": "active",
        #     "region": 43,
        #     "group": 3,
        #     "tenant": 5,
        #     "facility": "",
        #     "time_zone": null,
        #     "physical_address": "",
        #     "shipping_address": "",
        #     "latitude": null,
        #     "longitude": null,
        #     "asns": []
        #   }
        # },
        "dcim.site",
        nautobot_content_type="dcim.location",
        fields={
            "region": _define_site_region,
            "group": _define_site_group,
        },
    )

    adapter.configure_model(
        # EXAMPLE DATA:{
        #   "model": "dcim.location",
        #   "pk": 1,
        #   "fields": {
        #     "parent": null,
        #     "name": "Row 1",
        #     "description": "",
        #     "site": 21,
        #     "status": "active",
        #     "tenant": null,
        #   }
        # },
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
