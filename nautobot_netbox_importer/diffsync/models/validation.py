"""Validation helper class for nautobot-netbox-importer.

This file exists because both abstract.py and references.py need to use it.
"""
# pylint: disable=too-few-public-methods


class DiffSyncCustomValidationField:
    """Abstract base for a field with a custom validator."""

    @classmethod
    def __get_validators__(cls):
        """Get the Pydantic validator functions applicable to this class."""
        yield cls.validate

    @classmethod
    def validate(cls, value):
        """Stub."""
        raise NotImplementedError
