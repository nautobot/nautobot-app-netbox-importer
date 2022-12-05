# Getting Started with the App

This document provides a step-by-step tutorial on how to get the App going and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md).

## First steps with the App

This plugin is not adding any new feature in the Nautobot UI or API but two new commands, one for importing data records into Nautobot and one for importing the database changelog into Nautobot as an optional secondary step.

One the plugin is installed you will see both new commands available under `nautobot_netbox_importer` subsection of the `nautobot-server help` command:

```bash
$ nautobot-server help
[nautobot_netbox_importer]
    import_netbox_json
    import_netbox_objectchange_json
```

## What are the next steps?

Next, it's time to pull information from the original Netbox database, and convert into JSON format to import into Nautobot.
