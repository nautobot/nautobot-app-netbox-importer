"""NetBox to Nautobot importer."""

import json
from pathlib import Path
from typing import Union

from django.db.transaction import atomic
from nautobot.ipam.models import get_default_namespace

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

        related_wrapper = wrapper.adapter.get_wrapper(content_type)
        result = related_wrapper.get_pk_from_uid(object_id)
        target[field_name] = result
        related_wrapper.add_reference(result, wrapper)

    wrapper.add_importer(importer, field_name, "UUIDField")


def _define_choices(wrapper: SourceModelWrapper, field_name: FieldName) -> None:
    choices_wrapper = wrapper.adapter.get_wrapper("extras.customfieldchoice")

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

    location_type_wrapper = wrapper.adapter.get_wrapper("dcim.locationtype")
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

    wrapper.processed_fields.add("region")
    wrapper.processed_fields.add("site")

    location_wrapper = adapter.get_wrapper("dcim.location")
    site_wrapper = adapter.get_wrapper("dcim.site")
    region_wrapper = adapter.get_wrapper("dcim.region")

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
        units = source.get(field_name, None)
        if units:
            units = json.loads(units)
        if units:
            target[field_name] = [int(unit) for unit in units]
        else:
            target[field_name] = None

    wrapper.add_importer(importer, field_name, "JSONField")


