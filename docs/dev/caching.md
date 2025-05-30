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
