"""Generic DiffSync Importer base module."""

import datetime
import decimal
import logging
from typing import Any
from typing import Iterable
from typing import List
from typing import Mapping
from typing import MutableMapping
from typing import Tuple
from typing import Type
from typing import Union
from uuid import NAMESPACE_DNS
from uuid import UUID
from uuid import uuid5

from diffsync import DiffSync
from diffsync.store.local import LocalStore
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Field as DjangoField
from django.db.models.fields import NOT_PROVIDED
from nautobot.core.models import BaseModel
from nautobot.core.utils.lookup import get_model_from_name

logger = logging.getLogger("nautobot-netbox-importer")

Uid = Union[str, int, UUID]
ContentTypeStr = str
ContentTypeValue = Union[int, ContentTypeStr, List, Tuple[str, str]]
FieldName = str
RecordData = MutableMapping[FieldName, Any]
InternalFieldTypeStr = str
NautobotBaseModel = BaseModel
NautobotBaseModelType = Type[NautobotBaseModel]

EMPTY_VALUES = [None, set(), tuple(), {}, [], "", NOT_PROVIDED]
ONLY_ID_IDENTIFIERS: List[FieldName] = ["id"]
INTERNAL_TYPE_TO_ANNOTATION: Mapping[InternalFieldTypeStr, type] = {
    "Any": Any,
    "AutoField": int,
    "BigIntegerField": int,
    "BinaryField": str,
    "BooleanField": bool,
    "CharField": str,
    "CustomFieldData": Any,
    "DateField": datetime.date,
    "DateTimeField": datetime.datetime,
    "DecimalField": decimal.Decimal,
    "Int": int,
    "IntegerField": int,
    "JSONField": Any,
    "PositiveIntegerField": int,
    "PositiveSmallIntegerField": int,
    "SlugField": str,
    "SmallIntegerField": int,
    "TextField": str,
    "UUIDField": UUID,
}
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


def get_content_type_id(content_type: ContentTypeValue) -> int:
    """Get the Django content type ID for a given content type."""
    if isinstance(content_type, int):
        return content_type

    if not isinstance(content_type, str):
        content_type = ".".join(content_type)

    instance = ContentType.objects.get_for_model(get_model_from_name(content_type))
    return instance.id


def get_internal_field_type(field: DjangoField) -> InternalFieldTypeStr:
    """Get the internal field type for a Django field."""
    if isinstance(field, GenericForeignKey):
        return "GenericForeignKey"

    if hasattr(field, "get_internal_type"):
        return field.get_internal_type()

    raise NotImplementedError(f"Unsupported field type {field}")


class BaseDiffSync(DiffSync):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TBD: Should be fixed in DiffSync.
        # This is a work around to allow testing multiple imports in a single test run.
        self.top_level.clear()
        if isinstance(self.store, LocalStore):
            self.store._data.clear()
