# Customizing the NetBox Importer

This document explains how to define own customizations the NetBox Importer to fit your specific needs.

For more examples and details, check the following resources:

- The developer [FAQ](../dev/faq.md).
- [Files in `nautobot_netbox_importer/diffsync/models` directory](https://github.com/nautobot/nautobot-app-netbox-importer/tree/develop/nautobot_netbox_importer/diffsync/models).

## Basic Principles

The NetBox Importer is designed to be extensible. The core component, [generator](../dev/generator.md), creates the DiffSync and Importer classes needed to import data based on input data and Nautobot's structure.

NetBox specific mappings are defined in the [`diffsync` directory](https://github.com/nautobot/nautobot-app-netbox-importer/tree/develop/nautobot_netbox_importer/diffsync).

To customize the importer, you need to:

1. Create a Python file with your customizations
2. Register the file to be importable by the NetBox Importer
3. Call the `setup()` function from your customization file

## Example Customization

Here's how to create a simple customization using the Docker Compose development environment:

First, create the package structure:

```bash
mkdir -p netbox-customization
mkdir -p netbox-customization/netbox_customization
touch netbox-customization/netbox_customization/__init__.py
```

Create the package configuration file `netbox-customization/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "netbox-customization"
version = "0.1.0"
description = "Custom extensions for NetBox Importer"
requires-python = ">=3.9"

[tool.setuptools]
packages = ["netbox_customization"]
```

Create your customization file `netbox-customization/netbox_customization/customization.py`:

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

The customization file must contain a `setup` function that accepts a `NetBoxAdapter` instance.

Install the package in the development container:

```bash
invoke start
invoke exec "pip install -e ./netbox-customization"
```

!!! Warning
    This installs the package in the running container only. Changes will be lost when the container stops. For permanent changes, add the package to the project's `pyproject.toml` or update the `Dockerfile`.

Finally, use your customization when importing data:

```bash
invoke import-netbox \
    --customizations=netbox_customization.customization \
    <other importer options>
```

There are the following alternatives to the command above:

- Use the `--customizations` option with the `nautobot-server import_netbox` command:

    ```bash
    nautobot-server import_netbox \
        --customizations=netbox_customization.customization \
        <other importer options>
    ```

    !!! Note
        `invoke import-netbox` is the Docker Compose based wrapper for the `nautobot-server import_netbox` command.

- Register the customization file directly:

    ```python
    from nautobot_netbox_importer.base import register_generator_setup

    register_generator_setup("netbox_customization.customization")
    ```
