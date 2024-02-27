"""NetBox Specific Locations handling."""

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.generator import DiffSyncBaseModel
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import SourceModelWrapper
from nautobot_netbox_importer.generator import SourceReferences
from nautobot_netbox_importer.generator import fields


def define_location(field: SourceField) -> None:
    """Define location field for NetBox importer."""
    wrapper = field.wrapper

    location_wrapper = wrapper.adapter.wrappers["dcim.location"]
    site_wrapper = wrapper.adapter.wrappers["dcim.site"]
    region_wrapper = wrapper.adapter.wrappers["dcim.region"]

    def location_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        location = source.get(field.name, None)
        site = source.get("site", None)
        region = source.get("region", None)

        # Location is the most specific, then site, the last is region
        if location:
            result = location_wrapper.get_pk_from_uid(location)
            wrapper.add_reference(location_wrapper, result)
        elif site:
            result = site_wrapper.get_pk_from_uid(site)
            wrapper.add_reference(site_wrapper, result)
        elif region:
            result = region_wrapper.get_pk_from_uid(region)
            wrapper.add_reference(region_wrapper, result)
        else:
            return

        field.set_nautobot_value(target, result)

    field.set_importer(location_importer)
    field.handle_sibling("site", field.nautobot.name)
    field.handle_sibling("region", field.nautobot.name)


def _define_location_parent(field: SourceField) -> None:
    wrapper = field.wrapper
    site_wrapper = wrapper.adapter.wrappers["dcim.site"]

    def location_parent_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        parent = source.get(field.name, None)
        site = source.get("site", None)

        if parent:
            result = wrapper.get_pk_from_uid(parent)
            wrapper.add_reference(wrapper, result)
        elif site:
            result = site_wrapper.get_pk_from_uid(site)
            wrapper.add_reference(site_wrapper, result)
        else:
            return

        field.set_nautobot_value(target, result)

    field.set_importer(location_parent_importer)
    field.handle_sibling("site", field.nautobot.name)


def _define_site_group(field: SourceField) -> None:
    wrapper = field.wrapper
    site_group_wrapper = wrapper.adapter.wrappers["dcim.sitegroup"]
    location_type_wrapper = wrapper.adapter.wrappers["dcim.locationtype"]
    site_type_uid = location_type_wrapper.get_pk_from_uid("Site")

    def site_group_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        group = source.get(field.name, None)
        if group:
            result = site_group_wrapper.get_pk_from_uid(group)
            wrapper.add_reference(site_group_wrapper, result)
        else:
            result = site_type_uid
            wrapper.add_reference(location_type_wrapper, result)

        field.set_nautobot_value(target, result)

    field.set_importer(site_group_importer, "location_type")


def setup(adapter: SourceAdapter) -> None:
    """Setup locations for NetBox importer."""

    def forward_references(wrapper: SourceModelWrapper, references: SourceReferences) -> None:
        """Forward references to Location, Site and Region instance to their LocationType to fill `content_types`."""
        for uid, wrappers in references.items():
            instance = wrapper.get_or_create(uid, fail_missing=True)
            location_type_uid = getattr(instance, "location_type_id")
            for item in wrappers:
                item.add_reference(location_type_wrapper, location_type_uid)

    options = getattr(adapter, "options", {})
    sitegroup_parent_always_region = getattr(options, "sitegroup_parent_always_region", False)

    location_type_wrapper = adapter.configure_model("dcim.LocationType")

    region_type_uid = location_type_wrapper.cache_record(
        {
            "id": "Region",
            "name": "Region",
            "nestable": True,
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
        "dcim.SiteGroup",
        nautobot_content_type="dcim.LocationType",
        fields={
            "parent": fields.constant(region_type_uid) if sitegroup_parent_always_region else "parent",
            "nestable": fields.constant(True),
        },
    )

    adapter.configure_model(
        "dcim.Region",
        nautobot_content_type="dcim.Location",
        forward_references=forward_references,
        fields={
            "location_type": fields.constant(region_type_uid),
        },
    )

    adapter.configure_model(
        "dcim.Site",
        nautobot_content_type="dcim.Location",
        forward_references=forward_references,
        fields={
            "region": fields.relation("dcim.Region", "parent"),
            "group": _define_site_group,
        },
    )

    adapter.configure_model(
        "dcim.Location",
        forward_references=forward_references,
        fields={
            "location_type": fields.constant(location_type_uid),
            "parent": _define_location_parent,
        },
    )
