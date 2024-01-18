# Frequently Asked Questions

## What needs to be done to provide customization in the import process?

It's possible to customize the importer by registering a module containing a `setup` function. Such a function is called with a `NetBoxAdapter` instance as the first argument after the default setup is complete.

The function should be registered in your app's root `my_app/__init__.py` file, as follows:

```python
from nautobot_netbox_importer.utils import register_generator_setup

register_generator_setup("my_app.importer")
```

The function should be defined in the `my_app/importer.py` file as follows:

```python
"""Customize NetBox Importer setup."""

def setup(adapter):
    """Customize NetBox Importer setup."""
    adapter.configure_model(
        "my_netbox_app.my_model",
        nautobot_content_type="my_app.my_model",
        fields={
            "my_netbox_field": "my_nautobot_field",
        },
    )
```

`importer` can be replaced with any other name, but it has to be the same in both files.

Please consult the developer [FAQ](../dev/faq.md) for more details on how to define deviations from the default import process.
