"""NetBox to Nautobot importer."""
import json
from pathlib import Path
from typing import Tuple
from typing import Union

from django.db.transaction import atomic
from nautobot.ipam.models import get_default_namespace

from .base import EMPTY_VALUES
from .base import RecordData
from .nautobot import NautobotAdapter
from .source import SourceAdapter
from .source import SourceField
from .source import SourceRecord
from .summary import print_fields_mapping
from .summary import print_summary


def _define_tagged_object(field: SourceField) -> None:
    field.set_nautobot_field(field.name)

    def importer(source: RecordData, target: RecordData) -> None:
        content_type = source.get("content_type", None)
        object_id = source.get(field.name, None)
        if not object_id or not content_type:
            target[field.name] = None
            return

        related_wrapper = field.wrapper.adapter.get_or_create_wrapper(content_type)
        result = related_wrapper.get_pk_from_uid(object_id)
        target[field.name] = result
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


def _define_location_type(field: SourceField) -> None:
    field.set_nautobot_field(field.name)
    field.wrapper.set_references_forwarding("dcim.locationtype", field.nautobot.name)

    location_type_wrapper = field.wrapper.adapter.get_or_create_wrapper("dcim.locationtype")
    # Uppercase the first letter of the content type name
    name = field.wrapper.content_type.split(".")[1]
    name = name[0].upper() + name[1:]
    location_type_id = location_type_wrapper.cache_record({"id": name, "name": name, "nestable": True})

    def importer(_, target: RecordData) -> None:
        target[field.nautobot.name] = location_type_id
        location_type_wrapper.add_reference(location_type_id, field.wrapper)

    field.set_importer(importer)


def _define_location(field: SourceField) -> None:
    if field.name not in ["location", "parent"]:
        raise ValueError("_define_location only supports location and parent")
    field.set_nautobot_field(field.name)

    wrapper = field.wrapper
    wrapper.add_field("region", None)
    wrapper.add_field("site", None)

    location_wrapper = wrapper.adapter.get_or_create_wrapper("dcim.location")
    site_wrapper = wrapper.adapter.get_or_create_wrapper("dcim.site")
    region_wrapper = wrapper.adapter.get_or_create_wrapper("dcim.region")

    def importer(source: RecordData, target: RecordData) -> None:
        parent = source.get("parent", None)
        location = source.get("location", None)
        site = source.get("site", None)
        region = source.get("region", None)

        if field.nautobot.name == "parent_id" and parent:
            result = wrapper.get_pk_from_uid(parent)
            wrapper.add_reference(result, wrapper)
        elif location:
            result = location_wrapper.get_pk_from_uid(location)
            location_wrapper.add_reference(result, wrapper)
        elif site:
            result = site_wrapper.get_pk_from_uid(site)
            site_wrapper.add_reference(result, wrapper)
        elif region:
            result = region_wrapper.get_pk_from_uid(region)
            region_wrapper.add_reference(result, wrapper)
        else:
            result = None

        target[field.nautobot.name] = result

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

        target[field.name] = units

    field.set_importer(importer)


def _role_definition_factory(adapter: SourceAdapter, role_content_type: str):
    if role_content_type in adapter.wrappers:
        role_wrapper = adapter.wrappers[role_content_type]
    else:
        role_wrapper = adapter.configure_model(
            role_content_type,
            nautobot_content_type="extras.role",
            fields={"color": "color", "content_types": "content_types"},
        )

    def definition(field: SourceField) -> None:
        field.set_role_importer(role_wrapper)

    return definition


def _setup_source() -> SourceAdapter:
    """Setup NetBox models importers."""
    adapter = SourceAdapter(name="NetBox")
    adapter.configure(
        ignore_fields={
            "last_updated": None,  # It's updated on every save and can't be imported
        },
        ignore_content_types={
            "contenttypes.contenttype": None,  # Nautobot has own content types, handled via migrations
            "sessions.session": None,  # Nautobot has own sessions, sessions should never cross apps
            "dcim.cablepath": None,  # Recreated in Nautobot on signal when circuit termination is created
            "admin.logentry": None,  # Not directly used in Nautobot
            "users.userconfig": None,  # May not have a 1 to 1 translation to Nautobot
            "auth.permission": None,  # Handled via a Nautobot model and may not be a 1 to 1
        },
    )

    _setup_base(adapter)
    _setup_dcim(adapter)
    _setup_circuits(adapter)
    _setup_ipam(adapter)
    _setup_virtualization(adapter)

    return adapter


