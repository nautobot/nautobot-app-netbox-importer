# Frequently Asked Questions

## What has to be done to support a minor NetBox version?

When NetBox adds new fields and models that deviate from Nautobot, the following steps should be taken:

1. Define the deviations accordingly in `nautobot_netbox_importer/diffsync/models/<appropriate>.py` file.

- For examples, check other files in that directory.
- When adding a new file, remember to register it in `nautobot_netbox_importer/adapter/netbox.py` file using `register_adapter_setup()`.

2. Add appropriate `version` key to `_INPUTS`, `_EXPECTED_SUMMARY`, and other `_EXPECTED_<name>` dictionaries in the `nautobot_netbox_importer/tests/test_import.py` file.

3. Run tests, and let the test suite create samples for new models.

4. Re-run tests and check the failure messages. Update `_EXPECTED_<name>` statistics mentioned earlier accordingly.

### What has to be done if NetBox or Nautobot changes a field's data type?

Field conversions are handled by the default importers most of the time, with the following exceptions:

1. JSON fields don't have a defined structure, so the importer can't convert them automatically if the structure differs between NetBox and Nautobot. For example, check the `units` field in the `nautobot_netbox_importer/diffsync/models/dcim.py` file.

The following code snippet shows how to specify the definition function for the `units` field:

```python
adapter.configure_model(
  "dcim.rackreservation",
  fields={
      "units": _define_units,
  },
)
```

The field definition should map the NetBox field to Nautobot and register an importer for the field:

```python
def _define_units(field: SourceField) -> None:
  def importer(source: RecordData, target: DiffSyncBaseModel) -> None:
      # In NetBox 3.4, units is a `list[int]`; previous versions use a JSON string with a list of strings.
      units = source.get(field.name, None)

      # Empty values can be ignored.
      if units in EMPTY_VALUES:
          return

      # Convert from NetBox format to Nautobot format.
      if isinstance(units, str):
          units = json.loads(units)
          if units:
              units = [int(unit) for unit in units]

      # Store the value in the target DiffSyncModel instance.
      setattr(target, field.nautobot.name, units)

  # Map the field from NetBox to Nautobot and register the importer.
  # The Nautobot field name is the same as the NetBox field name in this case.
  field.set_importer(importer)
```

2. Conversion between different field types is supported; however, it can fail depending on the data content. For instance, converting `str` to `int` will fail if the string contains non-numeric characters.

### What has to be done if NetBox or Nautobot changes a relation from 1-to-many to many-to-many?

Relation field conversions are handled by the default importers in most cases, with the following exception:

- NetBox many-to-many relations can't be converted to Nautobot 1-to-many or 1-to-1 relations.

### What has to be done if NetBox or Nautobot adds a new model?

If the model has the same content type and fields as the Nautobot model, then no action is required; the importer will handle it automatically.

Otherwise, it's necessary to define the deviations between the NetBox and Nautobot models in the `nautobot_netbox_importer/diffsync/adapters/<appropriate>.py` file and register the setup function in the `nautobot_netbox_importer/adapter/netbox.py` file using `register_adapter_setup()` as described above.

## What has to be done to support a minor Nautobot version?

No specific changes to tests should be necessary. The only action required is to cover all deviations between NetBox and Nautobot models in the `nautobot_netbox_importer/diffsync/adapters/<appropriate>.py` file as described above.

## What has to be done to support a major NetBox version?

A new major version of the `nautobot-netbox-importer` package should be released to address updated deviations between NetBox and Nautobot models, independent of the previous major version.

## What has to be done to support a major Nautobot version?

Similar to the previous question, a new independent release of the `nautobot-netbox-importer` package should be released.

## What has to be done to support a Nautobot App?

To support a Nautobot App, carry out the following steps:

1. Add the app as an extra dependency in the `pyproject.toml` file. Be sure to include all extra dependencies in the `all` group as well.

2. Configure the app in the `development/nautobot_config.py` file.

3. Run the commands:

```bash
invoke lock
invoke build
```

4. Define the deviations between NetBox and Nautobot models in the `nautobot_netbox_importer/diffsync/adapters/<app name>.py` file.

Follow the steps outlined in the "What has to be done to support a minor NetBox version?" section.

## What has to be done to support a NetBox App?

To support a NetBox App, carry out the same steps as in [this question](#what-has-to-be-done-to-support-a-minor-netbox-version).

## What has to be done to support a major Nautobot / NetBox App version?

Multiple major versions of the Nautobot or NetBox App can be supported within a single `nautobot-netbox-importer` major release. However, if an app introduces new models or fields that deviate from NetBox, then the steps described above should be followed.

## Why are `DiffSyncModel` classes generated dynamically?

`DiffSyncModel` classes are generated dynamically to efficiently support compatibility with various versions of NetBox and Nautobot, as well as Nautobot apps, using a single codebase. This method avoids the need for manually updating the code for each combination of NetBox/Nautobot versions and Nautobot apps, which would be complicated and time-consuming. Dynamic generation allows `DiffSyncModel` classes to adapt to the given data and the current Nautobot models, enabling us to maintain compatibility with minimal manual intervention.

Currently, verifying the versions of NetBox, Nautobot, or Nautobot apps is not necessary when generating `DiffSyncModel` classes. However, should the need arise, version checks can be implemented, and specific importers for particular fields based on version differences can be easily added.
