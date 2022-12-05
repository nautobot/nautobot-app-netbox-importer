# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.


## Prerequisites

- The plugin is compatible with Nautobot 1.0.0b3 and later and can handle JSON data exported from NetBox 2.10.3 thru 2.10.8  at present. 

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix and the deprecation policy.


## Install Guide

!!! note
    Plugins can be installed manually or using Python's `pip`. See the [nautobot documentation](https://docs.nautobot.com/projects/core/en/stable/plugins/#install-the-package) for more details. The pip package name for this plugin is [`nautobot-netbox-importer`](https://pypi.org/project/nautobot-netbox-importer/).

The plugin is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install nautobot-netbox-importer
```

To ensure Nautobot NetBox Importer is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot-netbox-importer` package:

```shell
echo nautobot-netbox-importer >> local_requirements.txt
```

Once installed, the plugin needs to be enabled in your Nautobot configuration. The following block of code below shows the additional configuration required to be added to your `nautobot_config.py` file:

- Append `"nautobot_netbox_importer"` to the `PLUGINS` list.
- Append the `"nautobot_netbox_importer"` dictionary to the `PLUGINS_CONFIG` dictionary and override any defaults.

```python
# In your nautobot_config.py
PLUGINS = ["nautobot_netbox_importer"]
```

Once the Nautobot configuration is updated, run the Post Upgrade command (`nautobot-server post_upgrade`) to run migrations and clear any cache:

```shell
nautobot-server post_upgrade
```

Then restart (if necessary) the Nautobot services which may include:

- Nautobot
- Nautobot Workers
- Nautobot Scheduler

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```