def _setup_base(adapter: SourceAdapter) -> None:
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
        "dcim.locationtype",
        default_reference={
            "id": "Unknown",
            "name": "Unknown",
            "nestable": True,
            "content_types": [],
        },
    )
    adapter.configure_model(
        "dcim.location",
        fields={
            "status": "status",
            "location_type": _define_location_type,
            "parent": _define_location,
        },
    )
    adapter.configure_model(
        "auth.user",
        nautobot_content_type="users.user",
        identifiers=["username"],
        fields={
            "last_login": None,
            "is_superuser": None,  # NetBox 3.1 TBD verify
            "password": None,  # Should not be attempted to migrated
            "user_permissions": None,  # NetBox 3.1 TBD verify
        },
    )
    adapter.configure_model(
        "auth.group",
        identifiers=["name"],
        fields={
            "permissions": None,  # NetBox 3.1 TBD verify
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
            "location": _define_location,
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
            "location": _define_location,
            "role": _role_definition_factory(adapter, "dcim.rackrole"),
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
            "front_image": None,  # TBD verify
            "rear_image": None,  # TBD verify
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
            "location": _define_location,
            "device_role": _role_definition_factory(adapter, "dcim.devicerole"),
            "role": _role_definition_factory(adapter, "dcim.devicerole"),
        },
    )
    adapter.configure_model(
        "dcim.powerpanel",
        fields={
            "location": _define_location,
        },
    )
    adapter.configure_model(
        "dcim.frontporttemplate",
        fields={
            "rear_port": "rear_port_template",
        },
    )
    adapter.configure_model(
        "dcim.region",
        "dcim.location",
        fields={
            "status": "status",
            "location_type": _define_location_type,
            "parent": _define_location,
        },
    )
    adapter.configure_model(
        "dcim.site",
        "dcim.location",
        fields={
            "status": "status",
            "location_type": _define_location_type,
            "parent": _define_location,
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
            "role": _role_definition_factory(adapter, "ipam.role"),
        },
    )
    ipaddress.nautobot.set_instance_defaults(namespace=get_default_namespace())
    adapter.configure_model(
        "ipam.prefix",
        fields={
            "location": _define_location,
            "role": _role_definition_factory(adapter, "ipam.role"),
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
            "location": _define_location,
            "role": _role_definition_factory(adapter, "ipam.role"),
        },
    )


def _setup_virtualization(adapter: SourceAdapter) -> None:
    adapter.configure_model(
        "virtualization.cluster",
        fields={
            "type": "cluster_type",
            "group": "cluster_group",
            "location": _define_location,
        },
    )
    adapter.configure_model(
        "virtualization.virtualmachine",
        fields={
            "role": _role_definition_factory(adapter, "dcim.devicerole"),
        },
    )
    adapter.configure_model(
        "virtualization.vminterface",
        fields={
            "status": "status",
            "parent": "parent_interface",
        },
    )


@atomic
def sync_to_nautobot(
    file_path: Union[str, Path],
    dry_run=True,
    summary=False,
    field_mapping=False,
) -> Tuple[SourceAdapter, NautobotAdapter]:
    """Import a NetBox export file."""

    def process_cable_termination(source_data: RecordData) -> str:
        # NetBox 3.3 split the dcim.cable model into dcim.cable and dcim.cabletermination models.
        cable_end = source_data.pop("cable_end").lower()
        source_data["id"] = source_data.pop("cable")
        source_data[f"termination_{cable_end}_type"] = source_data.pop("termination_type")
        source_data[f"termination_{cable_end}_id"] = source_data.pop("termination_id")

        return f"dcim.cabletermination_{cable_end}"

    def read_source_file():
        # TBD: Consider stream processing to avoid loading the entire file into memory
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

    source = _setup_source()

    source.import_data(read_source_file)

    nautobot = source.import_nautobot()
    nautobot.sync_from(source)

    if summary:
        print_summary(source, nautobot)
    if field_mapping:
        print_fields_mapping(source)

    if dry_run:
        raise ValueError("Aborting the transaction due to the dry-run mode.")

    return source, nautobot
