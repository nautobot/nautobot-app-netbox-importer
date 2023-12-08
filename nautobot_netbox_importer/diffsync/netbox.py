"""NetBox to Nautobot importer."""

import json
from pathlib import Path
from typing import Union, Tuple

from django.db.transaction import atomic
from nautobot.ipam.models import get_default_namespace

from nautobot_netbox_importer.diffsync.nautobot import NautobotAdapter

from .base import EMPTY_VALUES
from .base import FieldName
from .base import RecordData
from .source import AddFieldDuplicity
from .source import SourceAdapter
from .source import SourceModelWrapper
from .source import SourceRecord


def _define_tagged_object(wrapper: SourceModelWrapper, field_name: FieldName) -> None:
    def importer(source: RecordData, target: RecordData) -> None:
        content_type = source.get("content_type", None)
        object_id = source.get(field_name, None)
        if not object_id or not content_type:
            target[field_name] = None
            return

        related_wrapper = wrapper.adapter.get_or_create_wrapper(content_type)
        result = related_wrapper.get_pk_from_uid(object_id)
        target[field_name] = result
        related_wrapper.add_reference(result, wrapper)

    wrapper.add_importer(importer, field_name, "UUIDField")


def _define_choices(wrapper: SourceModelWrapper, field_name: FieldName) -> None:
    choices_wrapper = wrapper.adapter.get_or_create_wrapper("extras.customfieldchoice")

    def importer(source: RecordData, target: RecordData) -> None:
        choices = source.get(field_name, None)
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

    wrapper.add_importer(importer)


def _name_from_wrapper(wrapper) -> str:
    """Return model name with upper cased first letter.

    e.g. `dcim.site` -> `Site`
    """
    name = wrapper.content_type.split(".")[1]
    return name[0].upper() + name[1:]


def _define_location_type(wrapper: SourceModelWrapper, field_name: FieldName) -> None:
    field_name = f"{field_name}_id"

    wrapper.set_references_forwarding("dcim.locationtype", field_name)

    location_type_wrapper = wrapper.adapter.get_or_create_wrapper("dcim.locationtype")
    name = _name_from_wrapper(wrapper)
    location_type_id = location_type_wrapper.cache_data({"id": name, "name": name, "nestable": True})

    def importer(_, target: RecordData) -> None:
        target[field_name] = location_type_id
        location_type_wrapper.add_reference(location_type_id, wrapper)

    wrapper.add_importer(importer, field_name, "UUIDField")


def _define_location(wrapper: SourceModelWrapper, field_name: FieldName) -> None:
    adapter = wrapper.adapter
    if field_name not in ["location", "parent"]:
        raise ValueError("_define_location only supports location and parent")
    field_name = f"{field_name}_id"

    wrapper.add_field("region", None, AddFieldDuplicity.IGNORE)
    wrapper.add_field("site", None, AddFieldDuplicity.IGNORE)

    location_wrapper = adapter.get_or_create_wrapper("dcim.location")
    site_wrapper = adapter.get_or_create_wrapper("dcim.site")
    region_wrapper = adapter.get_or_create_wrapper("dcim.region")

    def importer(source: RecordData, target: RecordData) -> None:
        parent = source.get("parent", None)
        location = source.get("location", None)
        site = source.get("site", None)
        region = source.get("region", None)

        if field_name == "parent_id" and parent:
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

        target[field_name] = result

    wrapper.add_importer(importer, field_name, "UUIDField")


def _define_units(wrapper: SourceModelWrapper, field_name: FieldName) -> None:
    def importer(source: RecordData, target: RecordData) -> None:
        # NetBox 3.4 units is `list[int]`, previous versions are JSON string with list of strings
        units = source.get(field_name, None)

        if units in EMPTY_VALUES:
            return

        if isinstance(units, str):
            units = json.loads(units)
            if units:
                units = [int(unit) for unit in units]

        target[field_name] = units

    wrapper.add_importer(importer, field_name, "JSONField")