# pylint: disable=too-many-statements
def _setup_models(netbox: SourceAdapter) -> None:
    """Setup NetBox models importers."""

    def _role_definition_factory(role_content_type: str):
        role_wrapper = netbox.define_model(role_content_type, "extras.role")
        role_wrapper.add_field("content_types", "content_types", AddFieldDuplicity.IGNORE)
        role_wrapper.add_field("color", "color", AddFieldDuplicity.IGNORE)

        def definition(wrapper: SourceModelWrapper, field_name: FieldName) -> None:
            wrapper.add_role_importer(field_name, role_wrapper)

        return definition

    netbox.ignore_fields(
        "mark_connected",  # Not supported in Nautobot
        "slug",  # Removed in Nautobot 2
        # Following fields fails for dcim.rack, see `./source.py` `_FORCE_FIELDS`
        "created",
        "last_updated",
    )

    netbox.ignore_models(
        "contenttypes.contenttype",
        "sessions.session",
        "dcim.cablepath",  # TBD recreate in Nautobot
        "admin.logentry",  # NetBox 3.0 TBD verify
        "users.userconfig",  # NetBox 3.0 TBD verify
        "auth.permission",  # NetBox 3.0 TBD verify
        "dcim.sitegroup",  # NetBox 3.1 TBD verify
        "ipam.asn",  # NetBox 3.1 TBD verify
        "ipam.iprange",  # NetBox 3.1 TBD verify
        "tenancy.contactgroup",  # NetBox 3.1 TBD verify
        "tenancy.contactrole",  # NetBox 3.1 TBD verify
        "tenancy.contact",  # NetBox 3.1 TBD verify
        "tenancy.contactassignment",  # NetBox 3.1 TBD verify
        "dcim.module",  # NetBox 3.2 TBD verify
        "dcim.modulebay",  # NetBox 3.2 TBD verify
        "dcim.modulebaytemplate",  # NetBox 3.2 TBD verify
        "dcim.moduletype",  # NetBox 3.2 TBD verify
    )

    netbox.define_model("extras.status", identifiers=["name"]).set_default_reference(
        name="Unknown",
        content_types=None,
    )
    netbox.define_model("extras.role")
    netbox.define_model("extras.customfieldchoice").set_fields(
        "custom_field",
        "value",
    )
    netbox.define_model("dcim.locationtype").set_default_reference(
        id="Unknown",
        name="Unknown",
        nestable=True,
        content_types=None,
    )
    location = netbox.define_model("dcim.location")
    location.set_fields(
        "status",
        location_type=_define_location_type,
        parent=_define_location,
        lft=None,
        rght=None,
        tree_id=None,
        level=None,
    )
    netbox.define_model("auth.user", "users.user", ["username"]).set_fields(
        last_login=None,
        is_superuser=None,  # NetBox 3.1 TBD verify
        password=None,  # NetBox 3.1 TBD verify
        user_permissions=None,  # NetBox 3.1 TBD verify
    )
    netbox.define_model("auth.group", identifiers=["name"]).set_fields(
        permissions=None,  # NetBox 3.1 TBD verify
    )
    netbox.define_model("circuits.circuit").set_fields(
        type="circuit_type",
        termination_a="circuit_termination_a",
        termination_z="circuit_termination_z",
    )
    netbox.define_model("dcim.rackreservation").set_fields(
        units=_define_units,
    )
    netbox.define_model("dcim.rack").set_fields(
        location=_define_location,
        role=_role_definition_factory("dcim.rackrole"),
    )
    netbox.define_model("dcim.cable").set_fields(
        termination_a="termination_a",
        termination_b="termination_b",
    )
    ipaddress = netbox.define_model("ipam.ipaddress")
    ipaddress.set_fields(
        role=_role_definition_factory("ipam.role"),
        vrf=None,  # TBD verify
    )
    ipaddress.nautobot.set_instance_defaults(namespace=get_default_namespace())
    netbox.define_model("ipam.vlan").set_fields(
        group="vlan_group",
        location=_define_location,
        role=_role_definition_factory("ipam.role"),
    )
    netbox.define_model("tenancy.tenant").set_fields(
        group="tenant_group",
    )
    netbox.define_model("virtualization.cluster").set_fields(
        type="cluster_type",
        group="cluster_group",
        location=_define_location,
    )
    netbox.define_model("circuits.circuittermination").set_fields(
        location=_define_location,
    )
    netbox.define_model("dcim.consoleport").set_fields(
        speed=None,  # TBD verify
    )
    netbox.define_model(
        "dcim.powerport",
    )
    netbox.define_model(
        "dcim.poweroutlet",
    )
    netbox.define_model("dcim.interfacetemplate").set_fields(
        module_type=None,  # TBD verify
    )
    netbox.define_model("dcim.interface").set_fields(
        "status",
        parent=None,  # TBD verify
        tagged_vlans=None,  # TBD verify
        module=None,  # TBD verify
    )
    netbox.define_model("dcim.frontport").set_fields(
        color=None,  # TBD verify
    )
    netbox.define_model("dcim.rearport").set_fields(
        color=None,  # TBD verify
    )
    netbox.define_model("dcim.devicerole", "extras.role").set_fields(
        vm_role=None,  # TBD verify
    )
    manufacturer = netbox.define_model("dcim.manufacturer")
    manufacturer.set_default_reference(
        id="Unknown",
        name="Unknown",
    )
    device_type = netbox.define_model("dcim.devicetype")
    device_type.set_fields(
        front_image=None,  # TBD verify
        rear_image=None,  # TBD verify
    )
    device_type.set_default_reference(
        id="Unknown",
        manufacturer=manufacturer.get_default_reference_pk(),
        model="Unknown",
    )
    netbox.define_model("dcim.moduletype", "dcim.devicetype")
    netbox.define_model("dcim.device").set_fields(
        location=_define_location,
        device_role=_role_definition_factory("dcim.devicerole"),
        local_context_data=None,  # TBD verify
    )
    netbox.define_model("dcim.powerpanel").set_fields(
        location=_define_location,
    )
    netbox.define_model("dcim.frontporttemplate").set_fields(
        rear_port="rear_port_template",
        color=None,  # TBD verify
    )
    netbox.define_model("dcim.rearporttemplate").set_fields(
        color=None,  # TBD verify
    )
    netbox.define_model("dcim.region", "dcim.location").set_fields(
        "status",
        location_type=_define_location_type,
        parent=_define_location,
        lft=None,
        rght=None,
        tree_id=None,
        level=None,
        group=None,
    )
    netbox.define_model("dcim.site", "dcim.location").set_fields(
        "status",
        location_type=_define_location_type,
        parent=_define_location,
        group=None,
    )
    netbox.define_model("ipam.prefix").set_fields(
        location=_define_location,
        role=_role_definition_factory("ipam.role"),
        is_pool=None,  # TBD verify
        mark_utilized=None,  # TBD verify
        vrf=None,  # TBD verify
    )
    netbox.define_model("ipam.vrf").set_fields(
        enforce_unique=None,  # TBD verify
    )
    netbox.define_model("ipam.aggregate", "ipam.prefix").set_fields(
        "status",
    )
    netbox.define_model("ipam.vlan").set_fields(
        min_vid=None,  # TBD verify
        max_vid=None,  # TBD verify
    )
    netbox.define_model("ipam.vlangroup").set_fields(
        scope_id=None,  # TBD verify
        scope_type=None,  # TBD verify
        min_vid=None,  # TBD verify
        max_vid=None,  # TBD verify
    )
    netbox.define_model("extras.customfield").set_fields(
        name="key",
        choices=_define_choices,
    )
    netbox.define_model("tenancy.tenantgroup").set_fields(
        lft=None,
        rght=None,
        tree_id=None,
        level=None,
    )
    virtual_machine = netbox.define_model("virtualization.virtualmachine")
    virtual_machine.set_fields(
        role=_role_definition_factory("dcim.devicerole"),
        local_context_data=None,  # TBD verify
    )
    netbox.define_model("virtualization.vminterface").set_fields(
        "status",
        parent=None,  # TBD verify
    )
    netbox.define_model("dcim.poweroutlettemplate").set_fields(
        power_port="power_port_template",
    )
    netbox.define_model("extras.taggeditem").set_fields(
        object_id=_define_tagged_object,
        content_types="content_types",
    )


@atomic
def sync_to_nautobot(file_path: Union[str, Path], dry_run=True, print_summary=True) -> SourceAdapter:
    """Import a NetBox export file."""

    def read_source_file():
        with open(file_path, "r", encoding="utf8") as file:
            data = json.load(file)

        for item in data:
            content_type = item["model"]
            netbox_pk = item.get("pk", None)
            source_data = item["fields"]
            if netbox_pk:
                source_data["id"] = netbox_pk
            yield SourceRecord(content_type, source_data)

    netbox = SourceAdapter("NetBox")

    _setup_models(netbox)

    netbox.import_data(read_source_file)

    nautobot = netbox.import_nautobot()
    nautobot.sync_from(netbox)

    if print_summary:
        netbox.print_summary(nautobot)

    if dry_run:
        raise ValueError("Aborting the transaction due to the dry-run mode.")

    return netbox
