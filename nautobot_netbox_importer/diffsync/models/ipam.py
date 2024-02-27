"""NetBox to Nautobot IPAM Models Mapping."""

from nautobot.ipam.models import get_default_namespace

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.generator import DiffSyncBaseModel
from nautobot_netbox_importer.generator import InvalidChoiceValueIssue
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import fields

from .locations import define_location


def _fhrp_protocol_fallback(field: SourceField, source: RecordData, target: DiffSyncBaseModel, _) -> None:
    """Fallback for FHRPGroup protocol."""
    value = field.get_source_value(source)
    if value.startswith("vrrp"):
        target_value = "vrrp"
    else:
        return

    field.set_nautobot_value(target, target_value)
    raise InvalidChoiceValueIssue(field, value, target_value)


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox IPAM models to Nautobot."""
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
        nautobot_content_type="ipam.prefix",
    )
    adapter.configure_model(
        "ipam.vlan",
        fields={
            "group": "vlan_group",
            "location": define_location,
            "role": fields.role(adapter, "ipam.role"),
        },
    )
    adapter.configure_model(
        "ipam.FHRPGroup",
        nautobot_content_type="dcim.InterfaceRedundancyGroup",
        fields={
            "protocol": fields.fallback(callback=_fhrp_protocol_fallback),
        },
    )
