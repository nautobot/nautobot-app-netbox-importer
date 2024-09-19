"""Utility functions and classes for nautobot_netbox_importer."""

from typing import Any, Generator, Iterable, Tuple


def get_field_choices(items: Iterable) -> Generator[Tuple[Any, Any], None, None]:
    """Yield all choices from a model field, flattening nested iterables."""
    for key, value in items:
        if isinstance(value, (list, tuple)):
            yield from get_field_choices(value)
        else:
            yield key, value
