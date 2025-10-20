# Import Order

The import order is the order in which the content types are imported into Nautobot. The import order is important because some content types depend on others. For example, if you are importing devices and their associated interfaces, you need to import the devices first before importing the interfaces.

As Nautobot references are not a tree but a cyclic graph, it's not possible to determine an always working import order. Instead, the import order can be updated when `FirstSaveFailed` or `SaveFailed` issues are encountered.

Models listed in `IMPORT_ORDER` take precedence over models defined using `configure_model`.

`IMPORT ORDER` constant is defined in [nautobot.py file](https://github.com/nautobot/nautobot-app-netbox-importer/blob/develop/nautobot_netbox_importer/generator/nautobot.py).
