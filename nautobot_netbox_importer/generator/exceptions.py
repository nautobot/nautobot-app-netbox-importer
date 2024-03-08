"""Custom exceptions for the NetBox Importer."""


class NetBoxImporterException(Exception):
    """Base exception for the netbox_importer package."""


class NautobotModelNotFound(NetBoxImporterException):
    """Raised when a Nautobot model cannot be found."""
