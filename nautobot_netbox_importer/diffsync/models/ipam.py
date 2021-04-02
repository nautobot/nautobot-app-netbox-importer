"""IPAM model class definitions for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-many-ancestors
from datetime import date
from typing import List, Optional

import netaddr
import nautobot.ipam.models as ipam

from .abstract import (
    ArrayField,
    OrganizationalModel,
    PrimaryModel,
    StatusModelMixin,
)
from .references import (
    foreign_key_field,
    ContentTypeRef,
    DeviceRef,
    IPAddressRef,
    RIRRef,
    RoleRef,
    RouteTargetRef,
    SiteRef,
    TenantRef,
    VLANGroupRef,
    VLANRef,
    VRFRef,
    VirtualMachineRef,
)


def network_from_components(network_bytes, prefix_length):
    """Given a network address as a byte string, and a prefix length, construct an IPNetwork object."""
    ipaddress = netaddr.IPAddress(int.from_bytes(network_bytes, "big"))
    return netaddr.IPNetwork(f"{ipaddress}/{prefix_length}")


class Aggregate(PrimaryModel):
    """An aggregate exists at the root level of the IP address space hierarchy."""

    _modelname = "aggregate"
    _attributes = (*PrimaryModel._attributes, "prefix", "rir", "tenant", "date_added", "description")
    _nautobot_model = ipam.Aggregate

    prefix: netaddr.IPNetwork
    rir: RIRRef
    tenant: Optional[TenantRef]
    date_added: Optional[date]
    description: str

    def __init__(self, *args, **kwargs):
        """Clean up prefix to an IPNetwork before initializing as normal."""
        if "prefix" in kwargs:
            # NetBox import
            if isinstance(kwargs["prefix"], str):
                kwargs["prefix"] = netaddr.IPNetwork(kwargs["prefix"])
        else:
            # Nautobot import
            kwargs["prefix"] = network_from_components(kwargs["network"], kwargs["prefix_length"])
            del kwargs["network"]
            del kwargs["broadcast"]
            del kwargs["prefix_length"]

        super().__init__(*args, **kwargs)


class IPAddress(StatusModelMixin, PrimaryModel):
    """An individual IPv4 or IPv6 address."""

    _modelname = "ipaddress"
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "address",
        "vrf",
        "tenant",
        "assigned_object_type",
        "assigned_object_id",
        "role",
        "nat_inside",
        "dns_name",
        "description",
    )
    _nautobot_model = ipam.IPAddress

    address: netaddr.IPNetwork  # not IPAddress
    vrf: Optional[VRFRef]
    tenant: Optional[TenantRef]
    assigned_object_type: Optional[ContentTypeRef]
    _assigned_object_id = foreign_key_field("*assigned_object_type")
    assigned_object_id: Optional[_assigned_object_id]
    role: str
    nat_inside: Optional[IPAddressRef]
    dns_name: str
    description: str

    def __init__(self, *args, **kwargs):
        """Clean up address to an IPNetwork before initializing as normal."""
        if "address" in kwargs:
            # Import from NetBox
            if isinstance(kwargs["address"], str):
                kwargs["address"] = netaddr.IPNetwork(kwargs["address"])
        else:
            # Import from Nautobot
            kwargs["address"] = network_from_components(kwargs["host"], kwargs["prefix_length"])
            del kwargs["host"]
            del kwargs["broadcast"]
            del kwargs["prefix_length"]
        super().__init__(*args, **kwargs)


class Prefix(StatusModelMixin, PrimaryModel):
    """An IPv4 or IPv4 network, including mask."""

    _modelname = "prefix"
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "prefix",
        "vrf",
        "site",
        "tenant",
        "vlan",
        "role",
        "is_pool",
        "description",
    )
    _nautobot_model = ipam.Prefix

    prefix: netaddr.IPNetwork
    vrf: Optional[VRFRef]
    site: Optional[SiteRef]
    tenant: Optional[TenantRef]
    vlan: Optional[VLANRef]
    role: Optional[RoleRef]
    is_pool: bool
    description: str

    def __init__(self, *args, **kwargs):
        """Clean up prefix to an IPNetwork before initializing as normal."""
        if "prefix" in kwargs:
            # NetBox import
            if isinstance(kwargs["prefix"], str):
                kwargs["prefix"] = netaddr.IPNetwork(kwargs["prefix"])
        else:
            # Nautobot import
            kwargs["prefix"] = network_from_components(kwargs["network"], kwargs["prefix_length"])
            del kwargs["network"]
            del kwargs["broadcast"]
            del kwargs["prefix_length"]
        super().__init__(*args, **kwargs)


class RIR(OrganizationalModel):
    """A Regional Internet Registry (RIR)."""

    _modelname = "rir"
    _attributes = (*OrganizationalModel._attributes, "name", "slug", "is_private", "description")
    _nautobot_model = ipam.RIR

    name: str
    slug: str
    is_private: bool
    description: str


class Role(OrganizationalModel):
    """The functional role of a Prefix or VLAN."""

    _modelname = "role"  # ambiguous much?
    _attributes = (*OrganizationalModel._attributes, "name", "slug", "weight", "description")
    _nautobot_model = ipam.Role

    name: str
    slug: str
    weight: int
    description: str


class RouteTarget(PrimaryModel):
    """A BGP extended community."""

    _modelname = "routetarget"
    _attributes = (*PrimaryModel._attributes, "name", "description", "tenant")
    _nautobot_model = ipam.RouteTarget

    name: str
    description: str
    tenant: Optional[TenantRef]


class Service(PrimaryModel):
    """A layer-four service such as HTTP or SSH."""

    _modelname = "service"
    _attributes = (
        *PrimaryModel._attributes,
        "device",
        "virtual_machine",
        "protocol",
        "ports",
        "name",
        "ipaddresses",
        "description",
    )
    _nautobot_model = ipam.Service

    device: Optional[DeviceRef]
    virtual_machine: Optional[VirtualMachineRef]
    protocol: str
    ports: ArrayField

    name: str
    ipaddresses: List[IPAddressRef]
    description: str


class VLAN(StatusModelMixin, PrimaryModel):
    """A distinct layer two forwarding domain."""

    _modelname = "vlan"
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "group",
        "vid",
        "name",
        "site",
        "tenant",
        "status",
        "role",
        "description",
    )
    _nautobot_model = ipam.VLAN

    name: str
    vid: int
    group: Optional[VLANGroupRef]
    site: Optional[SiteRef]
    tenant: Optional[TenantRef]
    role: Optional[RoleRef]
    description: str


class VLANGroup(OrganizationalModel):
    """An arbitrary collection of VLANs."""

    _modelname = "vlangroup"
    _attributes = (*OrganizationalModel._attributes, "site", "name", "slug", "description")
    _nautobot_model = ipam.VLANGroup

    name: str
    slug: str
    site: Optional[SiteRef]
    description: str


class VRF(PrimaryModel):
    """A virtual routing and forwarding (VRF) table."""

    _modelname = "vrf"
    _attributes = (
        *PrimaryModel._attributes,
        "name",
        "rd",
        "tenant",
        "enforce_unique",
        "description",
        "import_targets",
        "export_targets",
    )
    _nautobot_model = ipam.VRF

    name: str
    rd: Optional[str]
    tenant: Optional[TenantRef]

    enforce_unique: bool
    description: str
    import_targets: List[RouteTargetRef] = []
    export_targets: List[RouteTargetRef] = []
