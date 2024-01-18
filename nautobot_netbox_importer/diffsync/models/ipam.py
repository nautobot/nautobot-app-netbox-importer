"""NetBox to Nautobot IPAM Models Mapping."""
from nautobot.ipam.models import get_default_namespace

from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import fields

from .locations import define_location


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
