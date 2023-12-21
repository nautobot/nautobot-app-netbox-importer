"""NetBox to Nautobot Source Importer Definitions."""
import json
from pathlib import Path
from typing import NamedTuple
from typing import Union
from uuid import UUID

from django.core.management import call_command
from django.db.transaction import atomic
from nautobot.ipam.models import get_default_namespace

from . import fields
from .base import EMPTY_VALUES
from .base import RecordData
from .base import logger
from .locations import define_location
from .locations import setup_locations
from .source import SourceAdapter
from .source import SourceField
from .source import SourceRecord
from .summary import print_fields_mapping
from .summary import print_summary


class NetBoxImporterOptions(NamedTuple):
    """NetBox importer options."""

    dry_run: bool = True
    bypass_data_validation: bool = False
    summary: bool = False
    field_mapping: bool = False
    update_paths: bool = False
    fix_powerfeed_locations: bool = False
    sitegroup_parent_always_region: bool = False


class _DryRunException(Exception):
    """Exception raised when a dry-run is requested."""


class _ValidationIssuesDetected(Exception):
    """Exception raised when validation issues are detected."""


def _define_tagged_object(field: SourceField) -> None:
    field.set_nautobot_field(field.name)

    def importer(source: RecordData, target: RecordData) -> None:
        content_type = source.get("content_type", None)
        object_id = source.get(field.name, None)
        if not object_id or not content_type:
            target[field.nautobot.name] = None
            return

        related_wrapper = field.wrapper.adapter.get_or_create_wrapper(content_type)
        result = related_wrapper.get_pk_from_uid(object_id)
        target[field.nautobot.name] = result
        related_wrapper.add_reference(result, field.wrapper)

    field.set_importer(importer)


def _define_choices(field: SourceField) -> None:
    choices_wrapper = field.wrapper.adapter.get_or_create_wrapper("extras.customfieldchoice")

    def importer(source: RecordData, target: RecordData) -> None:
        choices = source.get(field.name, None)
        if not choices:
            return

        choices = json.loads(choices)
        if not choices:
            return

        for choice in choices:
            choices_wrapper.import_record(
                {
                    "id": choice,
                    "custom_field": target["id"],
                    "value": choice,
                },
            )

    field.set_importer(importer)


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


def _setup_source(file_path: Union[str, Path], options: NetBoxImporterOptions) -> SourceAdapter:
    """Setup NetBox models importers."""

    def process_cable_termination(source_data: RecordData) -> str:
        # NetBox 3.3 split the dcim.cable model into dcim.cable and dcim.cabletermination models.
        cable_end = source_data.pop("cable_end").lower()
        source_data["id"] = source_data.pop("cable")
        source_data[f"termination_{cable_end}_type"] = source_data.pop("termination_type")
        source_data[f"termination_{cable_end}_id"] = source_data.pop("termination_id")

        return f"dcim.cabletermination_{cable_end}"

    def read_source_file():
        with open(file_path, "r", encoding="utf8") as file:
            data = json.load(file)

        for item in data:
            content_type = item["model"]
            netbox_pk = item.get("pk", None)
            source_data = item["fields"]

            if netbox_pk:
                source_data["id"] = netbox_pk

            if content_type == "dcim.cabletermination":
                content_type = process_cable_termination(source_data)

            yield SourceRecord(content_type, source_data)

    adapter = SourceAdapter(name="NetBox", get_source_data=read_source_file)

    _setup_base(adapter)
    setup_locations(adapter, options.sitegroup_parent_always_region)
    _setup_dcim(adapter)
    _setup_circuits(adapter)
    _setup_ipam(adapter)
    _setup_virtualization(adapter)

    return adapter


def _setup_base(adapter: SourceAdapter) -> None:
    adapter.disable_model("contenttypes.contenttype", "Nautobot has own content types; Handled via migrations")
    adapter.disable_model("sessions.session", "Nautobot has own sessions, sessions should never cross apps")
    adapter.disable_model("dcim.cablepath", "Recreated in Nautobot on signal when circuit termination is created")
    adapter.disable_model("admin.logentry", "Not directly used in Nautobot")
    adapter.disable_model("users.userconfig", "May not have a 1 to 1 translation to Nautobot")
    adapter.disable_model("auth.permission", "Handled via a Nautobot model and may not be a 1 to 1")

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
            "last_login": None,
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


def _setup_circuits(adapter: SourceAdapter) -> None:
    adapter.configure_model(
        "circuits.circuit",
        fields={
            "type": "circuit_type",
            "termination_a": "circuit_termination_a",
            "termination_z": "circuit_termination_z",
        },
    )
    adapter.configure_model(
        "circuits.circuittermination",
        fields={
            "location": define_location,
        },
    )


def _setup_dcim(adapter: SourceAdapter) -> None:
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


def _setup_ipam(adapter: SourceAdapter) -> None:
    ipaddress = adapter.configure_model(
        "ipam.ipaddress",
        fields={
            "role": fields.role(adapter, "ipam.role"),
        },
    )
    ipaddress.nautobot.set_instance_defaults(namespace=get_default_namespace())
    adapter.configure_model(
        "ipam.prefix",
        fields={
            "location": define_location,
            "role": fields.role(adapter, "ipam.role"),
        },
    )
    adapter.configure_model(
        "ipam.aggregate",
        "ipam.prefix",
        fields={
            "status": "status",
        },
    )
    adapter.configure_model(
        "ipam.vlan",
        fields={
            "group": "vlan_group",
            "location": define_location,
            "role": fields.role(adapter, "ipam.role"),
        },
    )


def _setup_virtualization(adapter: SourceAdapter) -> None:
    adapter.configure_model(
        "virtualization.cluster",
        fields={
            "type": "cluster_type",
            "group": "cluster_group",
            "location": define_location,
        },
    )
    adapter.configure_model(
        "virtualization.virtualmachine",
        fields={
            "role": fields.role(adapter, "dcim.devicerole"),
        },
    )
    adapter.configure_model(
        "virtualization.vminterface",
        fields={
            "status": "status",
            "parent": "parent_interface",
        },
    )


# pylint: disable=too-many-locals
def _fix_powerfeed_locations(adapter: SourceAdapter) -> None:
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


@atomic
def _exec_sync(source: SourceAdapter, options: NetBoxImporterOptions) -> None:
    source.import_data()
    if options.fix_powerfeed_locations:
        _fix_powerfeed_locations(source)
    source.post_import()

    nautobot = source.nautobot
    nautobot.load_data()

    nautobot.sync_from(source)

    if nautobot.validation_issues and not options.bypass_data_validation:
        raise _ValidationIssuesDetected("Data validation issues detected, aborting the transaction.")

    if options.dry_run:
        raise _DryRunException("Aborting the transaction due to the dry-run mode.")


def sync_to_nautobot(file_path: Union[str, Path], options: NetBoxImporterOptions) -> SourceAdapter:
    """Import a NetBox export file into Nautobot."""
    adapter = _setup_source(file_path, options)

    commited = False
    try:
        _exec_sync(adapter, options)
        commited = True
    except _DryRunException:
        logger.warning("Dry-run mode, no data has been imported.")
    except _ValidationIssuesDetected:
        logger.warning("Data validation issues detected, no data has been imported.")

    if commited and options.update_paths:
        logger.info("Updating paths ...")
        call_command("trace_paths", no_input=True)
        logger.info(" ... Updating paths completed.")

    if options.summary:
        print_summary(adapter)

    if options.field_mapping:
        print_fields_mapping(adapter)

    return adapter
