"""NetBox to Nautobot DCIM Models Mapping."""

import json
from uuid import UUID

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.generator import DiffSyncBaseModel
from nautobot_netbox_importer.generator import PreImportResult
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import fields

from .locations import define_location


def _define_units(field: SourceField) -> None:
    """Define the units field importer.

    This function is called between the first and second pass of input data, when creating importers.
    """

    def units_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        """Import the `units` field from NetBox to Nautobot.

        This function is called for each input source data record of `dcim.rackreservation` model.

        NetBox 3.4 units is `list[int]`, previous versions are JSON string with list of strings.
        """
        # Read value from input data
        value = field.get_source_value(source)

        # Process the conversion from NetBox to Nautobot format
        if isinstance(value, str) and value:
            value = json.loads(value)
        if value:
            value = [int(unit) for unit in value]

        # Store the value in the target DiffSyncModel instance.
        field.set_nautobot_value(target, value)

    # Register the importer and map the field from NetBox to Nautobot.
    # The Nautobot field name is the same as the NetBox field name: `units` in this case.
    field.set_importer(units_importer)


def _pre_import_cable_termination(source: RecordData, _) -> PreImportResult:
    cable_end = source.pop("cable_end").lower()
    source["id"] = source.pop("cable")
    source[f"termination_{cable_end}_type"] = source.pop("termination_type")
    source[f"termination_{cable_end}_id"] = source.pop("termination_id")

    return PreImportResult.USE_RECORD


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox DCIM models to Nautobot."""
    adapter.disable_model("dcim.cablepath", "Recreated in Nautobot on signal when circuit termination is created")
    adapter.configure_model(
        "dcim.rackreservation",
        fields={
            # Set the definition of the `units` field
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
    adapter.configure_model("dcim.cable")
    adapter.configure_model(
        "dcim.cabletermination",
        extend_content_type="dcim.cable",
        pre_import=_pre_import_cable_termination,
    )
    adapter.configure_model(
        "dcim.interface",
        fields={
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
            "front_image": fields.disable("Import does not contain images"),
            "rear_image": fields.disable("Import does not contain images"),
        },
        default_reference={
            "id": "Unknown",
            "manufacturer": manufacturer.get_default_reference_uid(),
            "model": "Unknown",
        },
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


def unrack_zero_uheight_devices(adapter: SourceAdapter) -> None:
    """Unrack devices with 0U height."""
    device_wrapper = adapter.wrappers["dcim.device"]
    device_type_wrapper = adapter.wrappers["dcim.devicetype"]

    # Find all device types with 0U height
    device_type_ids = set(
        getattr(item, "id")
        for item in adapter.get_all(device_type_wrapper.nautobot.diffsync_class)
        if getattr(item, "u_height", 0) == 0
    )

    if not device_type_ids:
        return

    # Update all devices with matching device type, clean `position` field.
    position = device_wrapper.fields["position"]
    for item in adapter.get_all(device_wrapper.nautobot.diffsync_class):
        if getattr(item, "position", None) and getattr(item, "device_type_id") in device_type_ids:
            position.set_nautobot_value(item, None)
            adapter.update(item)
            position.add_issue("Unracked", "Device unracked due to 0U height", item)


# pylint: disable=too-many-locals
def fix_power_feed_locations(adapter: SourceAdapter) -> None:
    """Fix panel location to match rack location based on powerfeed."""
    region_wrapper = adapter.wrappers["dcim.region"]
    site_wrapper = adapter.wrappers["dcim.site"]
    location_wrapper = adapter.wrappers["dcim.location"]
    rack_wrapper = adapter.wrappers["dcim.rack"]
    panel_wrapper = adapter.wrappers["dcim.powerpanel"]

    diffsync_class = adapter.wrappers["dcim.powerfeed"].nautobot.diffsync_class

    for item in adapter.get_all(diffsync_class):
        rack_id = getattr(item, "rack_id", None)
        panel_id = getattr(item, "power_panel_id", None)
        if not (rack_id and panel_id):
            continue

        rack = rack_wrapper.get_or_create(rack_id)
        panel = panel_wrapper.get_or_create(panel_id)

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
            target_wrapper.add_reference(region_wrapper, location_uid)
        elif location_uid in site_wrapper.references:
            target_wrapper.add_reference(site_wrapper, location_uid)
        elif location_uid in location_wrapper.references:
            target_wrapper.add_reference(location_wrapper, location_uid)
        else:
            raise ValueError(f"Unknown location type {location_uid}")
