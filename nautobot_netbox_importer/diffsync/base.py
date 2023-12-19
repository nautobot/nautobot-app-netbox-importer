"""Generic DiffSync Importer base module."""

import datetime
import decimal
import logging
from typing import Any
from typing import Iterable
from typing import List
from typing import Mapping
from typing import MutableMapping
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union
from uuid import NAMESPACE_DNS
from uuid import UUID
from uuid import uuid5

from dateutil import parser as datetime_parser
from diffsync import DiffSync
from diffsync.store.local import LocalStore
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import FieldDoesNotExist as _DjangoFieldDoesNotExist
from django.db.models import Field as _DjangoField
from django.db.models.fields import NOT_PROVIDED
from django.db.models.options import Options as _DjangoModelMeta
from nautobot.core.models import BaseModel
from pydantic import Field as _PydanticField

logger = logging.getLogger("nautobot-netbox-importer")

Uid = Union[str, int, UUID]
ContentTypeStr = str
ContentTypeValue = Union[int, ContentTypeStr, List, Tuple[str, str]]
FieldName = str
RecordData = MutableMapping[FieldName, Any]
InternalFieldTypeStr = str
NautobotBaseModel = BaseModel
NautobotBaseModelType = Type[NautobotBaseModel]
DjangoField = _DjangoField
DjangoFieldDoesNotExist = _DjangoFieldDoesNotExist
GenericForeignValue = Tuple[ContentTypeStr, Uid]
NautobotField = Union[_DjangoField, GenericForeignKey]
DjangoModelMeta = _DjangoModelMeta
PydanticField = _PydanticField

EMPTY_VALUES = [None, set(), tuple(), {}, [], "", NOT_PROVIDED]
INTERNAL_TYPE_TO_ANNOTATION: Mapping[InternalFieldTypeStr, type] = {
    "AutoField": int,
    "BigIntegerField": int,
    "BinaryField": str,
    "BooleanField": bool,
    "CharField": str,
    "CustomFieldData": Any,
    "DateField": datetime.date,
    "DateTimeField": datetime.datetime,
    "DecimalField": decimal.Decimal,
    "IntegerField": int,
    "JSONField": Any,
    "PositiveIntegerField": int,
    "PositiveSmallIntegerField": int,
    "Property": Any,
    "SlugField": str,
    "SmallIntegerField": int,
    "TextField": str,
    "UUIDField": UUID,
}
INTEGER_INTERNAL_TYPES: Iterable[InternalFieldTypeStr] = (
    "AutoField",
    "BigIntegerField",
    "IntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "SmallIntegerField",
)
REFERENCE_INTERNAL_TYPES: Iterable[InternalFieldTypeStr] = (
    "ForeignKey",
    "ForeignKeyWithAutoRelatedName",
    "GenericForeignKey",
    "ManyToManyField",
    "OneToOneField",
    "RoleField",
    "StatusField",
    "TreeNodeForeignKey",
)


def source_pk_to_uuid(content_type: ContentTypeStr, pk: Uid) -> UUID:
    """Deterministically map source primary key to a UUID primary key.

    One of the reasons Nautobot moved from sequential integers to UUIDs was to protect the application
    against key-enumeration attacks, so we don't use a hard-coded mapping from integer to UUID as that
    would defeat the purpose.
    """
    if isinstance(pk, UUID):
        return pk

    if isinstance(pk, int):
        pk = str(pk)

    if not pk or not isinstance(pk, str):
        raise ValueError(f"Invalid primary key {pk}")

    namespace = uuid5(
        NAMESPACE_DNS,  # not really but nothing actually enforces this
        settings.SECRET_KEY,
    )
    return uuid5(namespace, f"{content_type}:{pk}")


def normalize_datetime(value: Any) -> Optional[datetime.datetime]:
    """Normalize datetime values to UTC to compare with DiffSync."""
    if not value:
        return None

    if not isinstance(value, datetime.datetime):
        value = datetime_parser.isoparse(str(value))

    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)

    return value.astimezone(datetime.timezone.utc)


class BaseAdapter(DiffSync):
    """Base class for NetBox adapters."""

    def __init__(self, *args, **kwargs):
        """Initialize the adapter."""
        super().__init__(*args, **kwargs)

        self.cleanup()

    def cleanup(self):
        """Clean up the adapter."""
        # TBD: Should be fixed in DiffSync.
        # This is a work around to allow testing multiple imports in a single test run.
        self.top_level.clear()
        if isinstance(self.store, LocalStore):
            # pylint: disable=protected-access
            self.store._data.clear()
