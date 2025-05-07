# Understanding Caching in the NetBox Importer

Caching plays a crucial role in the NetBox to Nautobot data import process. This document explains the caching mechanisms, their purpose, and provides practical examples.

## Source Identifiers to Nautobot Primary Keys Mapping

Maps source identifiers to Nautobot primary keys, ensuring consistent references. This caching is separate for each `SourceModelWrapper` instance and is defined in `_uid_to_pk_cache` attribute.

It's possible to manually pre-cache particular source IDs to Nautobot primary keys. This is necessary to link existing Nautobot objects to the source data.

To cache particular source record to an existing Nautobot primary key, use `SourceModelWrapper.cache_record_uids` method. This is used e.g. to properly link existing Nautobot Roles to the source data, as NetBox has multiple models for separate roles, while Nautobot has a single model for all roles.

For more information about primary keys mapping see [UID to PK Mapping](./primary_keys.md).

## Records Caching

### Caching Record Data

This is the base caching method used for other records caching techniques. It caches data for optional later use. If cached record is referenced by imported data, it will be imported automatically; otherwise, it will be ignored.

To cache record data, use `SourceModelWrapper.cache_record` method.

### Setting the Default Reference

It's possible to specify the default reference for a model. This affects relation fields referencing this model, but with missing or (NULL) source data. The record is cached, when the default reference is set.

The following example creates a default reference for the `dcim.manufacturer` model. All empty `manufacturer` field values will be replaced with reference to `Unknown` manufacturer.

```python
def configure_importer(adapter):
    manufacturer = adapter.configure_model(
        "dcim.manufacturer",
        default_reference={
            "id": "Unknown",
            "name": "Unknown",
        },
    )
```

### Caching Dummy Objects

Dummy objects are useful when it's not possible to use a single default reference, due to validation issues, but it's still necessary to create placeholder objects for the relationship. This is used e.g.: to create dummy circuit terminations.

To allow creating placeholder objects for the model, you need to implement and register a custom function that fills the required fields for the dummy object. Then you can use the `cache_dummy_object` method to create a dummy object for the missing data.

Example of using this feature:

```python
def setup(adapter):
    # Define custom function to fill required fields for the dummy object
    def my_dummy_data_filler(data: RecordData, suffix: str):
        """Fill required fields for a dummy object"""
        if "name" not in data:
            data["name"] = f"Dummy-{suffix}"
        if "slug" not in data:
            data["slug"] = f"dummy-{suffix.lower()}"
        data["status"] = "active"

    # Configure the referenced model to fill dummy data
    adapter.configure_model(
        "my_app.my_model",
        fill_dummy_data=my_dummy_data_filler
    )

    # Setup the referencing field importer
    def define_my_model_ref(field: SourceField):
        """Define the field importer."""

        def my_ref_importer(source: RecordData, target: DiffSyncBaseModel):
            value = field.get_source_value(source)

            if not value:
                # Cache the dummy object, provide unique suffix (ID of imported record) to generate unique Nautobot UUID
                # This creates a new placeholder object for empty `my_model_ref` field
                value = my_model.cache_dummy_object(source["id"])

            field.set_nautobot_value(target, value)
    
        # Register the field importer
        field.set_importer(my_ref_importer)

    # Configure the referencing model, to cache the dummy object, when missing
    adapter.configure_model(
        "my_app.my_another_model",
        fields={
            # This field references `my_app.my_model` model.
            # This is necessary when Nautobot requires unique values for the field, but the source data doesn't provide it.
            "my_model_ref": define_my_model_ref,
        },
    )
```
