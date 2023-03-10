"""DCIM model class definitions for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-many-ancestors
from typing import Any, List, Mapping, Optional

from diffsync import DiffSync
from pydantic import validator, root_validator
import structlog

import nautobot.dcim.models as dcim
from nautobot.dcim.choices import InterfaceTypeChoices

from .abstract import (
    ArrayField,
    BaseInterfaceMixin,
    CableTerminationMixin,
    ComponentModel,
    ComponentTemplateModel,
    ConfigContextModelMixin,
    MPTTModelMixin,
    NautobotBaseModel,
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


INTERFACE_TYPE_CHOICES = set(InterfaceTypeChoices.values())


logger = structlog.get_logger()


class Cable(StatusModelMixin, PrimaryModel):
    """A physical connection between two endpoints."""

    _modelname = "cable"
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "termination_a_type",
        "termination_a_id",
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
    _attributes = (
        *PrimaryModel._attributes,
        *ConfigContextModelMixin._attributes,
        *StatusModelMixin._attributes,
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
        "virtual_chassis",
        "primary_ip4",
        "primary_ip6",
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
    _attributes = (*OrganizationalModel._attributes, "name", "slug", "color", "vm_role", "description")
    _nautobot_model = dcim.DeviceRole

    name: str
    slug: str
    color: str
    vm_role: bool
    description: str


class DeviceType(PrimaryModel):
    """A DeviceType represents a particular make and model of device."""

    _modelname = "devicetype"
    _attributes = (
        *PrimaryModel._attributes,
        "manufacturer",
        "model",
        "slug",
        "part_number",
        "u_height",
        "is_full_depth",
        "subdevice_role",
        "front_image",
        "rear_image",
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
    front_image: str
    rear_image: str
    comments: str

    @validator("front_image", pre=True)
    def front_imagefieldfile_to_str(cls, value):  # pylint: disable=no-self-argument,no-self-use
        """Convert ImageFieldFile objects to strings."""
        if hasattr(value, "name"):
            value = value.name
        return value

    @validator("rear_image", pre=True)
    def rear_imagefieldfile_to_str(cls, value):  # pylint: disable=no-self-argument,no-self-use
        """Convert ImageFieldFile objects to strings."""
        if hasattr(value, "name"):
            value = value.name
        return value


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

    @root_validator
    def invalid_type_to_other(cls, values):  # pylint: disable=no-self-argument,no-self-use
        """Fixup Invalid Interface.type values for Nautobot."""
        int_type = values["type"]
        if int_type not in INTERFACE_TYPE_CHOICES:
            values["type"] = "other"
            int_name = values["name"]
            int_device = values["device"]
            device = dcim.Device.objects.filter(pk=int_device)
            if device:
                int_device = device.first().name
            logger.warning(
                "Encountered a NetBox Interface.type that is not valid in this version of Nautobot, will convert it",
                interface_name=int_name,
                interface_device_name_or_pk=int_name,
                netbox_type=int_type,
                nautobot_type="other",
            )
        return values


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
    _attributes = (
        *ComponentModel._attributes,
        "device",
        "parent",
        "name",
        "manufacturer",
        "part_id",
        "serial",
        "asset_tag",
        "discovered",
    )
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
    _attributes = (*OrganizationalModel._attributes, "name", "slug", "description")
    _nautobot_model = dcim.Manufacturer

    name: str
    slug: str
    description: str


class Platform(OrganizationalModel):
    """Platform refers to the software or firmware running on a device."""

    _modelname = "platform"
    _attributes = (
        *OrganizationalModel._attributes,
        "name",
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
    _attributes = (
        *PrimaryModel._attributes,
        *CableTerminationMixin._attributes,
        *StatusModelMixin._attributes,
        "power_panel",
        "name",
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

    type: str
    power_port: Optional[PowerPortTemplateRef]
    feed_leg: str


class PowerPanel(PrimaryModel):
    """A distribution point for electrical power."""

    _modelname = "powerpanel"
    _attributes = (*PrimaryModel._attributes, "site", "name", "rack_group")
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
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "group",
        "name",
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
    _attributes = (*OrganizationalModel._attributes, "site", "name", "slug", "parent", "description")
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
    _attributes = (*PrimaryModel._attributes, "rack", "units", "tenant", "user", "description")
    _nautobot_model = dcim.RackReservation

    rack: RackRef
    units: ArrayField
    tenant: Optional[TenantRef]
    user: UserRef
    description: str


class RackRole(OrganizationalModel):
    """Racks can be organized by functional role."""

    _modelname = "rackrole"
    _attributes = (*OrganizationalModel._attributes, "name", "slug", "color", "description")
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
    _attributes = (*OrganizationalModel._attributes, "name", "parent", "slug", "description")
    # Not all Sites belong to a Region, so we don't treat Sites as a child.
    _nautobot_model = dcim.Region

    name: str
    parent: Optional[RegionRef]
    slug: str
    description: str


class Site(StatusModelMixin, PrimaryModel):
    """A Site represents a geographic location within a network."""

    _modelname = "site"
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "name",
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
    _attributes = (*PrimaryModel._attributes, "master", "name", "domain")
    _nautobot_model = dcim.VirtualChassis

    master: Optional[DeviceRef]
    name: str
    domain: str

    @classmethod
    def create(cls, diffsync: DiffSync, ids: Mapping, attrs: Mapping) -> Optional[NautobotBaseModel]:
        """Create an instance of this model, both in Nautobot and in DiffSync.

        There is an odd behavior (bug?) in Nautobot 1.0.0 wherein when creating a VirtualChassis with
        a predefined "master" Device, it changes the master device's position to 1 regardless of what
        it was previously configured to. This will cause us problems later when we attempt to associate
        member devices with the VirtualChassis if there's a member that's supposed to be using position 1.
        So, we take it upon ourselves to overrule Nautobot and put the master back into the position it's
        supposed to be in.
        """
        diffsync_record = super().create(diffsync, ids, attrs)
        if diffsync_record is not None and diffsync_record.master is not None:  # pylint: disable=no-member
            nautobot_record = cls.nautobot_model().objects.get(**ids)
            nautobot_master = nautobot_record.master
            diffsync_master = diffsync.get("device", str(nautobot_master.pk))
            if nautobot_master.vc_position != diffsync_master.vc_position:
                logger.debug(
                    "Fixing up master device vc_position",
                    virtual_chassis=diffsync_record,
                    incorrect_position=nautobot_master.vc_position,
                    correct_position=diffsync_master.vc_position,
                )
                nautobot_master.vc_position = diffsync_master.vc_position
                nautobot_master.save()

        return diffsync_record
