# Primary Keys

Each Nautobot instance primary key is deterministically generated using UUID5, based on the source content type and primary key.

!!! Note
    If the source primary key is already a UUID, it is passed through without change.

To generate the UUID, the `source_pk_to_uuid()` function is used. It takes two arguments: the source content type and the source primary key. Internally, it uses `settings.SECRET_KEY` to define the UUIDv5 namespace. Since the secret key is the same, it's possible to repeat the import process generating the same UUIDs.

It's possible to customize the primary key generation for particular source model.

This feature is used to deduplicate IP addresses and prefixes, as Nautobot has a strict database constraint for duplicates, but NetBox allows it. As a solution, Nautobot's IP address primary key is derived from the IP address value instead of the ID. Then duplicate source IP addresses are merged into a single Nautobot IP address.

An example how to derive Nautobot UUID from the field `name` instead of ID:

```python
from nautobot_netbox_importer.generator.base import source_pk_to_uuid

def my_setup(adapter: SourceAdapter) -> None:
    """Customize the mapping from source to Nautobot"""

    # Function accepts the source data and returns the Nautobot primary key
    def get_pk_from_name(source: RecordData) -> Uid:
        """Generate Nautobot primary key from name."""
        # Get the name field value from the source data
        name = name_field.get_source_value(source)
        if not name:
            raise ValueError("Missing name for the record")

        # Generate the UUID5 using the source content type and name
        return source_pk_to_uuid(model_wrapper.content_type, name)

    # Configure the model with the custom primary key generation
    model_wrapper = configure_model(
        "my_app.my_model",
        get_pk_from_data=get_pk_from_name,  # Customize the primary key generation
        fields={
            "name": "",  # Specify the `name` field
        },
    )

    # Get the name field source reference
    name_field = model_wrapper.fields["name"]
```

Once the primary key is generated, it's cached, see more in [Caching](./caching.md#source-identifiers-to-nautobot-primary-keys-mapping).

{%
    include-markdown '../diagrams/generate_primary_key.md'
    heading-offset=1
%}
