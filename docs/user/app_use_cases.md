# Using the App

This document describes common use-cases and scenarios for this App.

## General Usage

This app provides `import_netbox` management command to import data from NetBox with the following options:

```bash
nautobot-server import_netbox --help

usage: nautobot-server import_netbox [-h] [--dry-run] [--summary] [--field-mapping] [--update-paths] [--bypass-data-validation] [--sitegroup-parent-always-region] [--fix-powerfeed-locations] [--version]
                                     [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] [--no-color] [--force-color] [--skip-checks]
                                     json_file

Import a NetBox JSON data dump into Nautobot's database

positional arguments:
  json_file             Path to the JSON file to import.

options:
  -h, --help            show this help message and exit
  --dry-run             Do not write any data to the database.
  --summary             Show a summary of the import.
  --field-mapping       Show a mapping of NetBox fields to Nautobot fields. Only printed when `--summary` is also specified.
  --update-paths        Call management command `trace_paths` to update paths after the import.
  --bypass-data-validation
                        Bypass as much of Nautobot's internal data validation logic as possible, allowing the import of data from NetBox that would be rejected as invalid if entered as-is through the GUI or
                        REST API. USE WITH CAUTION: it is generally more desirable to *take note* of any data validation errors, *correct* the invalid data in NetBox, and *re-import* with the corrected data!
  --sitegroup-parent-always-region
                        When importing `dcim.sitegroup` to `dcim.locationtype`, always set the parent of a site group, to be a `Region` location type. This is a workaround to fix validation errors `'A
                        Location of type Location may only have a Location of the same type as its parent.'`.
  --fix-powerfeed-locations
                        Fix panel location to match rack location based on powerfeed.
...
```

### Importing Data Into Nautobot

This chapter outlines how to import data from NetBox into Nautobot.

#### Getting a Data Export from NetBox

Run the following command from the NetBox root directory to create a JSON file (`/tmp/netbox_data.json`) that contains the contents of your NetBox database:

```shell
./manage.py dumpdata \
    --traceback \
    --format=json \
    --exclude extras.ObjectChange \
    --output=/tmp/netbox_data.json
```

It's possible to exclude other models from the export, but the command provided above is a good starting point. The `import_netbox` command will skip models that are not present in the Nautobot database.

!!! tip
    Change log `ObjectChange` records are not included in the export command above because they can contain a massive amount of data. It's possible to import change log records in the next step, as described later in this document.

#### Dry Run

Before importing data into Nautobot, it's a good idea to process a dry run to see what will happen. This will not write any data to the database, but will show you what will happen if you run the import.

```shell
nautobot-server import_netbox \
    --dry-run \
    --summary \
    --field-mapping \
    --bypass-data-validation \
    /tmp/netbox_data.json
```

The following document describes [summary with mapping from NetBox 3.6 to Nautobot 2.1.0](./summary.md). Other versions mappings can vary.

#### Importing Data into Nautobot

Within the Nautobot application environment, run `nautobot-server import_netbox <json_file>`; for example: `nautobot-server import_netbox /tmp/netbox_data.json`.

Consider using the above-mentioned command options based on a dry run.

#### Data Validation and Error Handling

Note that the importer *does* apply Nautobot's data validation standards to the data records as it imports them. If any data records fail to meet data validation, you will see detailed error messages. For example, the following error might be generated if your NetBox data contains a rack that is assigned to a different location than the power panel.

```
  ValidationIssue(uid=UUID(0434ed4d-cc76-5051-a38c-b84ed32de2c1), name=P2-6B, error=ValidationError(['Rack R106 (Row 1)' and 'Power Panel Panel 2 (MDF)' are in different locations]))
```

In this case, the import of this Rack into Nautobot will fail, and you may encounter a series of cascading errors as other objects dependent on this Rack (e.g., Devices) also fail due to the absence of the Rack.

Normally, the correct response to this sort of error is to understand the cause of the error, log into your NetBox instance, and correct the invalid data. Then, re-export the data from NetBox and re-run the importer.

**If**, however, fixing the source data in NetBox is not possible for whatever reason, you **can** instruct the importer to import the data *even if it fails Nautobot's data validation checks*, by specifying the `--bypass-data-validation` option. This **will** result in your Nautobot database containing invalid data. As a result, you will want to rectify this in Nautobot as soon as possible to avoid unexpected errors in the future.

When using the `--bypass-data-validation` option, data validation checks are still run, but any failures will be logged (rather than causing the import process to throw errors), enabling you to be aware of any issues that will need to be remediated in Nautobot.

To address this specific issue, you can use the `--fix-powerfeed-locations` option to adjust panel locations to match rack locations based on the power feed object. Always verify the resulting data, as this option modifies affected panel locations.

### Importing Change Log Records

Because the database's change log can contain a massive amount of data, and often this historical information does not need to be imported, `ObjectChange` records are not included in the database export command above.

To import `ObjectChange` records specifically, **after** the previous NetBox import process has succeeded, you can do the following.

#### Getting Change Log Only from NetBox

From within the NetBox root directory, run the following command to create a JSON file (`/tmp/netbox_objectchange.json`).

```shell
./manage.py dumpdata \
    --traceback \
    --format=json \
    --output=/tmp/netbox_objectchange.json \
    contenttypes.ContentType \
    extras.ObjectChange
```

Don't forget to add `ContentType` model to the export command above, otherwise importer will not be able to map `ObjectChange` records to their corresponding objects.

#### Importing Change Log into Nautobot

From within the Nautobot application environment, run `nautobot-server import_netbox <json_file_only_objectchanges>`, for example, `nautobot-server import_netbox /tmp/netbox_objectchange.json`. This will skip all object change records that are not possible to map to their corresponding objects.
