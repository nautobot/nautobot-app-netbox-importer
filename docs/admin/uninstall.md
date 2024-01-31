# Uninstall the App from Nautobot

Here you will find any steps necessary to cleanly remove the App from your Nautobot environment.

## Database Cleanup

There is no database cleanup necessary for this App.

## Remove App configuration

Remove the configuration you added in `nautobot_config.py` from `PLUGINS` & `PLUGINS_CONFIG`.

## Uninstall the package

```bash
$ pip3 uninstall nautobot-netbox-importer
```
