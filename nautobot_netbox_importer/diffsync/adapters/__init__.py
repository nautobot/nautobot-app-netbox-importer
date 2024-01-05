"""Adapter classes for loading DiffSyncModels with data from NetBox or Nautobot."""

from .nautobot import NautobotAdapter
from .netbox import NetBoxAdapter
from .netbox import NetBoxImporterOptions

__all__ = (
    "NautobotAdapter",
    "NetBoxAdapter",
    "NetBoxImporterOptions",
)
