# NetBox Text Import Summary

This document describes the text summary of mapping from NetBox 3.6 to Nautobot 2.1.5. Mappings for other versions may vary based on available models and fields.

Text summary can be used to review the import process and to identify potential issues and deviations from the source data. It is also useful for debugging and troubleshooting the import process. It's formatted to be human-readable and can be easily compared between different import runs. In opposite to JSON summary it does not contain all the details about the import process, but only those models and fields coming from the input data.

The summary is generated when running the following command:

```shell
nautobot-server import_netbox \
    --dry-run \
    --bypass-data-validation \
    --print-summary \
    --save-text-summary-path=summary.txt \
    https://github.com/netbox-community/netbox-demo-data/raw/master/json/netbox-demo-v3.6.json
```

The summary is divided into several sections as described below.

## DiffSync Summary

The first section is the import summary. It shows a basic summary from the underlying [DiffSync](https://github.com/networktocode/diffsync) library.

```
* Import Summary: **********************************************************************************
= DiffSync Summary: ================================================================================
create: 5865
update: 1
delete: 0
no-change: 4
skip: 119
```

In this case, skipped objects are `ContentType` objects, as these are not directly imported into Nautobot.

`update` and `no-change` are those objects that are already in Nautobot. Typically, these are `User`, `Status`, `Role` or similar objects. Detailed information about these objects is shown in the debug log.

## Statistics

These sections show statistics for each model with non-zero values. The statistics are divided into two parts: Source and Nautobot statistics.

```
= Source Stats: ====================================================================================
- admin.logentry -----------------------------------------------------------------------------------
first_pass_used: 12
- auth.group ---------------------------------------------------------------------------------------
first_pass_used: 1
second_pass_used: 1
created: 1
imported: 1
- auth.permission ----------------------------------------------------------------------------------
first_pass_used: 473
- auth.user ----------------------------------------------------------------------------------------
first_pass_used: 6
second_pass_used: 6
created: 6
imported: 6
- circuits.circuit ---------------------------------------------------------------------------------
first_pass_used: 29
second_pass_used: 29
created: 29
imported: 29
- circuits.circuittermination ----------------------------------------------------------------------
first_pass_used: 45
second_pass_used: 45
created: 45
imported: 45
...
- contenttypes.contenttype -------------------------------------------------------------------------
first_pass_used: 119
second_pass_used: 119
created: 119
imported: 119
...
- dcim.devicetype ----------------------------------------------------------------------------------
pre_cached: 1
first_pass_used: 14
second_pass_used: 14
created: 15
imported: 15
imported_from_cache: 1
...
```

Nautobot statistics summarize the number of created objects and issues encountered during the import process:

```
= Nautobot Stats: ==================================================================================
- auth.group ---------------------------------------------------------------------------------------
source_created: 1
- circuits.circuit ---------------------------------------------------------------------------------
source_created: 29
- circuits.circuittermination ----------------------------------------------------------------------
source_created: 45
...
- contenttypes.contenttype -------------------------------------------------------------------------
source_ignored: 119
...
- dcim.device --------------------------------------------------------------------------------------
source_created: 72
...
- dcim.location ------------------------------------------------------------------------------------
source_created: 95
issues: 20
...
- extras.role --------------------------------------------------------------------------------------
source_created: 18
- extras.status ------------------------------------------------------------------------------------
source_created: 6
...
```

## Content Types Mapping Deviations

This section shows deviations from NetBox content type to Nautobot content type. Only those content types that differ between NetBox and Nautobot are shown.

`EXTENDS` means that the NetBox object of such a content type is merged with another object. For example, `CableTermination` objects are merged with the corresponding `Cable` objects before diffing and importing them into Nautobot.

```
= Content Types Mapping Deviations: ================================================================
  Mapping deviations from source content type to Nautobot content type
auth.user => users.user
dcim.cabletermination EXTENDS dcim.cable => dcim.cable
dcim.devicerole => extras.role
dcim.rackrole => extras.role
dcim.region => dcim.location
dcim.site => dcim.location
dcim.sitegroup => dcim.locationtype
ipam.aggregate => ipam.prefix
ipam.role => extras.role
```

## Content Types Back Mapping

This section shows back mapping deviations from Nautobot content types to NetBox content types. Only those content types that differ between NetBox and Nautobot are shown.

`Ambiguous` means that there are multiple NetBox content types that map to the same Nautobot content type.

```
= Content Types Back Mapping: ======================================================================
  Back mapping deviations from Nautobot content type to the source content type
users.user => auth.user
dcim.cable => dcim.cabletermination
extras.role => Ambiguous
dcim.location => Ambiguous
dcim.locationtype => dcim.sitegroup
ipam.prefix => ipam.aggregate
```

## Importer Issues

This section shows importer issues that were found during the import process grouped by the Nautobot content type.

These issues are not necessarily errors, but may be warnings or other issues that should be reviewed. See the [Data Validation and Error Handling chapter](./app_use_cases.md#data-validation-and-error-handling) for details.

```
= Importer issues: =================================================================================
- dcim.location ---------------------------------------------------------------------------------
022126fd-0b04-5d40-9aa0-3c1aa0a5dfd5 DM-Akron | ValidationError | {'parent': ['A Location of type Branch Offices can only have a Location of the same type or of type Customer Sites as its parent.']}
044d48c0-0889-5205-a6fa-2c7c21aaa1de DM-Nashua | ValidationError | {'parent': ['A Location of type Branch Offices can only have a Location of the same type or of type Customer Sites as its parent.']}
10cd37cc-9b76-5717-b0fa-2fcf0d2b9852 JBB Branch 104 | ValidationError | {'parent': ['A Location of type Branch Offices can only have a Location of the same type or of type Customer Sites as its parent.']}
...
- dcim.powerfeed --------------------------------------------------------------------------------
0434ed4d-cc76-5051-a38c-b84ed32de2c1 P2-6B | ValidationError | ['Rack R106 (Row 1) and power panel Panel 2 (MDF) are in different locations']
05541f06-08c9-5d84-a8b6-13ce3cd45938 P3-8A | ValidationError | ['Rack R308 (Row 3) and power panel Panel 3 (MDF) are in different locations']
05f5bb91-e84c-5908-8d9a-8256959bfcab P2-11B | ValidationError | ['Rack R203 (Row 2) and power panel Panel 2 (MDF) are in different locations']
...
```

## Field Mappings

The last section shows field mappings from NetBox to Nautobot, grouped by NetBox content type. Only source fields coming from input data are shown.

Each line consists of the following:

- NetBox field name.
- `=>` as a separator.
- Importer name.
    - When the field import is intentionally disabled, line continues with: `Disabled with reason: ...` instead.
- `=>` as a separator.
- Nautobot field name.
    - `CUSTOM TARGET` marks source fields that do not have a direct mapping to Nautobot and can potentially be imported to other content types,
      e.g., NetBox's `CustomField.choices` field to Nautobot's `CustomFieldChoice` objects.
- Field type in parentheses with the following special cases:
    - `(NotFound)` indicates the field is not found in Nautobot and can't be imported.
    - `(Property)` marks fields that are class properties rather than Django fields. These are imported.
    - `(PrivateProperty)` marks fields that are prefixed with an underscore `_` and are considered private properties. Those fields are not imported.
    - `(ReadOnlyProperty')` marks fields that are read-only properties in Nautobot and can't be imported.

```
= Field Mappings: ==================================================================================
- auth.group => auth.group -------------------------------------------------------------------------
name => value_importer => name (CharField)
permissions => Disabled with reason: Permissions import is not implemented yet
- auth.user => users.user --------------------------------------------------------------------------
date_joined => datetime_importer => date_joined (DateTimeField)
email => value_importer => email (CharField)
first_name => value_importer => first_name (CharField)
groups => identifiers_importer => groups (ManyToManyField)
is_active => value_importer => is_active (BooleanField)
is_staff => value_importer => is_staff (BooleanField)
is_superuser => value_importer => is_superuser (BooleanField)
last_login => Disabled with reason: Should not be attempted to migrate
last_name => value_importer => last_name (CharField)
password => Disabled with reason: Should not be attempted to migrate
user_permissions => Disabled with reason: Permissions import is not implemented yet
username => value_importer => username (CharField)
- circuits.circuit => circuits.circuit -------------------------------------------------------------
cid => value_importer => cid (CharField)
comments => value_importer => comments (TextField)
commit_rate => integer_importer => commit_rate (PositiveIntegerField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
install_date => date_importer => install_date (DateField)
last_updated => Disabled with reason: Last updated field is updated with each write
provider => relation_importer => provider_id (ForeignKey)
provider_account => NO IMPORTER => provider_account (NotFound)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
termination_a => relation_importer => circuit_termination_a_id (ForeignKey)
termination_date => NO IMPORTER => termination_date (NotFound)
termination_z => relation_importer => circuit_termination_z_id (ForeignKey)
type => relation_importer => circuit_type_id (ForeignKey)
- circuits.circuittermination => circuits.circuittermination ---------------------------------------
cable => relation_importer => cable_id (ForeignKey)
cable_end => NO IMPORTER => cable_end (NotFound)
circuit => relation_importer => circuit_id (ForeignKey)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
mark_connected => NO IMPORTER => mark_connected (NotFound)
port_speed => integer_importer => port_speed (PositiveIntegerField)
pp_info => value_importer => pp_info (CharField)
provider_network => relation_importer => provider_network_id (ForeignKey)
site => location_importer => location_id (ForeignKey)
term_side => choice_importer => term_side (CharField)
upstream_speed => integer_importer => upstream_speed (PositiveIntegerField)
xconnect_id => value_importer => xconnect_id (CharField)
- circuits.circuittype => circuits.circuittype -----------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- circuits.provider => circuits.provider -----------------------------------------------------------
asns => NO IMPORTER => asns (NotFound)
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- circuits.providernetwork => circuits.providernetwork ---------------------------------------------
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
provider => relation_importer => provider_id (ForeignKey)
service_id => NO IMPORTER => service_id (NotFound)
- contenttypes.contenttype => contenttypes.contenttype ---------------------------------------------
app_label => content_types_mapper_importer => app_label (CharField)
model => value_importer => model (CharField)
- dcim.cable => dcim.cable -------------------------------------------------------------------------
_abs_length => NO IMPORTER => _abs_length (PrivateProperty)
color => value_importer => color (CharField)
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
length => integer_importer => length (PositiveSmallIntegerField)
length_unit => choice_importer => length_unit (CharField)
status => status_importer => status_id (StatusField)
tenant => NO IMPORTER => tenant (NotFound)
type => choice_importer => type (CharField)
- dcim.cabletermination => dcim.cable --------------------------------------------------------------
_device => NO IMPORTER => _device (PrivateProperty)
_location => NO IMPORTER => _location (PrivateProperty)
_rack => NO IMPORTER => _rack (PrivateProperty)
_site => NO IMPORTER => _site (PrivateProperty)
id => uid_from_data => id (UUIDField)
termination_a_id => relation_and_type_importer => termination_a_id (UUIDField)
termination_a_type => relation_and_type_importer => termination_a_type_id (ForeignKey)
termination_b_id => relation_and_type_importer => termination_b_id (UUIDField)
termination_b_type => relation_and_type_importer => termination_b_type_id (ForeignKey)
- dcim.consoleport => dcim.consoleport -------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
_path => NO IMPORTER => _path (PrivateProperty)
cable => relation_importer => cable_id (ForeignKey)
cable_end => NO IMPORTER => cable_end (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
device => relation_importer => device_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
mark_connected => NO IMPORTER => mark_connected (NotFound)
module => NO IMPORTER => module (NotFound)
name => value_importer => name (CharField)
speed => NO IMPORTER => speed (NotFound)
type => choice_importer => type (CharField)
- dcim.consoleporttemplate => dcim.consoleporttemplate ---------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
created => datetime_importer => created (DateTimeField)
description => value_importer => description (CharField)
device_type => relation_importer => device_type_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
module_type => NO IMPORTER => module_type (NotFound)
name => value_importer => name (CharField)
type => choice_importer => type (CharField)
- dcim.device => dcim.device -----------------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
airflow => NO IMPORTER => airflow (NotFound)
asset_tag => value_importer => asset_tag (CharField)
cluster => relation_importer => cluster_id (ForeignKey)
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
device_type => relation_importer => device_type_id (ForeignKey)
face => choice_importer => face (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
local_context_data => NO IMPORTER => local_context_data (NotFound)
location => location_importer => location_id (ForeignKey)
name => value_importer => name (CharField)
platform => relation_importer => platform_id (ForeignKey)
position => integer_importer => position (PositiveSmallIntegerField)
primary_ip4 => relation_importer => primary_ip4_id (ForeignKey)
primary_ip6 => relation_importer => primary_ip6_id (ForeignKey)
rack => relation_importer => rack_id (ForeignKey)
role => role_importer => role_id (RoleField)
serial => value_importer => serial (CharField)
site => location_importer => location_id (ForeignKey)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
vc_position => integer_importer => vc_position (PositiveSmallIntegerField)
vc_priority => integer_importer => vc_priority (PositiveSmallIntegerField)
virtual_chassis => relation_importer => virtual_chassis_id (ForeignKey)
- dcim.devicebay => dcim.devicebay -----------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
device => relation_importer => device_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
installed_device => relation_importer => installed_device_id (OneToOneField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
- dcim.devicebaytemplate => dcim.devicebaytemplate -------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
created => datetime_importer => created (DateTimeField)
description => value_importer => description (CharField)
device_type => relation_importer => device_type_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
- dcim.devicerole => extras.role -------------------------------------------------------------------
color => value_importer => color (CharField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
vm_role => NO IMPORTER => vm_role (NotFound)
- dcim.devicetype => dcim.devicetype ---------------------------------------------------------------
_abs_weight => NO IMPORTER => _abs_weight (PrivateProperty)
airflow => NO IMPORTER => airflow (NotFound)
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
front_image => Disabled with reason: Import does not contain images
id => uid_from_data => id (UUIDField)
is_full_depth => value_importer => is_full_depth (BooleanField)
last_updated => Disabled with reason: Last updated field is updated with each write
manufacturer => relation_importer => manufacturer_id (ForeignKey)
model => value_importer => model (CharField)
part_number => value_importer => part_number (CharField)
rear_image => Disabled with reason: Import does not contain images
slug => NO IMPORTER => slug (NotFound)
subdevice_role => choice_importer => subdevice_role (CharField)
u_height => integer_importer => u_height (PositiveSmallIntegerField)
weight => NO IMPORTER => weight (NotFound)
weight_unit => NO IMPORTER => weight_unit (NotFound)
- dcim.frontport => dcim.frontport -----------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
cable => relation_importer => cable_id (ForeignKey)
cable_end => NO IMPORTER => cable_end (NotFound)
color => NO IMPORTER => color (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
device => relation_importer => device_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
mark_connected => NO IMPORTER => mark_connected (NotFound)
module => NO IMPORTER => module (NotFound)
name => value_importer => name (CharField)
rear_port => relation_importer => rear_port_id (ForeignKey)
rear_port_position => integer_importer => rear_port_position (PositiveSmallIntegerField)
type => choice_importer => type (CharField)
- dcim.frontporttemplate => dcim.frontporttemplate -------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
color => NO IMPORTER => color (NotFound)
created => datetime_importer => created (DateTimeField)
description => value_importer => description (CharField)
device_type => relation_importer => device_type_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
module_type => NO IMPORTER => module_type (NotFound)
name => value_importer => name (CharField)
rear_port => relation_importer => rear_port_template_id (ForeignKey)
rear_port_position => integer_importer => rear_port_position (PositiveSmallIntegerField)
type => choice_importer => type (CharField)
- dcim.interface => dcim.interface -----------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
_path => NO IMPORTER => _path (PrivateProperty)
bridge => relation_importer => bridge_id (ForeignKey)
cable => relation_importer => cable_id (ForeignKey)
cable_end => NO IMPORTER => cable_end (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
device => relation_importer => device_id (ForeignKeyWithAutoRelatedName)
duplex => NO IMPORTER => duplex (NotFound)
enabled => value_importer => enabled (BooleanField)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
lag => relation_importer => lag_id (ForeignKey)
last_updated => Disabled with reason: Last updated field is updated with each write
mac_address => value_importer => mac_address (CharField)
mark_connected => NO IMPORTER => mark_connected (NotFound)
mgmt_only => value_importer => mgmt_only (BooleanField)
mode => choice_importer => mode (CharField)
module => NO IMPORTER => module (NotFound)
mtu => integer_importer => mtu (PositiveIntegerField)
name => value_importer => name (CharField)
parent => relation_importer => parent_interface_id (ForeignKey)
poe_mode => NO IMPORTER => poe_mode (NotFound)
poe_type => NO IMPORTER => poe_type (NotFound)
rf_channel => NO IMPORTER => rf_channel (NotFound)
rf_channel_frequency => NO IMPORTER => rf_channel_frequency (NotFound)
rf_channel_width => NO IMPORTER => rf_channel_width (NotFound)
rf_role => NO IMPORTER => rf_role (NotFound)
speed => NO IMPORTER => speed (NotFound)
tagged_vlans => uuids_importer => tagged_vlans (ManyToManyField)
tx_power => NO IMPORTER => tx_power (NotFound)
type => choice_importer => type (CharField)
untagged_vlan => relation_importer => untagged_vlan_id (ForeignKey)
vdcs => NO IMPORTER => vdcs (NotFound)
vrf => relation_importer => vrf_id (ForeignKey)
wireless_lans => NO IMPORTER => wireless_lans (NotFound)
wireless_link => NO IMPORTER => wireless_link (NotFound)
wwn => NO IMPORTER => wwn (NotFound)
- dcim.interfacetemplate => dcim.interfacetemplate -------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
bridge => NO IMPORTER => bridge (NotFound)
created => datetime_importer => created (DateTimeField)
description => value_importer => description (CharField)
device_type => relation_importer => device_type_id (ForeignKeyWithAutoRelatedName)
enabled => NO IMPORTER => enabled (NotFound)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
mgmt_only => value_importer => mgmt_only (BooleanField)
module_type => NO IMPORTER => module_type (NotFound)
name => value_importer => name (CharField)
poe_mode => NO IMPORTER => poe_mode (NotFound)
poe_type => NO IMPORTER => poe_type (NotFound)
type => choice_importer => type (CharField)
- dcim.location => dcim.location -------------------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
level => Disabled with reason: Tree fields doesn't need to be imported
lft => Disabled with reason: Tree fields doesn't need to be imported
name => value_importer => name (CharField)
parent => location_parent_importer => parent_id (TreeNodeForeignKey)
rght => Disabled with reason: Tree fields doesn't need to be imported
site => location_parent_importer => parent_id (TreeNodeForeignKey)
slug => NO IMPORTER => slug (NotFound)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
tree_id => Disabled with reason: Tree fields doesn't need to be imported
- dcim.manufacturer => dcim.manufacturer -----------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- dcim.platform => dcim.platform -------------------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
manufacturer => relation_importer => manufacturer_id (ForeignKey)
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- dcim.powerfeed => dcim.powerfeed -----------------------------------------------------------------
_path => NO IMPORTER => _path (PrivateProperty)
amperage => integer_importer => amperage (PositiveSmallIntegerField)
available_power => integer_importer => available_power (PositiveIntegerField)
cable => relation_importer => cable_id (ForeignKey)
cable_end => NO IMPORTER => cable_end (NotFound)
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
mark_connected => NO IMPORTER => mark_connected (NotFound)
max_utilization => integer_importer => max_utilization (PositiveSmallIntegerField)
name => value_importer => name (CharField)
phase => choice_importer => phase (CharField)
power_panel => relation_importer => power_panel_id (ForeignKey)
rack => relation_importer => rack_id (ForeignKey)
status => status_importer => status_id (StatusField)
supply => choice_importer => supply (CharField)
type => choice_importer => type (CharField)
voltage => integer_importer => voltage (SmallIntegerField)
- dcim.poweroutlet => dcim.poweroutlet -------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
_path => NO IMPORTER => _path (PrivateProperty)
cable => relation_importer => cable_id (ForeignKey)
cable_end => NO IMPORTER => cable_end (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
device => relation_importer => device_id (ForeignKeyWithAutoRelatedName)
feed_leg => choice_importer => feed_leg (CharField)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
mark_connected => NO IMPORTER => mark_connected (NotFound)
module => NO IMPORTER => module (NotFound)
name => value_importer => name (CharField)
power_port => relation_importer => power_port_id (ForeignKey)
type => choice_importer => type (CharField)
- dcim.poweroutlettemplate => dcim.poweroutlettemplate ---------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
created => datetime_importer => created (DateTimeField)
description => value_importer => description (CharField)
device_type => relation_importer => device_type_id (ForeignKeyWithAutoRelatedName)
feed_leg => choice_importer => feed_leg (CharField)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
module_type => NO IMPORTER => module_type (NotFound)
name => value_importer => name (CharField)
power_port => relation_importer => power_port_template_id (ForeignKey)
type => choice_importer => type (CharField)
- dcim.powerpanel => dcim.powerpanel ---------------------------------------------------------------
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
location => location_importer => location_id (ForeignKey)
name => value_importer => name (CharField)
site => location_importer => location_id (ForeignKey)
- dcim.powerport => dcim.powerport -----------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
_path => NO IMPORTER => _path (PrivateProperty)
allocated_draw => integer_importer => allocated_draw (PositiveSmallIntegerField)
cable => relation_importer => cable_id (ForeignKey)
cable_end => NO IMPORTER => cable_end (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
device => relation_importer => device_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
mark_connected => NO IMPORTER => mark_connected (NotFound)
maximum_draw => integer_importer => maximum_draw (PositiveSmallIntegerField)
module => NO IMPORTER => module (NotFound)
name => value_importer => name (CharField)
type => choice_importer => type (CharField)
- dcim.powerporttemplate => dcim.powerporttemplate -------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
allocated_draw => integer_importer => allocated_draw (PositiveSmallIntegerField)
created => datetime_importer => created (DateTimeField)
description => value_importer => description (CharField)
device_type => relation_importer => device_type_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
maximum_draw => integer_importer => maximum_draw (PositiveSmallIntegerField)
module_type => NO IMPORTER => module_type (NotFound)
name => value_importer => name (CharField)
type => choice_importer => type (CharField)
- dcim.rack => dcim.rack ---------------------------------------------------------------------------
_abs_max_weight => NO IMPORTER => _abs_max_weight (PrivateProperty)
_abs_weight => NO IMPORTER => _abs_weight (PrivateProperty)
_name => NO IMPORTER => _name (PrivateProperty)
asset_tag => value_importer => asset_tag (CharField)
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
desc_units => value_importer => desc_units (BooleanField)
description => NO IMPORTER => description (NotFound)
facility_id => value_importer => facility_id (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
location => location_importer => location_id (ForeignKey)
max_weight => NO IMPORTER => max_weight (NotFound)
mounting_depth => NO IMPORTER => mounting_depth (NotFound)
name => value_importer => name (CharField)
outer_depth => integer_importer => outer_depth (PositiveSmallIntegerField)
outer_unit => choice_importer => outer_unit (CharField)
outer_width => integer_importer => outer_width (PositiveSmallIntegerField)
role => role_importer => role_id (RoleField)
serial => value_importer => serial (CharField)
site => location_importer => location_id (ForeignKey)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
type => choice_importer => type (CharField)
u_height => integer_importer => u_height (PositiveSmallIntegerField)
weight => NO IMPORTER => weight (NotFound)
weight_unit => NO IMPORTER => weight_unit (NotFound)
width => choice_importer => width (PositiveSmallIntegerField)
- dcim.rackreservation => dcim.rackreservation -----------------------------------------------------
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
rack => relation_importer => rack_id (ForeignKey)
tenant => relation_importer => tenant_id (ForeignKey)
units => units_importer => units (JSONField)
user => relation_importer => user_id (ForeignKey)
- dcim.rackrole => extras.role ---------------------------------------------------------------------
color => value_importer => color (CharField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- dcim.rearport => dcim.rearport -------------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
cable => relation_importer => cable_id (ForeignKey)
cable_end => NO IMPORTER => cable_end (NotFound)
color => NO IMPORTER => color (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
device => relation_importer => device_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
mark_connected => NO IMPORTER => mark_connected (NotFound)
module => NO IMPORTER => module (NotFound)
name => value_importer => name (CharField)
positions => integer_importer => positions (PositiveSmallIntegerField)
type => choice_importer => type (CharField)
- dcim.rearporttemplate => dcim.rearporttemplate ---------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
color => NO IMPORTER => color (NotFound)
created => datetime_importer => created (DateTimeField)
description => value_importer => description (CharField)
device_type => relation_importer => device_type_id (ForeignKeyWithAutoRelatedName)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
module_type => NO IMPORTER => module_type (NotFound)
name => value_importer => name (CharField)
positions => integer_importer => positions (PositiveSmallIntegerField)
type => choice_importer => type (CharField)
- dcim.region => dcim.location ---------------------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
level => Disabled with reason: Tree fields doesn't need to be imported
lft => Disabled with reason: Tree fields doesn't need to be imported
name => value_importer => name (CharField)
parent => relation_importer => parent_id (TreeNodeForeignKey)
rght => Disabled with reason: Tree fields doesn't need to be imported
slug => NO IMPORTER => slug (NotFound)
tree_id => Disabled with reason: Tree fields doesn't need to be imported
- dcim.site => dcim.location -----------------------------------------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
asns => NO IMPORTER => asns (NotFound)
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
facility => value_importer => facility (CharField)
group => site_group_importer => location_type_id (ForeignKey)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
latitude => value_importer => latitude (DecimalField)
longitude => value_importer => longitude (DecimalField)
name => value_importer => name (CharField)
physical_address => value_importer => physical_address (TextField)
region => relation_importer => parent_id (TreeNodeForeignKey)
shipping_address => value_importer => shipping_address (TextField)
slug => NO IMPORTER => slug (NotFound)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
time_zone => choice_importer => time_zone (CharField)
- dcim.sitegroup => dcim.locationtype --------------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
level => Disabled with reason: Tree fields doesn't need to be imported
lft => Disabled with reason: Tree fields doesn't need to be imported
name => value_importer => name (CharField)
parent => relation_importer => parent_id (TreeNodeForeignKey)
rght => Disabled with reason: Tree fields doesn't need to be imported
slug => NO IMPORTER => slug (NotFound)
tree_id => Disabled with reason: Tree fields doesn't need to be imported
- dcim.virtualchassis => dcim.virtualchassis -------------------------------------------------------
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
domain => value_importer => domain (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
master => relation_importer => master_id (OneToOneField)
name => value_importer => name (CharField)
- extras.customfield => extras.customfield ---------------------------------------------------------
choice_set => choices_importer => CUSTOM TARGET
content_types => content_types_importer => content_types (ManyToManyField)
created => datetime_importer => created (DateTimeField)
default => json_importer => default (JSONField)
description => value_importer => description (CharField)
filter_logic => choice_importer => filter_logic (CharField)
group_name => NO IMPORTER => group_name (NotFound)
id => uid_from_data => id (UUIDField)
label => value_importer => label (CharField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => key (SlugField)
object_type => NO IMPORTER => object_type (NotFound)
required => value_importer => required (BooleanField)
search_weight => NO IMPORTER => search_weight (NotFound)
type => fallback_importer => type (CharField)
ui_visibility => NO IMPORTER => ui_visibility (NotFound)
validation_maximum => integer_importer => validation_maximum (BigIntegerField)
validation_minimum => integer_importer => validation_minimum (BigIntegerField)
validation_regex => value_importer => validation_regex (CharField)
weight => integer_importer => weight (PositiveSmallIntegerField)
- extras.tag => extras.tag -------------------------------------------------------------------------
color => value_importer => color (CharField)
created => datetime_importer => created (DateTimeField)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- extras.taggeditem => extras.taggeditem -----------------------------------------------------------
content_type => tagged_object_importer => content_type_id (ForeignKey)
id => uid_from_data => id (UUIDField)
object_id => tagged_object_importer => object_id (UUIDField)
tag => tagged_object_importer => tag_id (ForeignKey)
- ipam.aggregate => ipam.prefix --------------------------------------------------------------------
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
date_added => NO IMPORTER => date_added (NotFound)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
prefix => value_importer => prefix (Property)
rir => relation_importer => rir_id (ForeignKey)
tenant => relation_importer => tenant_id (ForeignKey)
- ipam.ipaddress => ipam.ipaddress -----------------------------------------------------------------
address => value_importer => address (Property)
assigned_object_id => NO IMPORTER => assigned_object_id (NotFound)
assigned_object_type => NO IMPORTER => assigned_object_type (NotFound)
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
dns_name => value_importer => dns_name (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
nat_inside => relation_importer => nat_inside_id (ForeignKey)
role => role_importer => role_id (RoleField)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
vrf => NO IMPORTER => vrf (NotFound)
- ipam.prefix => ipam.prefix -----------------------------------------------------------------------
_children => NO IMPORTER => _children (PrivateProperty)
_depth => NO IMPORTER => _depth (PrivateProperty)
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
is_pool => NO IMPORTER => is_pool (NotFound)
last_updated => Disabled with reason: Last updated field is updated with each write
mark_utilized => NO IMPORTER => mark_utilized (NotFound)
prefix => value_importer => prefix (Property)
role => role_importer => role_id (RoleField)
site => location_importer => location_id (ForeignKey)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
vlan => relation_importer => vlan_id (ForeignKey)
vrf => NO IMPORTER => vrf (NotFound)
- ipam.rir => ipam.rir -----------------------------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
is_private => value_importer => is_private (BooleanField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- ipam.role => extras.role -------------------------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
weight => integer_importer => weight (PositiveSmallIntegerField)
- ipam.routetarget => ipam.routetarget -------------------------------------------------------------
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
tenant => relation_importer => tenant_id (ForeignKey)
- ipam.vlan => ipam.vlan ---------------------------------------------------------------------------
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
group => relation_importer => vlan_group_id (ForeignKey)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
role => role_importer => role_id (RoleField)
site => location_importer => location_id (ForeignKey)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
vid => integer_importer => vid (PositiveSmallIntegerField)
- ipam.vlangroup => ipam.vlangroup -----------------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
max_vid => NO IMPORTER => max_vid (NotFound)
min_vid => NO IMPORTER => min_vid (NotFound)
name => value_importer => name (CharField)
scope_id => NO IMPORTER => scope_id (NotFound)
scope_type => NO IMPORTER => scope_type (NotFound)
slug => NO IMPORTER => slug (NotFound)
- ipam.vrf => ipam.vrf -----------------------------------------------------------------------------
comments => NO IMPORTER => comments (NotFound)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
enforce_unique => NO IMPORTER => enforce_unique (NotFound)
export_targets => uuids_importer => export_targets (ManyToManyField)
id => uid_from_data => id (UUIDField)
import_targets => uuids_importer => import_targets (ManyToManyField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
rd => value_importer => rd (CharField)
tenant => relation_importer => tenant_id (ForeignKey)
- tenancy.tenant => tenancy.tenant -----------------------------------------------------------------
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
group => relation_importer => tenant_group_id (ForeignKey)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- tenancy.tenantgroup => tenancy.tenantgroup -------------------------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
level => Disabled with reason: Tree fields doesn't need to be imported
lft => Disabled with reason: Tree fields doesn't need to be imported
name => value_importer => name (CharField)
parent => relation_importer => parent_id (TreeNodeForeignKey)
rght => Disabled with reason: Tree fields doesn't need to be imported
slug => NO IMPORTER => slug (NotFound)
tree_id => Disabled with reason: Tree fields doesn't need to be imported
- virtualization.cluster => virtualization.cluster -------------------------------------------------
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
group => relation_importer => cluster_group_id (ForeignKey)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
site => location_importer => location_id (ForeignKey)
status => NO IMPORTER => status (NotFound)
tenant => relation_importer => tenant_id (ForeignKey)
type => relation_importer => cluster_type_id (ForeignKey)
- virtualization.clustergroup => virtualization.clustergroup ---------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- virtualization.clustertype => virtualization.clustertype -----------------------------------------
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
name => value_importer => name (CharField)
slug => NO IMPORTER => slug (NotFound)
- virtualization.virtualmachine => virtualization.virtualmachine -----------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
cluster => relation_importer => cluster_id (ForeignKey)
comments => value_importer => comments (TextField)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => NO IMPORTER => description (NotFound)
device => NO IMPORTER => device (NotFound)
disk => integer_importer => disk (PositiveIntegerField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
local_context_data => NO IMPORTER => local_context_data (NotFound)
memory => integer_importer => memory (PositiveIntegerField)
name => value_importer => name (CharField)
platform => relation_importer => platform_id (ForeignKey)
primary_ip4 => relation_importer => primary_ip4_id (ForeignKey)
primary_ip6 => relation_importer => primary_ip6_id (ForeignKey)
role => role_importer => role_id (RoleField)
site => NO IMPORTER => site (NotFound)
status => status_importer => status_id (StatusField)
tenant => relation_importer => tenant_id (ForeignKey)
vcpus => integer_importer => vcpus (PositiveSmallIntegerField)
- virtualization.vminterface => virtualization.vminterface -----------------------------------------
_name => NO IMPORTER => _name (PrivateProperty)
bridge => relation_importer => bridge_id (ForeignKey)
created => datetime_importer => created (DateTimeField)
custom_field_data => value_importer => custom_field_data (CustomFieldData)
description => value_importer => description (CharField)
enabled => value_importer => enabled (BooleanField)
id => uid_from_data => id (UUIDField)
last_updated => Disabled with reason: Last updated field is updated with each write
mac_address => value_importer => mac_address (CharField)
mode => choice_importer => mode (CharField)
mtu => integer_importer => mtu (PositiveIntegerField)
name => value_importer => name (CharField)
parent => relation_importer => parent_interface_id (ForeignKey)
tagged_vlans => uuids_importer => tagged_vlans (ManyToManyField)
untagged_vlan => relation_importer => untagged_vlan_id (ForeignKey)
virtual_machine => relation_importer => virtual_machine_id (ForeignKey)
vrf => relation_importer => vrf_id (ForeignKey)
* End of Import Summary. ***************************************************************************
```
