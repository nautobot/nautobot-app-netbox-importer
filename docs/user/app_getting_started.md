# Getting Started with the App

This document provides a step-by-step tutorial on how to get the App going and how to use it.

## Install the App

To install the App, please follow the detailed instructions in the [Installation Guide](../admin/install.md).

## First steps with the App

This app adds no new features to the Nautobot UI or API but adds a new management CLI command to import data from NetBox.

Once the app is installed, you will see a new command available under the `nautobot_netbox_importer` subsection of the `nautobot-server help` command:

```bash
$ nautobot-server help

...
[nautobot_netbox_importer]
    import_netbox
...
```

## What are the next steps?

Next, it's time to pull information from the original NetBox database and convert it into JSON format for import into Nautobot.

You can check out the [Use Cases](app_use_cases.md) section for more examples.
