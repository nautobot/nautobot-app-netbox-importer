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


class Aggregate(PrimaryModel):
    """An aggregate exists at the root level of the IP address space hierarchy."""

    _modelname = "aggregate"
    # Technically Aggregate has no unique key except its PK. But this should be close:
    _identifiers = ("prefix", "rir")
    _attributes = (*PrimaryModel._attributes, "tenant", "date_added", "description")
    _nautobot_model = ipam.Aggregate

    prefix: netaddr.IPNetwork
    rir: RIRRef
    tenant: Optional[TenantRef]
    date_added: Optional[date]
    description: str

    def __init__(self, *args, **kwargs):
        """Clean up prefix to an IPNetwork before initializing as normal."""
        if isinstance(kwargs["prefix"], str):
            kwargs["prefix"] = netaddr.IPNetwork(kwargs["prefix"])
        super().__init__(*args, **kwargs)


class IPAddress(StatusModelMixin, PrimaryModel):
    """An individual IPv4 or IPv6 address."""

    _modelname = "ipaddress"
    # TODO IPAddress has no unique key except its PK. Hopefully this is close enough.
    _identifiers = ("address", "vrf", "tenant", "assigned_object_type", "assigned_object_id")
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
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
        if isinstance(kwargs["address"], str):
            kwargs["address"] = netaddr.IPNetwork(kwargs["address"])
        super().__init__(*args, **kwargs)


class Prefix(StatusModelMixin, PrimaryModel):
    """An IPv4 or IPv4 network, including mask."""

    _modelname = "prefix"
    # TODO: Prefix has no unique key except its PK. Hopefully this is close enough.
    _identifiers = ("prefix", "vrf", "site", "tenant")
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
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
        if isinstance(kwargs["prefix"], str):
            kwargs["prefix"] = netaddr.IPNetwork(kwargs["prefix"])
        super().__init__(*args, **kwargs)


class RIR(OrganizationalModel):
    """A Regional Internet Registry (RIR)."""

    _modelname = "rir"
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "slug", "is_private", "description")
    _nautobot_model = ipam.RIR

    name: str
    slug: str
    is_private: bool
    description: str


class Role(OrganizationalModel):
    """The functional role of a Prefix or VLAN."""

    _modelname = "role"  # ambiguous much?
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "slug", "weight", "description")
    _nautobot_model = ipam.Role

    name: str
    slug: str
    weight: int
    description: str


class RouteTarget(PrimaryModel):
    """A BGP extended community."""

    _modelname = "routetarget"
    _identifiers = ("name",)
    _attributes = (*PrimaryModel._attributes, "description", "tenant")
    _nautobot_model = ipam.RouteTarget

    name: str
    description: str
    tenant: Optional[TenantRef]


class Service(PrimaryModel):
    """A layer-four service such as HTTP or SSH."""

    _modelname = "service"
    _identifiers = ("device", "virtual_machine", "protocol", "ports")
    _attributes = (*PrimaryModel._attributes, "name", "ipaddresses", "description")
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
    _identifiers = ("group", "vid", "name", "site")
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
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
    _identifiers = ("site", "name")
    _attributes = (*OrganizationalModel._attributes, "slug", "description")
    _nautobot_model = ipam.VLANGroup

    name: str
    slug: str
    site: Optional[SiteRef]
    description: str


class VRF(PrimaryModel):
    """A virtual routing and forwarding (VRF) table."""

    _modelname = "vrf"
    _identifiers = ("name", "rd", "tenant")
    _attributes = (
        *PrimaryModel._attributes,
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
