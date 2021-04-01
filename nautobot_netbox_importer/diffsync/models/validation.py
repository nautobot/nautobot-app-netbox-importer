"""Validation helper class for nautobot-netbox-importer.

This file exists because both abstract.py and references.py need to use it.
"""
# pylint: disable=too-few-public-methods

import uuid

from django.conf import settings


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


def netbox_pk_to_nautobot_pk(modelname, pk):
    """Deterministically map a NetBox integer primary key to a Nautobot UUID primary key.

    One of the reasons Nautobot moved from sequential integers to UUIDs was to protect the application
    against key-enumeration attacks, so we don't use a hard-coded mapping from integer to UUID as that
    would defeat the purpose.
    """
    assert isinstance(pk, int)
    namespace = uuid.uuid5(
        uuid.NAMESPACE_DNS,  # not really but nothing actually enforces this
        settings.SECRET_KEY
    )
    return uuid.uuid5(namespace, f"{modelname}:{pk}")