# pylint: disable=too-many-statements
def _setup_source() -> SourceAdapter:
    """Setup NetBox models importers."""

    def _role_definition_factory(role_content_type: str):
        if role_content_type in adapter.wrappers:
            role_wrapper = adapter.wrappers[role_content_type]
        else:
            role_wrapper = adapter.configure_model(role_content_type, nautobot_content_type="extras.role")
        role_wrapper.add_field("content_types", "content_types", AddFieldDuplicity.IGNORE)
        # role_wrapper.add_field("color", "color", AddFieldDuplicity.IGNORE)

        def definition(wrapper: SourceModelWrapper, field_name: FieldName) -> None:
            wrapper.add_role_importer(field_name, role_wrapper)

        return definition

    adapter = SourceAdapter(name="NetBox")
    adapter.configure(
        ignore_fields=(
            # Following fields fails for dcim.rack, see `./source.py` `_FORCE_FIELDS`
            "created",
            "last_updated",
        ),
        ignore_content_types={
            "contenttypes.contenttype": None,  # Nautobot has own content types
            "sessions.session": None,  # Nautobot has own sessions
            "dcim.cablepath": None,  # Recreated in Nautobot
            "admin.logentry": None,  # NetBox 3.0 TBD verify
            "users.userconfig": None,  # NetBox 3.0 TBD verify
            "auth.permission": None,  # NetBox 3.0 TBD verify
            "dcim.sitegroup": None,  # NetBox 3.1 TBD verify
            "ipam.asn": None,  # NetBox 3.1 TBD verify
            "ipam.iprange": None,  # NetBox 3.1 TBD verify
            "tenancy.contactgroup": None,  # NetBox 3.1 TBD verify
            "tenancy.contactrole": None,  # NetBox 3.1 TBD verify
            "tenancy.contact": None,  # NetBox 3.1 TBD verify
            "tenancy.contactassignment": None,  # NetBox 3.1 TBD verify
            "dcim.module": None,  # NetBox 3.2 TBD verify
            "dcim.modulebay": None,  # NetBox 3.2 TBD verify
            "dcim.modulebaytemplate": None,  # NetBox 3.2 TBD verify
            "dcim.moduletype": None,  # NetBox 3.2 TBD verify
        },
    )

    adapter.configure_model(
        "extras.status",
        identifiers=["name"],
        default_reference={
            "name": "Unknown",
            "content_types": [],
        },
    )
    # TBD: Verify if necessary
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
            "content_types": "content_types",
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
            "password": None,  # NetBox 3.1 TBD verify
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
        "circuits.circuit",
        fields={
            "type": "circuit_type",
            "termination_a": "circuit_termination_a",
            "termination_z": "circuit_termination_z",
        },
    )
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
            "role": _role_definition_factory("dcim.rackrole"),
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
        "tenancy.tenant",
        fields={
            "group": "tenant_group",
        },
    )
    adapter.configure_model(
        "virtualization.cluster",
        fields={
            "type": "cluster_type",
            "group": "cluster_group",
            "location": _define_location,
        },
    )
    adapter.configure_model(
        "circuits.circuittermination",
        fields={
            "location": _define_location,
        },
    )
    adapter.configure_model(
        "dcim.interface",
        fields={
            "status": "status",
            "parent": None,  # TBD verify
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
            "device_role": _role_definition_factory("dcim.devicerole"),
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
    ipaddress = adapter.configure_model(
        "ipam.ipaddress",
        fields={
            "role": _role_definition_factory("ipam.role"),
        },
    )
    ipaddress.nautobot.set_instance_defaults(namespace=get_default_namespace())
    adapter.configure_model(
        "ipam.prefix",
        fields={
            "location": _define_location,
            "role": _role_definition_factory("ipam.role"),
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
            "role": _role_definition_factory("ipam.role"),
        },
    )
    adapter.configure_model(
        "virtualization.virtualmachine",
        fields={
            "role": _role_definition_factory("dcim.devicerole"),
        },
    )
    adapter.configure_model(
        "virtualization.vminterface",
        fields={
            "status": "status",
            "parent": None,  # TBD verify
        },
    )
    adapter.configure_model(
        "dcim.poweroutlettemplate",
        fields={
            "power_port": "power_port_template",
        },
    )

    return adapter


@atomic
def sync_to_nautobot(
    file_path: Union[str, Path], dry_run=True, print_summary=True
) -> Tuple[SourceAdapter, NautobotAdapter]:
    """Import a NetBox export file."""

    def process_cable_termination(source_data: RecordData) -> str:
        # NetBox 3.3 split the dcim.cable model into dcim.cable and dcim.cabletermination models.
        # TBD: Resolve this in the specific wrappers for dcim.cable and dcim.cableterminationa and dcim.cableterminationz to avoid overriding the default values
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

    source = _setup_source()

    source.import_data(read_source_file)

    nautobot = source.import_nautobot()
    nautobot.sync_from(source)

    validation_errors = nautobot.get_validation_errors()
    if print_summary:
        source.print_summary(validation_errors)

    if dry_run:
        raise ValueError("Aborting the transaction due to the dry-run mode.")

    return source, nautobot
