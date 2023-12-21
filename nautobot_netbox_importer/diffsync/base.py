"""Generic DiffSync Importer base module."""

import datetime
import decimal
import logging
from enum import Enum
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
NautobotBaseModel = BaseModel
NautobotBaseModelType = Type[NautobotBaseModel]
DjangoField = _DjangoField
DjangoFieldDoesNotExist = _DjangoFieldDoesNotExist
GenericForeignValue = Tuple[ContentTypeStr, Uid]
NautobotField = Union[_DjangoField, GenericForeignKey]
DjangoModelMeta = _DjangoModelMeta
PydanticField = _PydanticField


class InternalFieldType(Enum):
    """Internal field types."""

    AUTO_FIELD = "AutoField"
    BIG_INTEGER_FIELD = "BigIntegerField"
    BINARY_FIELD = "BinaryField"
    BOOLEAN_FIELD = "BooleanField"
    CHAR_FIELD = "CharField"
    CUSTOM_FIELD_DATA = "CustomFieldData"
    DATE_FIELD = "DateField"
    DATE_TIME_FIELD = "DateTimeField"
    DECIMAL_FIELD = "DecimalField"
    DO_NOT_IMPORT_LAST_UPDATED = "DoNotImportLastUpdated"
    FOREIGN_KEY = "ForeignKey"
    FOREIGN_KEY_WITH_AUTO_RELATED_NAME = "ForeignKeyWithAutoRelatedName"
    GENERIC_FOREIGN_KEY = "GenericForeignKey"
    INTEGER_FIELD = "IntegerField"
    JSON_FIELD = "JSONField"
    MANY_TO_MANY_FIELD = "ManyToManyField"
    NOT_FOUND = "NotFound"
    ONE_TO_ONE_FIELD = "OneToOneField"
    POSITIVE_INTEGER_FIELD = "PositiveIntegerField"
    POSITIVE_SMALL_INTEGER_FIELD = "PositiveSmallIntegerField"
    PRIVATE_PROPERTY = "PrivateProperty"
    PROPERTY = "Property"
    READ_ONLY_PROPERTY = "ReadOnlyProperty"
    ROLE_FIELD = "RoleField"
    SLUG_FIELD = "SlugField"
    SMALL_INTEGER_FIELD = "SmallIntegerField"
    STATUS_FIELD = "StatusField"
    TEXT_FIELD = "TextField"
    TREE_NODE_FOREIGN_KEY = "TreeNodeForeignKey"
    UUID_FIELD = "UUIDField"


StrToInternalFieldType = {item.value: item for item in InternalFieldType.__members__.values()}

INTERNAL_TYPE_TO_ANNOTATION: Mapping[InternalFieldType, type] = {
    InternalFieldType.AUTO_FIELD: int,
    InternalFieldType.BIG_INTEGER_FIELD: int,
    InternalFieldType.BINARY_FIELD: bytes,
    InternalFieldType.BOOLEAN_FIELD: bool,
    InternalFieldType.CHAR_FIELD: str,
    InternalFieldType.CUSTOM_FIELD_DATA: Any,
    InternalFieldType.DATE_FIELD: datetime.date,
    InternalFieldType.DATE_TIME_FIELD: datetime.datetime,
    InternalFieldType.DECIMAL_FIELD: decimal.Decimal,
    InternalFieldType.INTEGER_FIELD: int,
    InternalFieldType.JSON_FIELD: Any,
    InternalFieldType.POSITIVE_INTEGER_FIELD: int,
    InternalFieldType.POSITIVE_SMALL_INTEGER_FIELD: int,
    InternalFieldType.PROPERTY: Any,
    InternalFieldType.SLUG_FIELD: str,
    InternalFieldType.SMALL_INTEGER_FIELD: int,
    InternalFieldType.TEXT_FIELD: str,
    InternalFieldType.UUID_FIELD: UUID,
}

INTEGER_INTERNAL_TYPES: Iterable[InternalFieldType] = (
    InternalFieldType.AUTO_FIELD,
    InternalFieldType.BIG_INTEGER_FIELD,
    InternalFieldType.INTEGER_FIELD,
    InternalFieldType.POSITIVE_INTEGER_FIELD,
    InternalFieldType.POSITIVE_SMALL_INTEGER_FIELD,
    InternalFieldType.SMALL_INTEGER_FIELD,
)

REFERENCE_INTERNAL_TYPES: Iterable[InternalFieldType] = (
    InternalFieldType.FOREIGN_KEY,
    InternalFieldType.FOREIGN_KEY_WITH_AUTO_RELATED_NAME,
    InternalFieldType.GENERIC_FOREIGN_KEY,
    InternalFieldType.MANY_TO_MANY_FIELD,
    InternalFieldType.ONE_TO_ONE_FIELD,
    InternalFieldType.ROLE_FIELD,
    InternalFieldType.STATUS_FIELD,
    InternalFieldType.TREE_NODE_FOREIGN_KEY,
)

DONT_IMPORT_TYPES: Iterable[InternalFieldType] = (
    InternalFieldType.DO_NOT_IMPORT_LAST_UPDATED,
    InternalFieldType.NOT_FOUND,
    InternalFieldType.PRIVATE_PROPERTY,
    InternalFieldType.READ_ONLY_PROPERTY,
)

EMPTY_VALUES = [None, set(), tuple(), {}, [], "", NOT_PROVIDED]


# pylint: disable=too-many-return-statements
def get_nautobot_field_and_type(
    model: NautobotBaseModelType,
    field_name: str,
) -> Tuple[Optional[NautobotField], InternalFieldType]:
    """Get Nautobot field and internal field type."""
    if field_name.startswith("_"):
        return None, InternalFieldType.PRIVATE_PROPERTY

    meta = model._meta  # type: ignore
    try:
        field = meta.get_field(field_name)
    except DjangoFieldDoesNotExist:
        if field_name == "custom_field_data":
            return meta.get_field("_custom_field_data"), InternalFieldType.CUSTOM_FIELD_DATA

        prop = getattr(model, field_name, None)
        if not prop:
            return None, InternalFieldType.NOT_FOUND
        if isinstance(prop, property) and not prop.fset:
            return None, InternalFieldType.READ_ONLY_PROPERTY
        return None, InternalFieldType.PROPERTY

    if field_name == "last_updated":
        return field, InternalFieldType.DO_NOT_IMPORT_LAST_UPDATED

    if isinstance(field, GenericForeignKey):
        # GenericForeignKey is not a real field, doesn't have `get_internal_type` method
        return field, InternalFieldType.GENERIC_FOREIGN_KEY

    try:
        return field, StrToInternalFieldType[field.get_internal_type()]
    except KeyError as error:
        raise NotImplementedError(f"Unsupported field type {meta.app_label}.{meta.model_name}.{field_name}") from error


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
