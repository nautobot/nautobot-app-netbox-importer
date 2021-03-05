"""DCIM model class definitions for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-many-ancestors
from typing import Any, List, Optional

import nautobot.dcim.models as dcim

from .abstract import (
    ArrayField,
    BaseInterfaceMixin,
    CableTerminationMixin,
    ComponentModel,
    ComponentTemplateModel,
    ConfigContextModelMixin,
    MPTTModelMixin,
    OrganizationalModel,
    PrimaryModel,
    StatusModelMixin,
)
from .references import (
    foreign_key_field,
    ClusterRef,
    ContentTypeRef,
    DeviceRef,
    DeviceRoleRef,
    DeviceTypeRef,
    IPAddressRef,
    InterfaceRef,
    InventoryItemRef,
    ManufacturerRef,
    PlatformRef,
    PowerPanelRef,
    PowerPortRef,
    PowerPortTemplateRef,
    RackGroupRef,
    RackRef,
    RackRoleRef,
    RearPortRef,
    RearPortTemplateRef,
    RegionRef,
    SiteRef,
    TenantRef,
    UserRef,
    VLANRef,
    VirtualChassisRef,
)


class Cable(StatusModelMixin, PrimaryModel):
    """A physical connection between two endpoints."""

    _modelname = "cable"
    _identifiers = ("termination_a_type", "termination_a_id")
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "termination_b_type",
        "termination_b_id",
        "type",
        "label",
        "color",
        "length",
        "length_unit",
    )
    _nautobot_model = dcim.Cable

    termination_a_type: ContentTypeRef
    _termination_a_id = foreign_key_field("*termination_a_type")
    termination_a_id: _termination_a_id
    termination_b_type: ContentTypeRef
    _termination_b_id = foreign_key_field("*termination_b_type")
    termination_b_id: _termination_b_id
    type: str
    label: str
    color: str
    length: Optional[int]
    length_unit: str


class ConsolePort(CableTerminationMixin, ComponentModel):
    """A physical console port within a Device."""

    _modelname = "consoleport"
    _attributes = (*ComponentModel._attributes, *CableTerminationMixin._attributes, "type")
    _nautobot_model = dcim.ConsolePort

    type: str


class ConsolePortTemplate(ComponentTemplateModel):
    """A template for a ConsolePort."""

    _modelname = "consoleporttemplate"
    _attributes = (*ComponentTemplateModel._attributes, "type")
    _nautobot_model = dcim.ConsolePortTemplate

    type: str


class ConsoleServerPort(CableTerminationMixin, ComponentModel):
    """A physical port that provides access to console ports."""

    _modelname = "consoleserverport"
    _attributes = (*ComponentModel._attributes, *CableTerminationMixin._attributes, "type")
    _nautobot_model = dcim.ConsoleServerPort

    type: str


class ConsoleServerPortTemplate(ComponentTemplateModel):
    """A template for a ConsoleServerPort."""

    _modelname = "consoleserverporttemplate"
    _attributes = (*ComponentTemplateModel._attributes, "type")
    _nautobot_model = dcim.ConsoleServerPortTemplate

    type: str


class Device(ConfigContextModelMixin, StatusModelMixin, PrimaryModel):
    """A Device represents a piece of physical hardware mounted within a Rack."""

    _modelname = "device"
    # Although dcim.Device defines (site, tenant, name) as a unique_together constraint,
    # multiple devices in the same site/tenant may coexist with a NULL name because NULL != NULL.
    # Similarly (rack, position, face) is unique_together but multiple un-racked devices may coexist.
    # Similarly (virtual_chassis, vc_position) is unique_together but multiple non-vc devices may coexist.
    # In short, to avoid treating distinct Device records incorrectly as duplicates, we
    # need to consider **most attributes** as "identifiers" of a unique Device.
    _identifiers = (
        "site",
        "tenant",
        "name",
        "rack",
        "position",
        "face",
        "vc_position",
        "vc_priority",
        "device_type",
        "device_role",
        "platform",
        "serial",
        "asset_tag",
        "cluster",
    )
    _attributes = (
        *PrimaryModel._attributes,
        *ConfigContextModelMixin._attributes,
        *StatusModelMixin._attributes,
        # Due to model loading order, VirtualChassis references will initially be None and
        # will only later be set; since a model's identifiers may not change after instantiation,
        # we cannot treat this as an identifier.
        "virtual_chassis",
        # Due to model loading order, IPAddress references will initially be None and will
        # only later be set; since a model's identifiers may not change after instantiation,
        # we cannot treat these as identifiers.
        "primary_ip4",
        "primary_ip6",
        # Highly unlikely that two Devices will be identical in all respects save their comments;
        # plus comments are the field most likely to change between subsequent data imports.
        "comments",
    )
    _nautobot_model = dcim.Device

    site: Optional[SiteRef]
    tenant: Optional[TenantRef]
    name: Optional[str]
    rack: Optional[RackRef]
    position: Optional[int]
    face: str  # may not be None but may be empty
    vc_position: Optional[int]
    vc_priority: Optional[int]
    device_type: DeviceTypeRef
    device_role: DeviceRoleRef
    platform: Optional[PlatformRef]
    serial: str  # may not be None but may be empty
    asset_tag: Optional[str]
    cluster: Optional[ClusterRef]

    virtual_chassis: Optional[VirtualChassisRef]
    primary_ip4: Optional[IPAddressRef]
    primary_ip6: Optional[IPAddressRef]
    comments: str


class DeviceBay(ComponentModel):
    """An empty space within a Device which can house a child Device."""

    _modelname = "devicebay"
    _attributes = (*ComponentModel._attributes, "installed_device")
    _nautobot_model = dcim.DeviceBay

    installed_device: Optional[DeviceRef]


class DeviceBayTemplate(ComponentTemplateModel):
    """A template for a DeviceBay."""

    _modelname = "devicebaytemplate"
    _nautobot_model = dcim.DeviceBayTemplate


class DeviceRole(OrganizationalModel):
    """Devices are organized by functional role."""

    _modelname = "devicerole"
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "slug", "color", "vm_role", "description")
    _nautobot_model = dcim.DeviceRole

    name: str
    slug: str
    color: str
    vm_role: bool
    description: str


class DeviceType(PrimaryModel):
    """A DeviceType represents a particular make and model of device."""

    _modelname = "devicetype"
    _identifiers = ("manufacturer", "model")
    _attributes = (
        *PrimaryModel._attributes,
        "slug",
        "part_number",
        "u_height",
        "is_full_depth",
        "subdevice_role",
        # TODO "front_image", "rear_image",
        "comments",
    )
    _nautobot_model = dcim.DeviceType

    manufacturer: ManufacturerRef
    model: str
    slug: str
    part_number: str
    u_height: int
    is_full_depth: bool
    subdevice_role: str
    # front_image
    # rear_image
    comments: str


class FrontPort(CableTerminationMixin, ComponentModel):
    """A pass-through port on the front of a Device."""

    _modelname = "frontport"
    _attributes = (
        *ComponentModel._attributes,
        *CableTerminationMixin._attributes,
        "type",
        "rear_port",
        "rear_port_position",
    )
    _nautobot_model = dcim.FrontPort

    type: str
    rear_port: RearPortRef
    rear_port_position: int


class FrontPortTemplate(ComponentTemplateModel):
    """A template for a FrontPort."""

    _modelname = "frontporttemplate"
    _attributes = (*ComponentTemplateModel._attributes, "type", "rear_port", "rear_port_position")
    _nautobot_model = dcim.FrontPortTemplate

    type: str
    rear_port: RearPortTemplateRef
    rear_port_position: int


class Interface(BaseInterfaceMixin, CableTerminationMixin, ComponentModel):
    """A network interface within a Device."""

    _modelname = "interface"
    _attributes = (
        *ComponentModel._attributes,
        *CableTerminationMixin._attributes,
        *BaseInterfaceMixin._attributes,
        "lag",
        "type",
        "mgmt_only",
        "untagged_vlan",
        "tagged_vlans",
    )
    _nautobot_model = dcim.Interface

    lag: Optional[InterfaceRef]
    type: str
    mgmt_only: bool
    untagged_vlan: Optional[VLANRef]
    tagged_vlans: List[VLANRef] = []


class InterfaceTemplate(ComponentTemplateModel):
    """A template for a physical data interface."""

    _modelname = "interfacetemplate"
    _attributes = (*ComponentTemplateModel._attributes, "type", "mgmt_only")
    _nautobot_model = dcim.InterfaceTemplate

    type: str
    mgmt_only: bool


class InventoryItem(MPTTModelMixin, ComponentModel):
    """A serialized piece of hardware within a Device."""

    _modelname = "inventoryitem"
    _identifiers = ("device", "parent", "name")
    _attributes = (*ComponentModel._attributes, "manufacturer", "part_id", "serial", "asset_tag", "discovered")
    _nautobot_model = dcim.InventoryItem

    parent: Optional[InventoryItemRef]
    manufacturer: Optional[ManufacturerRef]
    part_id: str
    serial: str
    asset_tag: Optional[str]
    discovered: bool


class Manufacturer(OrganizationalModel):
    """A Manufacturer represents a company which produces hardware devices."""

    _modelname = "manufacturer"
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "slug", "description")
    _nautobot_model = dcim.Manufacturer

    name: str
    slug: str
    description: str


class Platform(OrganizationalModel):
    """Platform refers to the software or firmware running on a device."""

    _modelname = "platform"
    _identifiers = ("name",)
    _attributes = (
        *OrganizationalModel._attributes,
        "slug",
        "manufacturer",
        "napalm_driver",
        "napalm_args",
        "description",
    )
    _nautobot_model = dcim.Platform

    name: str
    slug: str
    manufacturer: Optional[ManufacturerRef]
    napalm_driver: str
    napalm_args: Optional[dict]
    description: str


class PowerFeed(CableTerminationMixin, StatusModelMixin, PrimaryModel):
    """An electrical circuit delivered from a PowerPanel."""

    _modelname = "powerfeed"
    _identifiers = ("power_panel", "name")
    _attributes = (
        *PrimaryModel._attributes,
        *CableTerminationMixin._attributes,
        *StatusModelMixin._attributes,
        "rack",
        "type",
        "supply",
        "phase",
        "voltage",
        "amperage",
        "max_utilization",
        "available_power",
        "comments",
    )
    _nautobot_model = dcim.PowerFeed

    power_panel: PowerPanelRef
    name: str

    rack: Optional[RackRef]
    type: str
    supply: str
    phase: str
    voltage: int
    amperage: int
    max_utilization: int
    available_power: int
    comments: str


class PowerOutlet(CableTerminationMixin, ComponentModel):
    """A physical power outlet (output) within a Device."""

    _modelname = "poweroutlet"
    _attributes = (*ComponentModel._attributes, *CableTerminationMixin._attributes, "type", "power_port", "feed_leg")
    _nautobot_model = dcim.PowerOutlet

    type: str
    power_port: Optional[PowerPortRef]
    feed_leg: str


class PowerOutletTemplate(ComponentTemplateModel):
    """A template for a PowerOutlet."""

    _modelname = "poweroutlettemplate"
    _attributes = (*ComponentTemplateModel._attributes, "type", "power_port", "feed_leg")
    _nautobot_model = dcim.PowerOutletTemplate

    type: staticmethod
    power_port: Optional[PowerPortTemplateRef]
    feed_leg: str


class PowerPanel(PrimaryModel):
    """A distribution point for electrical power."""

    _modelname = "powerpanel"
    _identifiers = (
        "site",
        "name",
    )
    _attributes = (*PrimaryModel._attributes, "rack_group")
    _nautobot_model = dcim.PowerPanel

    site: SiteRef
    name: str
    rack_group: Optional[RackGroupRef]


class PowerPort(CableTerminationMixin, ComponentModel):
    """A physical power supply (input) port within a Device."""

    _modelname = "powerport"
    _attributes = (
        *ComponentModel._attributes,
        *CableTerminationMixin._attributes,
        "type",
        "maximum_draw",
        "allocated_draw",
    )
    _nautobot_model = dcim.PowerPort

    type: str
    maximum_draw: Optional[int]
    allocated_draw: Optional[int]


class PowerPortTemplate(ComponentTemplateModel):
    """A template for a PowerPort."""

    _modelname = "powerporttemplate"
    _attributes = (*ComponentTemplateModel._attributes, "type", "maximum_draw", "allocated_draw")
    _nautobot_model = dcim.PowerPortTemplate

    type: str
    maximum_draw: Optional[int]
    allocated_draw: Optional[int]


class Rack(StatusModelMixin, PrimaryModel):
    """Devices are housed within Racks."""

    _modelname = "rack"
    _identifiers = ("group", "name")
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "facility_id",
        "site",
        "tenant",
        "role",
        "serial",
        "asset_tag",
        "type",
        "width",
        "u_height",
        "desc_units",
        "outer_width",
        "outer_depth",
        "outer_unit",
        "comments",
    )
    _nautobot_model = dcim.Rack

    group: Optional[RackGroupRef]
    name: str

    facility_id: Optional[str]
    site: SiteRef
    tenant: Optional[TenantRef]
    role: Optional[RackRoleRef]
    serial: str
    asset_tag: Optional[str]
    type: str
    width: int
    u_height: int
    desc_units: bool
    outer_width: Optional[int]
    outer_depth: Optional[int]
    outer_unit: str
    comments: str


class RackGroup(MPTTModelMixin, OrganizationalModel):
    """Racks can be grouped as subsets within a Site."""

    _modelname = "rackgroup"
    _identifiers = ("site", "name")
    _attributes = (*OrganizationalModel._attributes, "slug", "parent", "description")
    # Not all Racks belong to a RackGroup, so we don't treat Racks as a child.
    _nautobot_model = dcim.RackGroup

    site: SiteRef
    name: str
    slug: str
    parent: Optional[RackGroupRef]
    description: str


class RackReservation(PrimaryModel):
    """One or more reserved units within a Rack."""

    _modelname = "rackreservation"
    # RackReservation doesn't have a set of unique keys, but no two RackReservations for the same Rack should overlap
    _identifiers = ("rack", "units")
    _attributes = (*PrimaryModel._attributes, "tenant", "user", "description")
    _nautobot_model = dcim.RackReservation

    rack: RackRef
    units: ArrayField
    tenant: Optional[TenantRef]
    user: UserRef
    description: str


class RackRole(OrganizationalModel):
    """Racks can be organized by functional role."""

    _modelname = "rackrole"
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "slug", "color", "description")
    _nautobot_model = dcim.RackRole

    name: str
    slug: str
    color: str
    description: str


class RearPort(CableTerminationMixin, ComponentModel):
    """A pass-through port on the rear of a Device."""

    _modelname = "rearport"
    _attributes = (
        *ComponentModel._attributes,
        *CableTerminationMixin._attributes,
        "type",
        "positions",
    )
    _nautobot_model = dcim.RearPort

    type: str
    positions: int


class RearPortTemplate(ComponentTemplateModel):
    """A template for a RearPort."""

    _modelname = "rearporttemplate"
    _attributes = (*ComponentTemplateModel._attributes, "type", "positions")
    _nautobot_model = dcim.RearPortTemplate

    type: str
    positions: int


class Region(MPTTModelMixin, OrganizationalModel):
    """Sites can be grouped within geographic Regions."""

    _modelname = "region"
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "parent", "slug", "description")
    # Not all Sites belong to a Region, so we don't treat Sites as a child.
    _nautobot_model = dcim.Region

    name: str
    parent: Optional[RegionRef]
    slug: str
    description: str


class Site(StatusModelMixin, PrimaryModel):
    """A Site represents a geographic location within a network."""

    _modelname = "site"
    _identifiers = ("name",)
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "slug",
        "region",
        "tenant",
        "facility",
        "asn",
        "time_zone",
        "description",
        "physical_address",
        "shipping_address",
        "latitude",
        "longitude",
        "contact_name",
        "contact_phone",
        "contact_email",
        "comments",
    )
    _nautobot_model = dcim.Site

    name: str
    slug: str
    region: Optional[RegionRef]
    tenant: Optional[TenantRef]
    facility: str
    asn: Optional[int]
    time_zone: Optional[str]
    description: str
    physical_address: str
    shipping_address: str
    latitude: Optional[float]
    longitude: Optional[float]
    contact_name: str
    contact_phone: str
    contact_email: str
    comments: str

    _name: Optional[str]
    images: Any

    def __init__(self, *args, **kwargs):
        """Explicitly convert time_zone to a string if needed."""
        if "time_zone" in kwargs and kwargs["time_zone"]:
            kwargs["time_zone"] = str(kwargs["time_zone"])
        super().__init__(*args, **kwargs)


class VirtualChassis(PrimaryModel):
    """A collection of Devices which operate with a shared control plane."""

    _modelname = "virtualchassis"
    # As implemented in NetBox and Nautobot, none of these are required to be unique. Probably a bug!
    _identifiers = ("master", "name", "domain")
    _attributes = (*PrimaryModel._attributes,)
    _nautobot_model = dcim.VirtualChassis

    master: Optional[DeviceRef]
    name: str
    domain: str
