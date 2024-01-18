# NetBox Import Summary

This document describes the summary of mapping from NetBox 3.6 to Nautobot 2.1.0. Mappings for other versions may vary based on available models and fields.

The summary is generated when running the following command:

```shell
nautobot-server import_netbox \
    --dry-run \
    --summary \
    --field-mapping \
    --bypass-data-validation \
    /tmp/netbox_data.json
```

The summary is divided into several sections as described below.

## DiffSync Summary

The first section is the import summary. It shows a basic summary from the underlying [DiffSync](https://github.com/networktocode/diffsync) library.

```
= Import Summary: ==============================================================
- DiffSync Summary: ------------------------------------------------------------
create: 5865
update: 1
delete: 0
no-change: 4
skip: 119
```

In this case, skipped objects are `ContentType` objects, as these are not directly imported into Nautobot.

`update` and `no-change` are those objects that are already in Nautobot. Typically, these are `User`, `Status`, `Role` or similar objects. Detailed information about these objects is shown in the debug log.

## Nautobot Models Summary

This section shows the number of objects that are imported for each Nautobot model.

```
- Nautobot Models Summary: -----------------------------------------------------
extras.customfield: 1
extras.status: 6
extras.role: 18
dcim.locationtype: 6
dcim.location: 95
tenancy.tenantgroup: 1
tenancy.tenant: 11
users.user: 6
circuits.circuit: 29
circuits.circuittermination: 45
circuits.circuittype: 4
circuits.provider: 9
circuits.providernetwork: 1
dcim.devicetype: 15
dcim.consoleport: 41
dcim.consoleporttemplate: 11
dcim.device: 72
dcim.devicebay: 14
dcim.frontport: 912
dcim.frontporttemplate: 120
dcim.interface: 1586
dcim.interfacetemplate: 300
dcim.powerfeed: 48
dcim.poweroutlet: 104
dcim.poweroutlettemplate: 8
dcim.powerpanel: 4
dcim.powerport: 75
dcim.powerporttemplate: 26
dcim.rack: 42
dcim.rearport: 630
dcim.rearporttemplate: 73
dcim.cable: 108
ipam.prefix: 94
contenttypes.contenttype: 119
extras.taggeditem: 72
auth.group: 1
dcim.rackreservation: 2
dcim.manufacturer: 15
ipam.ipaddress: 180
ipam.vlan: 63
virtualization.cluster: 32
virtualization.virtualmachine: 180
virtualization.vminterface: 720
dcim.devicebaytemplate: 14
dcim.platform: 3
dcim.virtualchassis: 4
ipam.vrf: 6
ipam.routetarget: 12
ipam.rir: 8
ipam.vlangroup: 7
extras.tag: 26
virtualization.clustertype: 6
virtualization.clustergroup: 4
```

## Validation Issues

This section shows validation issues that were found during the import process grouped by the Nautobot content type with a total summary at the end.

These issues are not necessarily errors, but may be warnings or other issues that should be reviewed. See the [Data Validation and Error Handling chapter](./app_use_cases.md#data-validation-and-error-handling) for details.

```
- Validation issues: -----------------------------------------------------------
. dcim.powerfeed: 48 ...........................................................
ValidationIssue(uid=UUID('0e23ee26-033e-5cfd-8bce-b5ef5909e13c'), name='P2-10B', error=ValidationError(['Rack R202 (Row 2) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('38f5aa36-561b-5cd8-8362-9d093ff7b89a'), name='P1-15A', error=ValidationError(['Rack R207 (Row 2) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('872d498b-e156-57b9-8f1d-f595c31ef703'), name='P3-5A', error=ValidationError(['Rack R305 (Row 3) and power panel Panel 3 (MDF) are in different locations']))
ValidationIssue(uid=UUID('17a0b412-4187-51a2-a238-901b3a275bcd'), name='P1-14A', error=ValidationError(['Rack R206 (Row 2) and power panel Panel 1 (MDF) are in different locations']))
...
................................................................................
Total validation issues: 48
```

## Content Types Mapping Deviations

This section shows deviations from NetBox content type to Nautobot content type. Only those content types that differ between NetBox and Nautobot are shown.

`EXTENDS` means that the NetBox object of such a content type is merged with another object. For example, `CableTermination` objects are merged with the corresponding `Cable` objects before diffing and importing them into Nautobot.

```
- Content Types Mapping Deviations: --------------------------------------------
  Mapping deviations from source content type to Nautobot content type
sessions.session => sessions.session | Disabled with reason: Nautobot has own sessions, sessions should never cross apps.
admin.logentry => admin.logentry | Disabled with reason: Not directly used in Nautobot.
users.userconfig => users.userconfig | Disabled with reason: May not have a 1 to 1 translation to Nautobot.
auth.permission => auth.permission | Disabled with reason: Handled via a Nautobot model and may not be a 1 to 1.
auth.user => users.user
dcim.sitegroup => dcim.locationtype
dcim.region => dcim.location
dcim.site => dcim.location
dcim.cablepath => dcim.cablepath | Disabled with reason: Recreated in Nautobot on signal when circuit termination is created
dcim.rackrole => extras.role
dcim.cabletermination EXTENDS dcim.cable => dcim.cable
dcim.devicerole => extras.role
ipam.role => extras.role
ipam.aggregate => ipam.prefix
dcim.modulebay => dcim.modulebay | Disabled with reason: Nautobot content type: `dcim.modulebay` not found
dcim.modulebaytemplate => dcim.modulebaytemplate | Disabled with reason: Nautobot content type: `dcim.modulebaytemplate` not found
dcim.moduletype => dcim.moduletype | Disabled with reason: Nautobot content type: `dcim.moduletype` not found
dcim.module => dcim.module | Disabled with reason: Nautobot content type: `dcim.module` not found
ipam.asn => ipam.asn | Disabled with reason: Nautobot content type: `ipam.asn` not found
ipam.iprange => ipam.iprange | Disabled with reason: Nautobot content type: `ipam.iprange` not found
tenancy.contactgroup => tenancy.contactgroup | Disabled with reason: Nautobot content type: `tenancy.contactgroup` not found
tenancy.contactrole => tenancy.contactrole | Disabled with reason: Nautobot content type: `tenancy.contactrole` not found
tenancy.contact => tenancy.contact | Disabled with reason: Nautobot content type: `tenancy.contact` not found
tenancy.contactassignment => tenancy.contactassignment | Disabled with reason: Nautobot content type: `tenancy.contactassignment` not found
dcim.inventoryitemrole => dcim.inventoryitemrole | Disabled with reason: Nautobot content type: `dcim.inventoryitemrole` not found
dcim.inventoryitemtemplate => dcim.inventoryitemtemplate | Disabled with reason: Nautobot content type: `dcim.inventoryitemtemplate` not found
dcim.virtualdevicecontext => dcim.virtualdevicecontext | Disabled with reason: Nautobot content type: `dcim.virtualdevicecontext` not found
ipam.fhrpgroup => ipam.fhrpgroup | Disabled with reason: Nautobot content type: `ipam.fhrpgroup` not found
ipam.fhrpgroupassignment => ipam.fhrpgroupassignment | Disabled with reason: Nautobot content type: `ipam.fhrpgroupassignment` not found
ipam.servicetemplate => ipam.servicetemplate | Disabled with reason: Nautobot content type: `ipam.servicetemplate` not found
ipam.l2vpn => ipam.l2vpn | Disabled with reason: Nautobot content type: `ipam.l2vpn` not found
ipam.l2vpntermination => ipam.l2vpntermination | Disabled with reason: Nautobot content type: `ipam.l2vpntermination` not found
extras.report => extras.report | Disabled with reason: Nautobot content type: `extras.report` not found
extras.script => extras.script | Disabled with reason: Nautobot content type: `extras.script` not found
extras.journalentry => extras.journalentry | Disabled with reason: Nautobot content type: `extras.journalentry` not found
extras.configrevision => extras.configrevision | Disabled with reason: Nautobot content type: `extras.configrevision` not found
extras.savedfilter => extras.savedfilter | Disabled with reason: Nautobot content type: `extras.savedfilter` not found
extras.cachedvalue => extras.cachedvalue | Disabled with reason: Nautobot content type: `extras.cachedvalue` not found
extras.branch => extras.branch | Disabled with reason: Nautobot content type: `extras.branch` not found
extras.stagedchange => extras.stagedchange | Disabled with reason: Nautobot content type: `extras.stagedchange` not found
users.adminuser => users.adminuser | Disabled with reason: Nautobot content type: `users.adminuser` not found
wireless.wirelesslangroup => wireless.wirelesslangroup | Disabled with reason: Nautobot content type: `wireless.wirelesslangroup` not found
wireless.wirelesslan => wireless.wirelesslan | Disabled with reason: Nautobot content type: `wireless.wirelesslan` not found
wireless.wirelesslink => wireless.wirelesslink | Disabled with reason: Nautobot content type: `wireless.wirelesslink` not found
django_rq.queue => django_rq.queue | Disabled with reason: Nautobot content type: `django_rq.queue` not found
secrets.secret => secrets.secret | Disabled with reason: Nautobot content type: `secrets.secret` not found
secrets.secretrole => secrets.secretrole | Disabled with reason: Nautobot content type: `secrets.secretrole` not found
secrets.userkey => secrets.userkey | Disabled with reason: Nautobot content type: `secrets.userkey` not found
secrets.sessionkey => secrets.sessionkey | Disabled with reason: Nautobot content type: `secrets.sessionkey` not found
```

## Content Types Back Mapping

This section shows back mapping deviations from Nautobot content types to NetBox content types. Only those content types that differ between NetBox and Nautobot are shown.

`Ambiguous` means that there are multiple NetBox content types that map to the same Nautobot content type.

```
- Content Types Back Mapping: --------------------------------------------------
  Back mapping deviations from Nautobot content type to the source content type
extras.role => Ambiguous
users.user => auth.user
dcim.locationtype => Ambiguous
dcim.location => Ambiguous
ipam.prefix => Ambiguous
```

## Fields Mapping

The last section shows fields mapping from NetBox to Nautobot, grouped by NetBox content type.

Each line consists of the following:

- NetBox field name.
- `(DATA)` marks fields that are present in the NetBox data.
- `(CUSTOM)` marks fields that have a custom import logic defined instead of the default one.
- `=>` as a separator.
- Nautobot field name.
- Field type in parentheses with the following special cases:
    -  `Disabled with reason: ...` means the field is intentionally disabled by the importer as it's not possible to import it to Nautobot.
    - `(ReadOnlyProperty')` marks fields that are read-only properties in Nautobot and can't be imported.
    - `(PrivateProperty)` marks fields that are prefixed with an underscore `_` and are considered private properties. Those fields are not imported.
    - `(NotFound)` indicates the field is not found in Nautobot and can't be imported.
    - `(DoNotImportLastUpdated)` marks the `last_updated` field, which is changed in Nautobot with each object update, as not to be imported.
    - `Custom Importer` marks fields that do not have a direct mapping to Nautobot and can potentially be imported to other content types, e.g., NetBox's `CustomField.choices` field to Nautobot's `CustomFieldChoice` objects.
    - `(Property)` marks fields that are class properties rather than Django fields. These are imported.

```
- Fields Mapping: --------------------------------------------------------------
. contenttypes.contenttype => contenttypes.contenttype .........................
id (CUSTOM) => id (AutoField)
app_label (DATA) (CUSTOM) => app_label (CharField)
model (DATA) => model (CharField)
. extras.status => extras.status ...............................................
id (CUSTOM) => id (UUIDField)
name (DATA) => name (CharField)
content_types (DATA) => content_types (ManyToManyField)
. extras.customfield => extras.customfield .....................................
id (DATA) (CUSTOM) => id (UUIDField)
name (DATA) (CUSTOM) => key (SlugField)
choices (CUSTOM) => Custom Importer
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
type (DATA) => type (CharField)
object_type (DATA) => object_type (NotFound)
label (DATA) => label (CharField)
group_name (DATA) => group_name (NotFound)
description (DATA) => description (CharField)
required (DATA) => required (BooleanField)
search_weight (DATA) => search_weight (NotFound)
filter_logic (DATA) => filter_logic (CharField)
default (DATA) => default (JSONField)
weight (DATA) => weight (PositiveSmallIntegerField)
validation_minimum (DATA) => validation_minimum (BigIntegerField)
validation_maximum (DATA) => validation_maximum (BigIntegerField)
validation_regex (DATA) => validation_regex (CharField)
choice_set (DATA) => choice_set (NotFound)
ui_visibility (DATA) => ui_visibility (NotFound)
content_types (DATA) => content_types (ManyToManyField)
. extras.taggeditem => extras.taggeditem .......................................
id (DATA) (CUSTOM) => id (UUIDField)
object_id (DATA) (CUSTOM) => object_id (UUIDField)
content_type (DATA) => content_type_id (ForeignKey)
tag (DATA) => tag_id (ForeignKey)
. auth.user => users.user ......................................................
id (CUSTOM) => id (UUIDField)
last_login (DATA) (CUSTOM) => Disabled with reason: Should not be attempted to migrated
password (DATA) (CUSTOM) => Disabled with reason: Should not be attempted to migrated
user_permissions (DATA) (CUSTOM) => Disabled with reason: Permissions import are not implemented yet
is_superuser (DATA) => is_superuser (BooleanField)
username (DATA) => username (CharField)
first_name (DATA) => first_name (CharField)
last_name (DATA) => last_name (CharField)
email (DATA) => email (CharField)
is_staff (DATA) => is_staff (BooleanField)
is_active (DATA) => is_active (BooleanField)
date_joined (DATA) => date_joined (DateTimeField)
groups (DATA) => groups (ManyToManyField)
. auth.group => auth.group .....................................................
id (CUSTOM) => id (AutoField)
permissions (DATA) (CUSTOM) => Disabled with reason: Permissions import are not implemented yet
name (DATA) => name (CharField)
. tenancy.tenant => tenancy.tenant .............................................
id (DATA) (CUSTOM) => id (UUIDField)
group (DATA) (CUSTOM) => tenant_group_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (TextField)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
. dcim.locationtype => dcim.locationtype .......................................
id (DATA) (CUSTOM) => id (UUIDField)
tree_id (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
lft (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
rght (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
level (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
name (DATA) => name (CharField)
nestable (DATA) => nestable (BooleanField)
content_types (DATA) => content_types (ManyToManyField)
parent (DATA) => parent_id (TreeNodeForeignKey)
. dcim.sitegroup => dcim.locationtype ..........................................
id (DATA) (CUSTOM) => id (UUIDField)
tree_id (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
lft (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
rght (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
level (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
parent (DATA) (CUSTOM) => parent_id (TreeNodeForeignKey)
nestable (CUSTOM) => nestable (BooleanField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
. dcim.region => dcim.location .................................................
id (DATA) (CUSTOM) => id (UUIDField)
tree_id (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
lft (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
rght (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
level (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
status (CUSTOM) => status_id (StatusField)
location_type (CUSTOM) => location_type_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
parent (DATA) => parent_id (TreeNodeForeignKey)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
. dcim.site => dcim.location ...................................................
id (DATA) (CUSTOM) => id (UUIDField)
tree_id (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
lft (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
rght (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
level (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
region (DATA) (CUSTOM) => parent_id (TreeNodeForeignKey)
group (DATA) (CUSTOM) => location_type_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (TextField)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
slug (DATA) => slug (NotFound)
status (DATA) => status_id (StatusField)
tenant (DATA) => tenant_id (ForeignKey)
facility (DATA) => facility (CharField)
time_zone (DATA) => time_zone (CharField)
physical_address (DATA) => physical_address (TextField)
shipping_address (DATA) => shipping_address (TextField)
latitude (DATA) => latitude (DecimalField)
longitude (DATA) => longitude (DecimalField)
asns (DATA) => asns (NotFound)
. dcim.location => dcim.location ...............................................
id (DATA) (CUSTOM) => id (UUIDField)
tree_id (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
lft (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
rght (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
level (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
status (DATA) (CUSTOM) => status_id (StatusField)
location_type (CUSTOM) => location_type_id (ForeignKey)
parent (DATA) (CUSTOM) => parent_id (TreeNodeForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
site (DATA) (CUSTOM) => parent_id (TreeNodeForeignKey)
tenant (DATA) => tenant_id (ForeignKey)
. dcim.rackreservation => dcim.rackreservation .................................
id (DATA) (CUSTOM) => id (UUIDField)
units (DATA) (CUSTOM) => units (JSONField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
comments (DATA) => comments (NotFound)
rack (DATA) => rack_id (ForeignKey)
tenant (DATA) => tenant_id (ForeignKey)
user (DATA) => user_id (ForeignKey)
description (DATA) => description (CharField)
. dcim.rackrole => extras.role .................................................
id (DATA) (CUSTOM) => id (UUIDField)
color (DATA) (CUSTOM) => color (CharField)
content_types (CUSTOM) => content_types (ManyToManyField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
. dcim.rack => dcim.rack .......................................................
id (DATA) (CUSTOM) => id (UUIDField)
location (DATA) (CUSTOM) => location_id (ForeignKey)
role (DATA) (CUSTOM) => role_id (RoleField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (TextField)
weight (DATA) => weight (NotFound)
weight_unit (DATA) => weight_unit (NotFound)
_abs_weight (DATA) => _abs_weight (PrivateProperty)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
facility_id (DATA) => facility_id (CharField)
site (DATA) (CUSTOM) => location_id (ForeignKey)
tenant (DATA) => tenant_id (ForeignKey)
status (DATA) => status_id (StatusField)
serial (DATA) => serial (CharField)
asset_tag (DATA) => asset_tag (CharField)
type (DATA) => type (CharField)
width (DATA) => width (PositiveSmallIntegerField)
u_height (DATA) => u_height (PositiveSmallIntegerField)
desc_units (DATA) => desc_units (BooleanField)
outer_width (DATA) => outer_width (PositiveSmallIntegerField)
outer_depth (DATA) => outer_depth (PositiveSmallIntegerField)
outer_unit (DATA) => outer_unit (CharField)
max_weight (DATA) => max_weight (NotFound)
_abs_max_weight (DATA) => _abs_max_weight (PrivateProperty)
mounting_depth (DATA) => mounting_depth (NotFound)
region (CUSTOM) => location_id (ForeignKey)
. dcim.cable => dcim.cable .....................................................
id (DATA) (CUSTOM) => id (UUIDField)
termination_a (CUSTOM) => termination_a (GenericForeignKey)
termination_b (CUSTOM) => termination_b (GenericForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (NotFound)
type (DATA) => type (CharField)
status (DATA) => status_id (StatusField)
tenant (DATA) => tenant (NotFound)
label (DATA) => label (CharField)
color (DATA) => color (CharField)
length (DATA) => length (PositiveSmallIntegerField)
length_unit (DATA) => length_unit (CharField)
_abs_length (DATA) => _abs_length (PrivateProperty)
termination_a_type (CUSTOM) => termination_a (GenericForeignKey)
termination_a_id (CUSTOM) => termination_a (GenericForeignKey)
termination_b_type (CUSTOM) => termination_b (GenericForeignKey)
termination_b_id (CUSTOM) => termination_b (GenericForeignKey)
. dcim.cabletermination => dcim.cable ..........................................
id (DATA) (CUSTOM) => id (UUIDField)
termination_a (CUSTOM) => termination_a (GenericForeignKey)
termination_b (CUSTOM) => termination_b (GenericForeignKey)
_device (DATA) => _device (PrivateProperty)
_rack (DATA) => _rack (PrivateProperty)
_location (DATA) => _location (PrivateProperty)
_site (DATA) => _site (PrivateProperty)
termination_a_type (DATA) (CUSTOM) => termination_a (GenericForeignKey)
termination_a_id (DATA) (CUSTOM) => termination_a (GenericForeignKey)
termination_b_type (DATA) (CUSTOM) => termination_b (GenericForeignKey)
termination_b_id (DATA) (CUSTOM) => termination_b (GenericForeignKey)
. dcim.interface => dcim.interface .............................................
id (DATA) (CUSTOM) => id (UUIDField)
status (CUSTOM) => status_id (StatusField)
parent (DATA) (CUSTOM) => parent_interface_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
device (DATA) => device_id (ForeignKeyWithAutoRelatedName)
name (DATA) => name (CharField)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
module (DATA) => module (NotFound)
cable (DATA) => cable_id (ForeignKey)
cable_end (DATA) => cable_end (NotFound)
mark_connected (DATA) => mark_connected (NotFound)
_path (DATA) => _path (PrivateProperty)
enabled (DATA) => enabled (BooleanField)
mac_address (DATA) => mac_address (CharField)
mtu (DATA) => mtu (PositiveIntegerField)
mode (DATA) => mode (CharField)
bridge (DATA) => bridge_id (ForeignKey)
_name (DATA) => _name (PrivateProperty)
lag (DATA) => lag_id (ForeignKey)
type (DATA) => type (CharField)
mgmt_only (DATA) => mgmt_only (BooleanField)
speed (DATA) => speed (NotFound)
duplex (DATA) => duplex (NotFound)
wwn (DATA) => wwn (NotFound)
rf_role (DATA) => rf_role (NotFound)
rf_channel (DATA) => rf_channel (NotFound)
rf_channel_frequency (DATA) => rf_channel_frequency (NotFound)
rf_channel_width (DATA) => rf_channel_width (NotFound)
tx_power (DATA) => tx_power (NotFound)
poe_mode (DATA) => poe_mode (NotFound)
poe_type (DATA) => poe_type (NotFound)
wireless_link (DATA) => wireless_link (NotFound)
untagged_vlan (DATA) => untagged_vlan_id (ForeignKey)
vrf (DATA) => vrf_id (ForeignKey)
vdcs (DATA) => vdcs (NotFound)
wireless_lans (DATA) => wireless_lans (NotFound)
tagged_vlans (DATA) => tagged_vlans (ManyToManyField)
. dcim.manufacturer => dcim.manufacturer .......................................
id (DATA) (CUSTOM) => id (UUIDField)
name (DATA) => name (CharField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
. dcim.devicetype => dcim.devicetype ...........................................
id (DATA) (CUSTOM) => id (UUIDField)
front_image (DATA) (CUSTOM) => Disabled with reason: Import does not contain images
rear_image (DATA) (CUSTOM) => Disabled with reason: Import does not contain images
color (CUSTOM) => color (NotFound)
manufacturer (DATA) => manufacturer_id (ForeignKey)
model (DATA) => model (CharField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (TextField)
weight (DATA) => weight (NotFound)
weight_unit (DATA) => weight_unit (NotFound)
_abs_weight (DATA) => _abs_weight (PrivateProperty)
slug (DATA) => slug (NotFound)
part_number (DATA) => part_number (CharField)
u_height (DATA) => u_height (PositiveSmallIntegerField)
is_full_depth (DATA) => is_full_depth (BooleanField)
subdevice_role (DATA) => subdevice_role (CharField)
airflow (DATA) => airflow (NotFound)
. dcim.devicerole => extras.role ...............................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
color (DATA) => color (CharField)
vm_role (DATA) => vm_role (NotFound)
. dcim.device => dcim.device ...................................................
id (DATA) (CUSTOM) => id (UUIDField)
location (DATA) (CUSTOM) => location_id (ForeignKey)
device_role (CUSTOM) => role_id (RoleField)
role (DATA) (CUSTOM) => role_id (RoleField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (TextField)
local_context_data (DATA) => local_context_data (NotFound)
device_type (DATA) => device_type_id (ForeignKey)
tenant (DATA) => tenant_id (ForeignKey)
platform (DATA) => platform_id (ForeignKey)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
serial (DATA) => serial (CharField)
asset_tag (DATA) => asset_tag (CharField)
site (DATA) (CUSTOM) => location_id (ForeignKey)
rack (DATA) => rack_id (ForeignKey)
position (DATA) => position (PositiveSmallIntegerField)
face (DATA) => face (CharField)
status (DATA) => status_id (StatusField)
airflow (DATA) => airflow (NotFound)
primary_ip4 (DATA) => primary_ip4_id (ForeignKey)
primary_ip6 (DATA) => primary_ip6_id (ForeignKey)
cluster (DATA) => cluster_id (ForeignKey)
virtual_chassis (DATA) => virtual_chassis_id (ForeignKey)
vc_position (DATA) => vc_position (PositiveSmallIntegerField)
vc_priority (DATA) => vc_priority (PositiveSmallIntegerField)
region (CUSTOM) => location_id (ForeignKey)
. dcim.powerpanel => dcim.powerpanel ...........................................
id (DATA) (CUSTOM) => id (UUIDField)
location (DATA) (CUSTOM) => location_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (NotFound)
site (DATA) (CUSTOM) => location_id (ForeignKey)
name (DATA) => name (CharField)
region (CUSTOM) => location_id (ForeignKey)
. dcim.frontporttemplate => dcim.frontporttemplate .............................
id (DATA) (CUSTOM) => id (UUIDField)
rear_port (DATA) (CUSTOM) => rear_port_template_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
device_type (DATA) => device_type_id (ForeignKeyWithAutoRelatedName)
module_type (DATA) => module_type (NotFound)
type (DATA) => type (CharField)
color (DATA) => color (NotFound)
rear_port_position (DATA) => rear_port_position (PositiveSmallIntegerField)
. dcim.poweroutlettemplate => dcim.poweroutlettemplate .........................
id (DATA) (CUSTOM) => id (UUIDField)
power_port (DATA) (CUSTOM) => power_port_template_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
device_type (DATA) => device_type_id (ForeignKeyWithAutoRelatedName)
module_type (DATA) => module_type (NotFound)
type (DATA) => type (CharField)
feed_leg (DATA) => feed_leg (CharField)
. ipam.role => extras.role .....................................................
id (DATA) (CUSTOM) => id (UUIDField)
color (CUSTOM) => color (CharField)
content_types (CUSTOM) => content_types (ManyToManyField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
weight (DATA) => weight (PositiveSmallIntegerField)
. ipam.ipaddress => ipam.ipaddress .............................................
id (DATA) (CUSTOM) => id (UUIDField)
role (DATA) (CUSTOM) => role_id (RoleField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (NotFound)
address (DATA) => address (Property)
vrf (DATA) => vrf (NotFound)
tenant (DATA) => tenant_id (ForeignKey)
status (DATA) => status_id (StatusField)
assigned_object_type (DATA) => assigned_object_type (NotFound)
assigned_object_id (DATA) => assigned_object_id (NotFound)
nat_inside (DATA) => nat_inside_id (ForeignKey)
dns_name (DATA) => dns_name (CharField)
. ipam.prefix => ipam.prefix ...................................................
id (DATA) (CUSTOM) => id (UUIDField)
location (CUSTOM) => location_id (ForeignKey)
role (DATA) (CUSTOM) => role_id (RoleField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (NotFound)
prefix (DATA) => prefix (Property)
site (DATA) (CUSTOM) => location_id (ForeignKey)
vrf (DATA) => vrf (NotFound)
tenant (DATA) => tenant_id (ForeignKey)
vlan (DATA) => vlan_id (ForeignKey)
status (DATA) => status_id (StatusField)
is_pool (DATA) => is_pool (NotFound)
mark_utilized (DATA) => mark_utilized (NotFound)
_depth (DATA) => _depth (PrivateProperty)
_children (DATA) => _children (PrivateProperty)
region (CUSTOM) => location_id (ForeignKey)
. ipam.aggregate => ipam.prefix ................................................
id (DATA) (CUSTOM) => id (UUIDField)
status (CUSTOM) => status_id (StatusField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (NotFound)
prefix (DATA) => prefix (Property)
rir (DATA) => rir_id (ForeignKey)
tenant (DATA) => tenant_id (ForeignKey)
date_added (DATA) => date_added (NotFound)
. ipam.vlan => ipam.vlan .......................................................
id (DATA) (CUSTOM) => id (UUIDField)
group (DATA) (CUSTOM) => vlan_group_id (ForeignKey)
location (CUSTOM) => location_id (ForeignKey)
role (DATA) (CUSTOM) => role_id (RoleField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (NotFound)
site (DATA) (CUSTOM) => location_id (ForeignKey)
vid (DATA) => vid (PositiveSmallIntegerField)
name (DATA) => name (CharField)
tenant (DATA) => tenant_id (ForeignKey)
status (DATA) => status_id (StatusField)
region (CUSTOM) => location_id (ForeignKey)
. virtualization.cluster => virtualization.cluster .............................
id (DATA) (CUSTOM) => id (UUIDField)
type (DATA) (CUSTOM) => cluster_type_id (ForeignKey)
group (DATA) (CUSTOM) => cluster_group_id (ForeignKey)
location (CUSTOM) => location_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (TextField)
name (DATA) => name (CharField)
status (DATA) => status (NotFound)
tenant (DATA) => tenant_id (ForeignKey)
site (DATA) (CUSTOM) => location_id (ForeignKey)
region (CUSTOM) => location_id (ForeignKey)
. virtualization.virtualmachine => virtualization.virtualmachine ...............
id (DATA) (CUSTOM) => id (UUIDField)
role (DATA) (CUSTOM) => role_id (RoleField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (TextField)
local_context_data (DATA) => local_context_data (NotFound)
site (DATA) => site (NotFound)
cluster (DATA) => cluster_id (ForeignKey)
device (DATA) => device (NotFound)
tenant (DATA) => tenant_id (ForeignKey)
platform (DATA) => platform_id (ForeignKey)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
status (DATA) => status_id (StatusField)
primary_ip4 (DATA) => primary_ip4_id (ForeignKey)
primary_ip6 (DATA) => primary_ip6_id (ForeignKey)
vcpus (DATA) => vcpus (PositiveSmallIntegerField)
memory (DATA) => memory (PositiveIntegerField)
disk (DATA) => disk (PositiveIntegerField)
. virtualization.vminterface => virtualization.vminterface .....................
id (DATA) (CUSTOM) => id (UUIDField)
status (CUSTOM) => status_id (StatusField)
parent (DATA) (CUSTOM) => parent_interface_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
enabled (DATA) => enabled (BooleanField)
mac_address (DATA) => mac_address (CharField)
mtu (DATA) => mtu (PositiveIntegerField)
mode (DATA) => mode (CharField)
bridge (DATA) => bridge_id (ForeignKey)
virtual_machine (DATA) => virtual_machine_id (ForeignKey)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
description (DATA) => description (CharField)
untagged_vlan (DATA) => untagged_vlan_id (ForeignKey)
vrf (DATA) => vrf_id (ForeignKey)
tagged_vlans (DATA) => tagged_vlans (ManyToManyField)
. circuits.circuit => circuits.circuit .........................................
id (DATA) (CUSTOM) => id (UUIDField)
type (DATA) (CUSTOM) => circuit_type_id (ForeignKey)
termination_a (DATA) (CUSTOM) => circuit_termination_a_id (ForeignKey)
termination_z (DATA) (CUSTOM) => circuit_termination_z_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (TextField)
cid (DATA) => cid (CharField)
provider (DATA) => provider_id (ForeignKey)
provider_account (DATA) => provider_account (NotFound)
status (DATA) => status_id (StatusField)
tenant (DATA) => tenant_id (ForeignKey)
install_date (DATA) => install_date (DateField)
termination_date (DATA) => termination_date (NotFound)
commit_rate (DATA) => commit_rate (PositiveIntegerField)
. circuits.circuittermination => circuits.circuittermination ...................
id (DATA) (CUSTOM) => id (UUIDField)
location (CUSTOM) => location_id (ForeignKey)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
cable (DATA) => cable_id (ForeignKey)
cable_end (DATA) => cable_end (NotFound)
mark_connected (DATA) => mark_connected (NotFound)
circuit (DATA) => circuit_id (ForeignKey)
term_side (DATA) => term_side (CharField)
site (DATA) (CUSTOM) => location_id (ForeignKey)
provider_network (DATA) => provider_network_id (ForeignKey)
port_speed (DATA) => port_speed (PositiveIntegerField)
upstream_speed (DATA) => upstream_speed (PositiveIntegerField)
xconnect_id (DATA) => xconnect_id (CharField)
pp_info (DATA) => pp_info (CharField)
description (DATA) => description (CharField)
region (CUSTOM) => location_id (ForeignKey)
. circuits.circuittype => circuits.circuittype .................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
. circuits.provider => circuits.provider .......................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (TextField)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
asns (DATA) => asns (NotFound)
. circuits.providernetwork => circuits.providernetwork .........................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (TextField)
name (DATA) => name (CharField)
provider (DATA) => provider_id (ForeignKey)
service_id (DATA) => service_id (NotFound)
. dcim.consoleport => dcim.consoleport .........................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
device (DATA) => device_id (ForeignKeyWithAutoRelatedName)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
module (DATA) => module (NotFound)
cable (DATA) => cable_id (ForeignKey)
cable_end (DATA) => cable_end (NotFound)
mark_connected (DATA) => mark_connected (NotFound)
_path (DATA) => _path (PrivateProperty)
type (DATA) => type (CharField)
speed (DATA) => speed (NotFound)
. dcim.powerport => dcim.powerport .............................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
device (DATA) => device_id (ForeignKeyWithAutoRelatedName)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
module (DATA) => module (NotFound)
cable (DATA) => cable_id (ForeignKey)
cable_end (DATA) => cable_end (NotFound)
mark_connected (DATA) => mark_connected (NotFound)
_path (DATA) => _path (PrivateProperty)
type (DATA) => type (CharField)
maximum_draw (DATA) => maximum_draw (PositiveSmallIntegerField)
allocated_draw (DATA) => allocated_draw (PositiveSmallIntegerField)
. dcim.poweroutlet => dcim.poweroutlet .........................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
device (DATA) => device_id (ForeignKeyWithAutoRelatedName)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
module (DATA) => module (NotFound)
cable (DATA) => cable_id (ForeignKey)
cable_end (DATA) => cable_end (NotFound)
mark_connected (DATA) => mark_connected (NotFound)
_path (DATA) => _path (PrivateProperty)
type (DATA) => type (CharField)
power_port (DATA) => power_port_id (ForeignKey)
feed_leg (DATA) => feed_leg (CharField)
. dcim.frontport => dcim.frontport .............................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
device (DATA) => device_id (ForeignKeyWithAutoRelatedName)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
module (DATA) => module (NotFound)
cable (DATA) => cable_id (ForeignKey)
cable_end (DATA) => cable_end (NotFound)
mark_connected (DATA) => mark_connected (NotFound)
type (DATA) => type (CharField)
color (DATA) => color (NotFound)
rear_port (DATA) => rear_port_id (ForeignKey)
rear_port_position (DATA) => rear_port_position (PositiveSmallIntegerField)
. dcim.rearport => dcim.rearport ...............................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
device (DATA) => device_id (ForeignKeyWithAutoRelatedName)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
module (DATA) => module (NotFound)
cable (DATA) => cable_id (ForeignKey)
cable_end (DATA) => cable_end (NotFound)
mark_connected (DATA) => mark_connected (NotFound)
type (DATA) => type (CharField)
color (DATA) => color (NotFound)
positions (DATA) => positions (PositiveSmallIntegerField)
. dcim.devicebay => dcim.devicebay .............................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
device (DATA) => device_id (ForeignKeyWithAutoRelatedName)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
installed_device (DATA) => installed_device_id (OneToOneField)
. dcim.consoleporttemplate => dcim.consoleporttemplate .........................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
device_type (DATA) => device_type_id (ForeignKeyWithAutoRelatedName)
module_type (DATA) => module_type (NotFound)
type (DATA) => type (CharField)
. dcim.powerporttemplate => dcim.powerporttemplate .............................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
device_type (DATA) => device_type_id (ForeignKeyWithAutoRelatedName)
module_type (DATA) => module_type (NotFound)
type (DATA) => type (CharField)
maximum_draw (DATA) => maximum_draw (PositiveSmallIntegerField)
allocated_draw (DATA) => allocated_draw (PositiveSmallIntegerField)
. dcim.interfacetemplate => dcim.interfacetemplate .............................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
name (DATA) => name (CharField)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
device_type (DATA) => device_type_id (ForeignKeyWithAutoRelatedName)
module_type (DATA) => module_type (NotFound)
_name (DATA) => _name (PrivateProperty)
type (DATA) => type (CharField)
enabled (DATA) => enabled (NotFound)
mgmt_only (DATA) => mgmt_only (BooleanField)
bridge (DATA) => bridge (NotFound)
poe_mode (DATA) => poe_mode (NotFound)
poe_type (DATA) => poe_type (NotFound)
. dcim.rearporttemplate => dcim.rearporttemplate ...............................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
device_type (DATA) => device_type_id (ForeignKeyWithAutoRelatedName)
module_type (DATA) => module_type (NotFound)
type (DATA) => type (CharField)
color (DATA) => color (NotFound)
positions (DATA) => positions (PositiveSmallIntegerField)
. dcim.devicebaytemplate => dcim.devicebaytemplate .............................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
device_type (DATA) => device_type_id (ForeignKeyWithAutoRelatedName)
name (DATA) => name (CharField)
_name (DATA) => _name (PrivateProperty)
label (DATA) => label (CharField)
description (DATA) => description (CharField)
. dcim.platform => dcim.platform ...............................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
manufacturer (DATA) => manufacturer_id (ForeignKey)
. dcim.virtualchassis => dcim.virtualchassis ...................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (NotFound)
master (DATA) => master_id (OneToOneField)
name (DATA) => name (CharField)
domain (DATA) => domain (CharField)
. dcim.powerfeed => dcim.powerfeed .............................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (NotFound)
comments (DATA) => comments (TextField)
cable (DATA) => cable_id (ForeignKey)
cable_end (DATA) => cable_end (NotFound)
mark_connected (DATA) => mark_connected (NotFound)
_path (DATA) => _path (PrivateProperty)
power_panel (DATA) => power_panel_id (ForeignKey)
rack (DATA) => rack_id (ForeignKey)
name (DATA) => name (CharField)
status (DATA) => status_id (StatusField)
type (DATA) => type (CharField)
supply (DATA) => supply (CharField)
phase (DATA) => phase (CharField)
voltage (DATA) => voltage (SmallIntegerField)
amperage (DATA) => amperage (PositiveSmallIntegerField)
max_utilization (DATA) => max_utilization (PositiveSmallIntegerField)
available_power (DATA) => available_power (PositiveIntegerField)
. ipam.vrf => ipam.vrf .........................................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (NotFound)
name (DATA) => name (CharField)
rd (DATA) => rd (CharField)
tenant (DATA) => tenant_id (ForeignKey)
enforce_unique (DATA) => enforce_unique (NotFound)
import_targets (DATA) => import_targets (ManyToManyField)
export_targets (DATA) => export_targets (ManyToManyField)
. ipam.routetarget => ipam.routetarget .........................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
comments (DATA) => comments (NotFound)
name (DATA) => name (CharField)
tenant (DATA) => tenant_id (ForeignKey)
. ipam.rir => ipam.rir .........................................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
is_private (DATA) => is_private (BooleanField)
. ipam.vlangroup => ipam.vlangroup .............................................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
description (DATA) => description (CharField)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
scope_type (DATA) => scope_type (NotFound)
scope_id (DATA) => scope_id (NotFound)
min_vid (DATA) => min_vid (NotFound)
max_vid (DATA) => max_vid (NotFound)
. extras.tag => extras.tag .....................................................
id (DATA) (CUSTOM) => id (UUIDField)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
color (DATA) => color (CharField)
description (DATA) => description (CharField)
. tenancy.tenantgroup => tenancy.tenantgroup ...................................
id (DATA) (CUSTOM) => id (UUIDField)
tree_id (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
lft (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
rght (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
level (DATA) (CUSTOM) => Disabled with reason: Tree fields doesn't need to be imported
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
parent (DATA) => parent_id (TreeNodeForeignKey)
description (DATA) => description (CharField)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
. virtualization.clustertype => virtualization.clustertype .....................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
. virtualization.clustergroup => virtualization.clustergroup ...................
id (DATA) (CUSTOM) => id (UUIDField)
created (DATA) => created (DateTimeField)
last_updated (DATA) => last_updated (DoNotImportLastUpdated)
custom_field_data (DATA) => custom_field_data (CustomFieldData)
name (DATA) => name (CharField)
slug (DATA) => slug (NotFound)
description (DATA) => description (CharField)
================================================================================
```
