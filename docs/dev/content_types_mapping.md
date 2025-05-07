# Content Types Mapping

Each NetBox model is represented by a `SourceModelWrapper` class instance.

Complementary to the `SourceModelWrapper`, for each imported Nautobot model, there is a `NautobotModelWrapper` class instance.

`SourceModelWrapper` links to one or none (if disabled) `NautobotModelWrapper` instances. This means that one Nautobot model can be referenced by multiple NetBox models.

## Creating Multiple Nautobot Model instances from Single NetBox Source Record

To create multiple Nautobot model instances from single NetBox model, you can hook custom `pre_import` function containing multiple `import_record()` calls. This function is executed before the data import, allowing you to modify the source data and create multiple records from one source record.

This feature is used e.g. to create custom field choices instances, as Nautobot has a separate model for custom field choices, while NetBox has these choices as a field in `CustomField` model. For details, check [custom fields setup source code](https://github.com/nautobot/nautobot-app-netbox-importer/blob/develop/nautobot_netbox_importer/diffsync/models/custom_fields.py).

## Content Types Back Mapping

Back mapping means mapping content types back from Nautobot to NetBox. When multiple NetBox models are mapped to one Nautobot model, it's not possible to determine which NetBox model should be used for the back mapping. In such case `ambiguous` mapping is outputted in summary, see [Import Summary documentation](../user/summary.md).

This back mapping is used when creating `SourceModelWrapper` instances from Nautobot data.

When there isn't clear 1:1 back mapping from Nautobot model to NetBox model, it isn't possible to import existing Nautobot data for `diffsync` comparison. This affects the import, when there are already existing Nautobot records in the Nautobot database.

## Content Types Mapping in Stages

NetBox importer maps NetBox content types to Nautobot content types in stages described bellow.

### Defining the Source Structure Deviations

In this stage, each model configured by `adapter.configure_model()` is linked to the provided Nautobot content type.

!!! Note
    Both, the `SourceModelWrapper` and `NautobotModelWrapper` are created, if not already present.

### Reading Source Structure

In the first data iteration, the system creates or updates `SourceModelWrapper` based on the source data.

### Importing the Data

In the second data iteration, the importer reads content types first as those are placed on the top of the import data. This allows to map each `SourceModelWrapper` to NetBox content type ID for the later data conversions, when content types are referenced by their IDs.

TBD: Consider moving this to first iteration.
