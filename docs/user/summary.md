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

The first section is the import summary. It shows a summary from the underlying `DiffSync` library.

```
= Import Summary: ==============================================================
- DiffSync Summary: ------------------------------------------------------------
create: 5865
update: 1
delete: 0
no-change: 4
skip: 119
```

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
ValidationIssue(uid=UUID('f2ee9737-42d8-5093-a349-be97765a39e0'), name='P1-2A', error=ValidationError(['Rack R102 (Row 1) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('c0e96716-af7f-5b78-8210-d51b55fa53d2'), name='P1-1A', error=ValidationError(['Rack R101 (Row 1) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('7c07894e-9772-5e1c-a418-bdf3fd58e7c3'), name='P1-7A', error=ValidationError(['Rack R107 (Row 1) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('47f69d3d-8fcd-5b63-8695-21aa51fb4fbf'), name='P2-9B', error=ValidationError(['Rack R201 (Row 2) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('b3bfb863-c40a-5c49-b82e-1095037d3578'), name='P3-3A', error=ValidationError(['Rack R303 (Row 3) and power panel Panel 3 (MDF) are in different locations']))
ValidationIssue(uid=UUID('a5511926-c977-593b-9bf1-57c8175be85d'), name='P2-5B', error=ValidationError(['Rack R105 (Row 1) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('e1b4bb92-803c-59f4-90a7-4f5deb95abc2'), name='P4-2B', error=ValidationError(['Rack R302 (Row 3) and power panel Panel 4 (MDF) are in different locations']))
ValidationIssue(uid=UUID('e04582bd-f2cb-5deb-b374-be9260cd5b27'), name='P4-6B', error=ValidationError(['Rack R306 (Row 3) and power panel Panel 4 (MDF) are in different locations']))
ValidationIssue(uid=UUID('05541f06-08c9-5d84-a8b6-13ce3cd45938'), name='P3-8A', error=ValidationError(['Rack R308 (Row 3) and power panel Panel 3 (MDF) are in different locations']))
ValidationIssue(uid=UUID('b9c591cd-fdc0-5cf2-83c4-400554b811cd'), name='P1-16A', error=ValidationError(['Rack R208 (Row 2) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('53ed215b-9003-522d-9cb1-d48dbb18fdc2'), name='P3-7A', error=ValidationError(['Rack R307 (Row 3) and power panel Panel 3 (MDF) are in different locations']))
ValidationIssue(uid=UUID('10da56b6-09b1-5da6-9505-d9253863e062'), name='P3-1A', error=ValidationError(['Rack R301 (Row 3) and power panel Panel 3 (MDF) are in different locations']))
ValidationIssue(uid=UUID('3f702c58-7dea-5b78-a007-17f40b465810'), name='P1-10A', error=ValidationError(['Rack R202 (Row 2) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('5fa35cf7-5d55-5533-99ee-7d1ecaa69856'), name='P2-1B', error=ValidationError(['Rack R101 (Row 1) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('b4031fa2-14a6-5d06-a3a2-3a3376b10d72'), name='P1-11A', error=ValidationError(['Rack R203 (Row 2) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('d951d5fc-81be-51ae-98a1-7759c859d904'), name='P4-5B', error=ValidationError(['Rack R305 (Row 3) and power panel Panel 4 (MDF) are in different locations']))
ValidationIssue(uid=UUID('29b6b9f0-f50a-592c-8e3f-e415a0bf4cd4'), name='P4-1B', error=ValidationError(['Rack R301 (Row 3) and power panel Panel 4 (MDF) are in different locations']))
ValidationIssue(uid=UUID('05f5bb91-e84c-5908-8d9a-8256959bfcab'), name='P2-11B', error=ValidationError(['Rack R203 (Row 2) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('31f1abb3-660f-5a57-9256-42be3d5b75cf'), name='P2-3B', error=ValidationError(['Rack R103 (Row 1) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('cd4f8f27-620f-59fe-aa9a-4c13ff4a7274'), name='P1-12A', error=ValidationError(['Rack R204 (Row 2) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('e1672072-7885-5330-a7dd-52f3769d4863'), name='P1-5A', error=ValidationError(['Rack R105 (Row 1) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('bb4485d0-144b-506f-a8ab-faf523304cf8'), name='P4-7B', error=ValidationError(['Rack R307 (Row 3) and power panel Panel 4 (MDF) are in different locations']))
ValidationIssue(uid=UUID('c6b3c62b-5f0d-51d1-95d9-761914979d47'), name='P3-6A', error=ValidationError(['Rack R306 (Row 3) and power panel Panel 3 (MDF) are in different locations']))
ValidationIssue(uid=UUID('7eae2a15-d2d0-52ab-bfcf-3cf6823078cf'), name='P2-7B', error=ValidationError(['Rack R107 (Row 1) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('5a2f51ea-7a05-53d2-8a47-cd383629a343'), name='P1-13A', error=ValidationError(['Rack R205 (Row 2) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('8cf662de-a918-5648-b152-d71da75a7392'), name='P3-4A', error=ValidationError(['Rack R304 (Row 3) and power panel Panel 3 (MDF) are in different locations']))
ValidationIssue(uid=UUID('07316815-d36d-552d-8859-03e7fe09354a'), name='P2-13B', error=ValidationError(['Rack R205 (Row 2) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('194e2d64-c904-59bc-af2c-e040beb3aeac'), name='P2-14B', error=ValidationError(['Rack R206 (Row 2) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('3213730d-18bd-5a3a-9828-4ab023ed4652'), name='P1-6A', error=ValidationError(['Rack R106 (Row 1) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('1f4b42df-43ce-52aa-8a61-4a19ce1af962'), name='P4-3B', error=ValidationError(['Rack R303 (Row 3) and power panel Panel 4 (MDF) are in different locations']))
ValidationIssue(uid=UUID('416a01e5-fbf9-522e-b9e9-4037cf8c984f'), name='P1-4A', error=ValidationError(['Rack R104 (Row 1) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('fcb61481-0da8-5412-b68b-2463016a017d'), name='P2-12B', error=ValidationError(['Rack R204 (Row 2) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('c2893189-8044-5d85-8e91-7832c201474d'), name='P1-8A', error=ValidationError(['Rack R108 (Row 1) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('06ebb1db-aaa0-5b24-a832-8ca1671f8b0a'), name='P2-4B', error=ValidationError(['Rack R104 (Row 1) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('a7c6bcef-dbe4-51cd-a6d0-14ab5facbe5e'), name='P1-3A', error=ValidationError(['Rack R103 (Row 1) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('451c4aad-d892-5114-8724-be2f8148c322'), name='P2-2B', error=ValidationError(['Rack R102 (Row 1) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('7257a622-3ca0-5163-8b6e-5e88c573b17e'), name='P2-16B', error=ValidationError(['Rack R208 (Row 2) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('6a1a4ac2-e77b-526b-9aa6-8c7903e5f572'), name='P2-8B', error=ValidationError(['Rack R108 (Row 1) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('87cf96f1-95fa-546c-9665-977f42764f8b'), name='P4-4B', error=ValidationError(['Rack R304 (Row 3) and power panel Panel 4 (MDF) are in different locations']))
ValidationIssue(uid=UUID('314fead6-ffae-51f7-abb0-2edcf7d6da49'), name='P3-2A', error=ValidationError(['Rack R302 (Row 3) and power panel Panel 3 (MDF) are in different locations']))
ValidationIssue(uid=UUID('20b3c4c0-eb30-5f8b-adcf-20e4fa5d0061'), name='P2-15B', error=ValidationError(['Rack R207 (Row 2) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('0434ed4d-cc76-5051-a38c-b84ed32de2c1'), name='P2-6B', error=ValidationError(['Rack R106 (Row 1) and power panel Panel 2 (MDF) are in different locations']))
ValidationIssue(uid=UUID('6203a499-6777-5cd0-841b-fa6339c48890'), name='P1-9A', error=ValidationError(['Rack R201 (Row 2) and power panel Panel 1 (MDF) are in different locations']))
ValidationIssue(uid=UUID('3338c701-47fd-513e-945a-78a98b84d7f0'), name='P4-8B', error=ValidationError(['Rack R308 (Row 3) and power panel Panel 4 (MDF) are in different locations']))
................................................................................
Total validation issues: 48
```

## Content Types Mapping Deviations

This section shows deviations from NetBox content type to Nautobot content type. Only those content types that differ between NetBox and Nautobot are shown.

```
- Content Types Mapping Deviations: ----------------------------------------------------
  Mapping deviations from source content type to Nautobot content type
sessions.session | Disabled with reason: Nautobot has own sessions, sessions should never cross apps.
admin.logentry | Disabled with reason: Not directly used in Nautobot.
users.userconfig: Nautobot Model Not Found
auth.permission | Disabled with reason: Handled via a Nautobot model and may not be a 1 to 1.
auth.user => users.user
dcim.sitegroup => dcim.locationtype
dcim.region => dcim.location
dcim.site => dcim.location
dcim.cablepath | Disabled with reason: Recreated in Nautobot on signal when circuit termination is created
dcim.rackrole => extras.role
dcim.cabletermination_a => dcim.cable
dcim.cabletermination_b => dcim.cable
dcim.devicerole => extras.role
ipam.role => extras.role
ipam.aggregate => ipam.prefix
dcim.modulebay: Nautobot Model Not Found
dcim.modulebaytemplate: Nautobot Model Not Found
dcim.moduletype: Nautobot Model Not Found
dcim.module: Nautobot Model Not Found
ipam.asn: Nautobot Model Not Found
ipam.iprange: Nautobot Model Not Found
tenancy.contactgroup: Nautobot Model Not Found
tenancy.contactrole: Nautobot Model Not Found
tenancy.contact: Nautobot Model Not Found
tenancy.contactassignment: Nautobot Model Not Found
dcim.inventoryitemrole: Nautobot Model Not Found
dcim.inventoryitemtemplate: Nautobot Model Not Found
dcim.cabletermination: Nautobot Model Not Found
dcim.virtualdevicecontext: Nautobot Model Not Found
ipam.fhrpgroup: Nautobot Model Not Found
ipam.fhrpgroupassignment: Nautobot Model Not Found
ipam.servicetemplate: Nautobot Model Not Found
ipam.l2vpn: Nautobot Model Not Found
ipam.l2vpntermination: Nautobot Model Not Found
extras.report: Nautobot Model Not Found
extras.script: Nautobot Model Not Found
extras.journalentry: Nautobot Model Not Found
extras.configrevision: Nautobot Model Not Found
extras.savedfilter: Nautobot Model Not Found
extras.cachedvalue: Nautobot Model Not Found
extras.branch: Nautobot Model Not Found
extras.stagedchange: Nautobot Model Not Found
users.adminuser: Nautobot Model Not Found
wireless.wirelesslangroup: Nautobot Model Not Found
wireless.wirelesslan: Nautobot Model Not Found
wireless.wirelesslink: Nautobot Model Not Found
django_rq.queue: Nautobot Model Not Found
secrets.secret: Nautobot Model Not Found
secrets.secretrole: Nautobot Model Not Found
secrets.userkey: Nautobot Model Not Found
secrets.sessionkey: Nautobot Model Not Found
```

## Content Types Back Mapping

This section shows back mapping deviations from Nautobot content types to NetBox content types. Only those content types that differ between NetBox and Nautobot are shown.

"Ambiguous" means that there are multiple NetBox content types that map to the same Nautobot content type.

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
    - `SKIPPED` means the field is intentionally skipped by the importer.
    - `(ReadOnlyProperty')` marks fields that are read-only properties in Nautobot and can't be imported.
    - `(PrivateProperty)` marks fields that are prefixed with an underscore `_` and are considered private properties. Those fields are not imported.
    - `(NotFound)` indicates the field is not found in Nautobot and can't be imported.
    - `(DoNotImportLastUpdated)` are fields that are not imported as they are automatically updated by Nautobot.
    - `CUSTOM IMPORTER` marks fields that do not have a direct mapping to Nautobot and can potentially be imported to other content types, e.g., NetBox's `CustomField.choices` field to Nautobot's `CustomFieldChoice` instances.
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
choices (CUSTOM) => CUSTOM IMPORTER
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
last_login (DATA) (CUSTOM) => SKIPPED
password (DATA) (CUSTOM) => SKIPPED
user_permissions (DATA) (CUSTOM) => SKIPPED
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
permissions (DATA) (CUSTOM) => SKIPPED
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
tree_id (CUSTOM) => SKIPPED
lft (CUSTOM) => SKIPPED
rght (CUSTOM) => SKIPPED
level (CUSTOM) => SKIPPED
name (DATA) => name (CharField)
nestable (DATA) => nestable (BooleanField)
content_types (DATA) => content_types (ManyToManyField)
parent (DATA) => parent_id (TreeNodeForeignKey)
. dcim.sitegroup => dcim.locationtype ..........................................
id (DATA) (CUSTOM) => id (UUIDField)
tree_id (DATA) (CUSTOM) => SKIPPED
lft (DATA) (CUSTOM) => SKIPPED
rght (DATA) (CUSTOM) => SKIPPED
level (DATA) (CUSTOM) => SKIPPED
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
tree_id (DATA) (CUSTOM) => SKIPPED
lft (DATA) (CUSTOM) => SKIPPED
rght (DATA) (CUSTOM) => SKIPPED
level (DATA) (CUSTOM) => SKIPPED
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
tree_id (CUSTOM) => SKIPPED
lft (CUSTOM) => SKIPPED
rght (CUSTOM) => SKIPPED
level (CUSTOM) => SKIPPED
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
tree_id (DATA) (CUSTOM) => SKIPPED
lft (DATA) (CUSTOM) => SKIPPED
rght (DATA) (CUSTOM) => SKIPPED
level (DATA) (CUSTOM) => SKIPPED
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
. dcim.cabletermination_a => dcim.cable ........................................
id (DATA) (CUSTOM) => id (UUIDField)
termination_a (CUSTOM) => termination_a (GenericForeignKey)
_device (DATA) => _device (PrivateProperty)
_rack (DATA) => _rack (PrivateProperty)
_location (DATA) => _location (PrivateProperty)
_site (DATA) => _site (PrivateProperty)
termination_a_type (DATA) (CUSTOM) => termination_a (GenericForeignKey)
termination_a_id (DATA) (CUSTOM) => termination_a (GenericForeignKey)
. dcim.cabletermination_b => dcim.cable ........................................
id (DATA) (CUSTOM) => id (UUIDField)
termination_b (CUSTOM) => termination_b (GenericForeignKey)
_device (DATA) => _device (PrivateProperty)
_rack (DATA) => _rack (PrivateProperty)
_location (DATA) => _location (PrivateProperty)
_site (DATA) => _site (PrivateProperty)
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
front_image (DATA) (CUSTOM) => SKIPPED
rear_image (DATA) (CUSTOM) => SKIPPED
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
tree_id (DATA) (CUSTOM) => SKIPPED
lft (DATA) (CUSTOM) => SKIPPED
rght (DATA) (CUSTOM) => SKIPPED
level (DATA) (CUSTOM) => SKIPPED
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
