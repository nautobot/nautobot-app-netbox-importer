"""DiffSync adapters for nautobot-netbox-importer."""

from packaging import version

from .nautobot import NautobotDiffSync
from .netbox import NetBox210DiffSync

netbox_adapters = {
    version.parse("2.10.3"): NetBox210DiffSync,
    version.parse("2.10.4"): NetBox210DiffSync,
    version.parse("2.10.5"): NetBox210DiffSync,
}

__all__ = (
    "netbox_adapters",
    "NautobotDiffSync",
)
