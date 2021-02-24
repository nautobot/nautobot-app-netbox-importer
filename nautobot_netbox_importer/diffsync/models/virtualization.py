"""Virtualization model class definitions for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-many-ancestors
from typing import List, Optional

import nautobot.virtualization.models as virtualization

from .abstract import (
    BaseInterfaceMixin,
    ConfigContextModelMixin,
    CustomFieldModelMixin,
    NautobotBaseModel,
    OrganizationalModel,
    PrimaryModel,
    StatusModelMixin,
)
from .references import (
    ClusterGroupRef,
    ClusterRef,
    ClusterTypeRef,
    DeviceRoleRef,
    IPAddressRef,
    PlatformRef,
    SiteRef,
    TenantRef,
    VLANRef,
    VirtualMachineRef,
)


class ClusterType(OrganizationalModel):
    """A type of Cluster."""

    _modelname = "clustertype"
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "slug", "description")
    _nautobot_model = virtualization.ClusterType

    name: str
    slug: str
    description: str


class ClusterGroup(OrganizationalModel):
    """An organizational group of Clusters."""

    _modelname = "clustergroup"
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "slug", "description")
    _nautobot_model = virtualization.ClusterGroup

    name: str
    slug: str
    description: str


class Cluster(PrimaryModel):
    """A cluster of VirtualMachines, optionally associated with one or more Devices."""

    _modelname = "cluster"
    _identifiers = ("name",)
    _attributes = (*PrimaryModel._attributes, "type", "group", "tenant", "site", "comments")
    _nautobot_model = virtualization.Cluster

    name: str
    type: ClusterTypeRef
    group: Optional[ClusterGroupRef]
    tenant: Optional[TenantRef]
    site: Optional[SiteRef]
    comments: str


class VirtualMachine(ConfigContextModelMixin, StatusModelMixin, PrimaryModel):
    """A virtual machine which runs inside a Cluster."""

    _modelname = "virtualmachine"
    _identifiers = ("cluster", "tenant", "name")
    _attributes = (
        *ConfigContextModelMixin._attributes,
        *StatusModelMixin._attributes,
        *PrimaryModel._attributes,
        "platform",
        "role",
        "primary_ip4",
        "primary_ip6",
        "vcpus",
        "memory",
        "disk",
        "comments",
    )
    _nautobot_model = virtualization.VirtualMachine

    cluster: ClusterRef
    tenant: Optional[TenantRef]
    name: str
    platform: Optional[PlatformRef]
    role: Optional[DeviceRoleRef]
    primary_ip4: Optional[IPAddressRef]
    primary_ip6: Optional[IPAddressRef]
    vcpus: Optional[int]
    memory: Optional[int]
    disk: Optional[int]
    comments: str


class VMInterface(CustomFieldModelMixin, BaseInterfaceMixin, NautobotBaseModel):
    """An interface on a VirtualMachine."""

    _modelname = "vminterface"
    _identifiers = ("virtual_machine", "name")
    _attributes = (
        *CustomFieldModelMixin._attributes,
        *BaseInterfaceMixin._attributes,
        "description",
        "untagged_vlan",
        "tagged_vlans",
    )
    _nautobot_model = virtualization.VMInterface

    virtual_machine: VirtualMachineRef
    name: str

    description: str
    untagged_vlan: Optional[VLANRef]
    tagged_vlans: List[VLANRef] = []
