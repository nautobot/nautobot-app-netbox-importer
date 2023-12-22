"""NetBox to Nautobot DCIM Models Mapping."""
import json
from uuid import UUID

from nautobot_netbox_importer.generator import EMPTY_VALUES
from nautobot_netbox_importer.generator import RecordData
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import fields

from .locations import define_location


def _define_units(field: SourceField) -> None:
    field.set_nautobot_field(field.name)

    def importer(source: RecordData, target: RecordData) -> None:
        # NetBox 3.4 units is `list[int]`, previous versions are JSON string with list of strings
        units = source.get(field.name, None)
        if units in EMPTY_VALUES:
            return

        if isinstance(units, str):
            units = json.loads(units)
            if units:
                units = [int(unit) for unit in units]

        target[field.nautobot.name] = units

    field.set_importer(importer)


def setup_dcim(adapter: SourceAdapter) -> None:
    """Map NetBox DCIM models to Nautobot."""
    adapter.disable_model("dcim.cablepath", "Recreated in Nautobot on signal when circuit termination is created")
    adapter.configure_model(
        "dcim.rackreservation",
        fields={
            "units": _define_units,
        },
    )
    adapter.configure_model(
        "dcim.rack",
        fields={
            "location": define_location,
            "role": fields.role(adapter, "dcim.rackrole"),
        },
    )
    adapter.configure_model(
        "dcim.cable",
        fields={
            "termination_a": "termination_a",
            "termination_b": "termination_b",
        },
    )
    adapter.configure_model(
        "dcim.cabletermination_a",
        extend_content_type="dcim.cable",
        fields={
            "termination_a": "termination_a",
        },
    )
    adapter.configure_model(
        "dcim.cabletermination_b",
        extend_content_type="dcim.cable",
        fields={
            "termination_b": "termination_b",
        },
    )
    adapter.configure_model(
        "dcim.interface",
        fields={
            "status": "status",
            "parent": "parent_interface",
        },
    )
    manufacturer = adapter.configure_model(
        "dcim.manufacturer",
        default_reference={
            "id": "Unknown",
            "name": "Unknown",
        },
    )
    adapter.configure_model(
        "dcim.devicetype",
        fields={
            "front_image": None,
            "rear_image": None,
            "color": "color",
        },
        default_reference={
            "id": "Unknown",
            "manufacturer": manufacturer.get_default_reference_uid(),
            "model": "Unknown",
        },
    )
    adapter.configure_model(
        "dcim.devicerole",
        nautobot_content_type="extras.role",
    )
    adapter.configure_model(
        "dcim.device",
        fields={
            "location": define_location,
            "device_role": fields.role(adapter, "dcim.devicerole"),
            "role": fields.role(adapter, "dcim.devicerole"),
        },
    )
    adapter.configure_model(
        "dcim.powerpanel",
        fields={
            "location": define_location,
        },
    )
    adapter.configure_model(
        "dcim.frontporttemplate",
        fields={
            "rear_port": "rear_port_template",
        },
    )
    adapter.configure_model(
        "dcim.poweroutlettemplate",
        fields={
            "power_port": "power_port_template",
        },
    )


# pylint: disable=too-many-locals
def fix_power_feed_locations(adapter: SourceAdapter) -> None:
    """Fix panel location to match rack location based on powerfeed."""
    region_wrapper = adapter.wrappers["dcim.region"]
    site_wrapper = adapter.wrappers["dcim.site"]
    location_wrapper = adapter.wrappers["dcim.location"]
    rack_wrapper = adapter.wrappers.get("dcim.rack", None)
    panel_wrapper = adapter.wrappers.get("dcim.powerpanel", None)
    if not (rack_wrapper and panel_wrapper):
        return

    importer = adapter.wrappers["dcim.powerfeed"].nautobot.importer
    if not importer:
        return

    for item in adapter.get_all(importer):
        rack_id = getattr(item, "rack_id", None)
        panel_id = getattr(item, "power_panel_id", None)
        if not (rack_id and panel_id):
            continue

        rack = rack_wrapper.get(rack_id)
        panel = panel_wrapper.get(panel_id)

        rack_location_uid = getattr(rack, "location_id", None)
        panel_location_uid = getattr(panel, "location_id", None)
        if rack_location_uid == panel_location_uid:
            continue

        if rack_location_uid:
            location_uid = rack_location_uid
            target = panel
            target_wrapper = panel_wrapper
        else:
            location_uid = panel_location_uid
            target = rack
            target_wrapper = rack_wrapper

        if not isinstance(location_uid, UUID):
            raise TypeError(f"Location UID must be UUID, got {type(location_uid)}")

        target.location_id = location_uid
        adapter.update(target)

        # Need to update references, to properly update `content_types` fields
        # References can be counted and removed, if needed
        if location_uid in region_wrapper.references:
            region_wrapper.add_reference(location_uid, target_wrapper)
        elif location_uid in site_wrapper.references:
            site_wrapper.add_reference(location_uid, target_wrapper)
        elif location_uid in location_wrapper.references:
            location_wrapper.add_reference(location_uid, target_wrapper)
        else:
            raise ValueError(f"Unknown location type {location_uid}")
