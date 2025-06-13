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

## Content Types References

In Nautobot models, such as `Role` or `Status`, the `content_types` field stores all content types that references this model. To properly populate this field, references to all instances are cached in the `SourceModelWrapper.references` dictionary.

### References Configuration Options

In `adapter.configure_model()`, you can control reference handling with:

- `disable_related_reference`:

    When set to `True`, prevents the model from collecting references:

    ```python
    adapter.configure_model(
        content_type="dcim.device",
        disable_related_reference=True
    )
    ```

    Use when a model shouldn't participate in reference tracking.

- `forward_references`:

    Custom function to delegate reference handling to another model:

    ```python
    def custom_forward_handler(wrapper, references):
        # Forward references to another wrapper
        other_wrapper = adapter.get_or_create_wrapper("other.model")
        other_wrapper.references.update(references)

    adapter.configure_model(
        content_type="dcim.device",
        forward_references=custom_forward_handler
    )
    ```

    Use when references need to be consolidated from multiple source models to a single Nautobot model, e.g. for locations.

### Reference Collection

During import, when an instances reference another instance, the reference is recorded using:

```python
wrapper.add_reference(related_wrapper, uid)
```

This adds the source wrapper to the referenced model's `references` dictionary, keyed by the instance UID. Most field importers handling relationships call this method to track references.

### Reference Processing

After all data is imported, `post_process_references()` is called on each wrapper to handle the collected references:

When `forward_references` is defined, references are not stored for the current model instance, but rather forwarded to another model instance.

When `disable_related_reference` is not set, the references are processed to populate the `content_types` field in Nautobot models.

Reference tracking is also used to store cached instances to Nautobot. Importer skips cached only instances, when not referenced by any other instance.

### Content Types Field Population

During reference processing, the `content_types` field is populated with all content types referencing particular instance, e.g. `Role`, `Status`, etc.
