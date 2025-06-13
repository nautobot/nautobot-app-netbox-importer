"""Base types for the Nautobot Importer."""

import logging
from os import PathLike
from typing import Any, Callable, List, MutableMapping, Tuple, Union
from uuid import UUID

logger = logging.getLogger("nautobot-netbox-importer")

Uid = Union[str, int, UUID]
ContentTypeStr = str
ContentTypeValue = Union[int, ContentTypeStr, List, Tuple[str, str]]
FieldName = str
RecordData = MutableMapping[FieldName, Any]
GenericForeignValue = Tuple[ContentTypeStr, Uid]
Pathable = Union[str, PathLike]
FillPlaceholder = Callable[[RecordData, str], None]
NullablePrimitives = Union[str, int, float, bool, None]

PLACEHOLDER_UID = "placeholder"
GENERATOR_SETUP_MODULES: List[str] = []
NOTHING = object()


def register_generator_setup(module: str) -> None:
    """Register adapter setup function.

    This function must be called before the adapter is used and containing module can't import anything from Nautobot.
    """
    if module not in GENERATOR_SETUP_MODULES:
        GENERATOR_SETUP_MODULES.append(module)
