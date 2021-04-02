"""Reference type declarations for nautobot-netbox-importer.

The classes defined in this module represent references (foreign-key and/or natural-key)
to an object of the given type.
"""

from uuid import UUID

from .validation import DiffSyncCustomValidationField, netbox_pk_to_nautobot_pk


class ForeignKeyField(DiffSyncCustomValidationField, UUID):
    """Convenience class for translating NetBox foreign keys to Nautobot UUID keys."""

    to_name: str

    @classmethod
    def validate(cls, value):
        """Map NetBox integer PKs to Nautobot UUID PKs, but leave dicts and UUIDs alone."""
        if isinstance(value, int):
            value = netbox_pk_to_nautobot_pk(cls.to_name, value)

        if isinstance(value, UUID):
            # cls(UUID) is an error, but cls(str(UUID)) reconstructs the original UUID
            value = str(value)
        elif isinstance(value, dict):
            # Model such as Status for which we might not know the PK, and instead are
            # referencing it as a dict of fields - leave it as a dict.
            return value

        return cls(value)


def foreign_key_field(to_name: str):
    """Helper method to create a type for a foreign key to a specific model."""

    class TaggedForeignKeyField(ForeignKeyField):
        """Convenience class for representing foreign keys (as natural keys) in DiffSync."""

    TaggedForeignKeyField.to_name = to_name
    return TaggedForeignKeyField


class ContentTypeRef(DiffSyncCustomValidationField, dict):
    """Foreign-key reference to a ContentType.

    Since ContentType is an automatically generated model, we can't control its PK.
    """

    to_name = "contenttype"

    @classmethod
    def validate(cls, value):
        """Coerce references to a Script or Report NetBox ContentType into a Job Nautobot ContentType ref."""
        if isinstance(value, (int, UUID)):
            # TODO is this still needed?
            value = {"pk": value}
        elif isinstance(value, dict):
            if "model" in value and value["model"] in ("script", "report"):
                value["model"] = "job"
        return cls(value)


class GroupRef(DiffSyncCustomValidationField, dict):
    """Foreign-key reference to a user Group."""

    to_name = "group"

    @classmethod
    def validate(cls, value):
        """This is another TODO."""
        # TODO double-check this, seems unnecessary/wrong?
        if isinstance(value, (int, UUID)):
            value = {"pk": value}
        return cls(value)


CableRef = foreign_key_field("cable")
CircuitRef = foreign_key_field("circuit")
CircuitTypeRef = foreign_key_field("circuittype")
ClusterRef = foreign_key_field("cluster")
ClusterGroupRef = foreign_key_field("clustergroup")
ClusterTypeRef = foreign_key_field("clustertype")
CustomFieldRef = foreign_key_field("customfield")
DeviceRef = foreign_key_field("device")
DeviceRoleRef = foreign_key_field("devicerole")
DeviceTypeRef = foreign_key_field("devicetype")
InterfaceRef = foreign_key_field("interface")
InventoryItemRef = foreign_key_field("inventoryitem")
IPAddressRef = foreign_key_field("ipaddress")
ManufacturerRef = foreign_key_field("manufacturer")
PermissionRef = foreign_key_field("permission")
PlatformRef = foreign_key_field("platform")
PowerPanelRef = foreign_key_field("powerpanel")
PowerPortRef = foreign_key_field("powerport")
PowerPortTemplateRef = foreign_key_field("powerporttemplate")
ProviderRef = foreign_key_field("provider")
RackRef = foreign_key_field("rack")
RackGroupRef = foreign_key_field("rackgroup")
RackRoleRef = foreign_key_field("rackrole")
RearPortRef = foreign_key_field("rearport")
RearPortTemplateRef = foreign_key_field("rearporttemplate")
RegionRef = foreign_key_field("region")
RoleRef = foreign_key_field("role")
RouteTargetRef = foreign_key_field("routetarget")
RIRRef = foreign_key_field("rir")
StatusRef = foreign_key_field("status")
SiteRef = foreign_key_field("site")
TagRef = foreign_key_field("tag")
TenantRef = foreign_key_field("tenant")
TenantGroupRef = foreign_key_field("tenantgroup")
UserRef = foreign_key_field("user")
VirtualChassisRef = foreign_key_field("virtualchassis")
VirtualMachineRef = foreign_key_field("virtualmachine")
VLANRef = foreign_key_field("vlan")
VLANGroupRef = foreign_key_field("vlangroup")
VRFRef = foreign_key_field("vrf")
