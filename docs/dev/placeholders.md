# Placeholders

Placeholders are useful when it's not possible to use a single default reference, due to validation issues, but it's still necessary to create placeholder objects for the relationship. This is used e.g.: to create missing circuit terminations.

To allow creating placeholder objects for the model, you need to implement and register a custom function that fills the required fields for the placeholder. Then you can use the `import_placeholder` method to create a placeholder for the missing data.

Example of using this feature:

```python
def setup(adapter):
    # Define custom function to fill required fields for the placeholder
    def my_placeholder_filler(data: RecordData, suffix: str):
        """Fill required fields for a placeholder"""
        if "name" not in data:
            data["name"] = f"Placeholder-{suffix}"
        if "slug" not in data:
            data["slug"] = f"placeholder-{suffix.lower()}"
        data["status"] = "active"

    # Configure the referenced model to fill placeholder
    adapter.configure_model(
        "my_app.my_model",
        fill_placeholder=my_placeholder_filler
    )

    # Setup the referencing field importer
    def define_my_model_ref(field: SourceField):
        """Define the field importer."""

        def my_ref_importer(source: RecordData, target: DiffSyncBaseModel):
            value = field.get_source_value(source)

            if not value:
                # Cache the placeholder, provide unique suffix (ID of imported record) to generate unique Nautobot UUID
                # This creates a new placeholder object for empty `my_model_ref` field
                value = my_model.import_placeholder(source["id"])

            field.set_nautobot_value(target, value)
    
        # Register the field importer
        field.set_importer(my_ref_importer)

    # Configure the referencing model, to cache the placeholder, when missing
    adapter.configure_model(
        "my_app.my_another_model",
        fields={
            # This field references `my_app.my_model` model.
            # This is necessary when Nautobot requires unique values for the field, but the source data doesn't provide it.
            "my_model_ref": define_my_model_ref,
        },
    )
```

