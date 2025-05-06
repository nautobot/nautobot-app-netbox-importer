# Understanding Caching in the NetBox Importer

Caching plays a crucial role in the NetBox to Nautobot data import process. This document explains the caching mechanisms, their purpose, and provides practical examples.

## Source Identifiers to Nautobot Primary Keys Mapping

Maps source identifiers to Nautobot primary keys, ensuring consistent references. This caching is separate for each `SourceModelWrapper` instance and is defined in `_uid_to_pk_cache` attribute.

It's possible to manually pre-cache particular source IDs to Nautobot primary keys. This is necessary to link existing Nautobot objects to the source data.

To cache particular source record to an existing Nautobot primary key, use `SourceModelWrapper.cache_record_uids` method. This is used e.g. to properly link existing Nautobot Roles to the source data.

For more information about primary keys mapping see [UID to PK Mapping](./primary_keys.md).

## Records Caching

### Caching Record Data

This is the base caching method used for other records caching techniques. It caches data for optional later use. If cached record is referenced by imported data, it will be imported automatically; otherwise, it will be ignored.

To cache record data, use `SourceModelWrapper.cache_record` method.

### Setting the Default Reference

It's possible to specify the default reference for a model. This affects relation fields referencing this model, but with missing source data. Specifying the default reference automatically caches the record.

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

Dummy objects are useful when it's not possible to use a single default reference, due to validation issues, but it's still necessary to create a placeholder objects for the relationship. This is used e.g.: to create dummy circuit terminations.

You can provide a custom function to fill dummy data:

```python
def my_dummy_data_filler(data, suffix):
    """Fill required fields for a dummy object"""
    if "name" not in data:
        data["name"] = f"Dummy-{suffix}"
    if "slug" not in data:
        data["slug"] = f"dummy-{suffix.lower()}"
    data["status"] = "active"

# Then configure the wrapper to use it
adapter.configure_model(
    "dcim.location",
    fill_dummy_data=my_dummy_data_filler
)
```

Then you can use the `cache_dummy_object` method to create a dummy object for the given data:
