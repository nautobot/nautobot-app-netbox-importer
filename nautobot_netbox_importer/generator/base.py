"""Generic DiffSync Importer base module."""

import datetime
import decimal
from enum import Enum
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Type
from uuid import UUID
from uuid import uuid5

from dateutil import parser as datetime_parser
from diffsync import DiffSync
from diffsync.store.local import LocalStore
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist as DjangoFieldDoesNotExist
from django.db.models import Field as DjangoField
from django.db.models.fields import NOT_PROVIDED
from django.db.models.options import Options as _DjangoModelMeta
from nautobot.core.models import BaseModel
from pydantic import Field as _PydanticField

from nautobot_netbox_importer.base import ContentTypeStr
from nautobot_netbox_importer.base import Uid

NautobotBaseModel = BaseModel
NautobotBaseModelType = Type[NautobotBaseModel]
DjangoModelMeta = _DjangoModelMeta
PydanticField = _PydanticField


class InternalFieldType(Enum):
    """Internal field types."""

    AUTO_FIELD = "AutoField"
    BIG_AUTO_FIELD = "BigAutoField"
    BIG_INTEGER_FIELD = "BigIntegerField"
    BINARY_FIELD = "BinaryField"
    BOOLEAN_FIELD = "BooleanField"
    CHAR_FIELD = "CharField"
    CUSTOM_FIELD_DATA = "CustomFieldData"
    DATE_FIELD = "DateField"
    DATE_TIME_FIELD = "DateTimeField"
    DECIMAL_FIELD = "DecimalField"
    FOREIGN_KEY = "ForeignKey"
    FOREIGN_KEY_WITH_AUTO_RELATED_NAME = "ForeignKeyWithAutoRelatedName"
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
    InternalFieldType.BIG_AUTO_FIELD: int,
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

# Fields to auto add to source and target wrappers
AUTO_ADD_FIELDS = (
    "content_types",
    "status",
)

EMPTY_VALUES = (
    "",
    NOT_PROVIDED,
    None,
    [],
    dict,  # CustomFieldData field has `dict` class as the default value
    set(),
    tuple(),
    {},
)


def get_nautobot_field_and_type(
    model: NautobotBaseModelType,
    field_name: str,
) -> Tuple[Optional[DjangoField], InternalFieldType]:
    """Get Nautobot field and internal field type."""
    if field_name.startswith("_"):
        return None, InternalFieldType.PRIVATE_PROPERTY

    meta = model._meta  # type: ignore
    if field_name == "custom_field_data":
        field_name = "_custom_field_data"
    try:
        field = meta.get_field(field_name)
    except DjangoFieldDoesNotExist:
        prop = getattr(model, field_name, None)
        if not prop:
            return None, InternalFieldType.NOT_FOUND
        if isinstance(prop, property) and not prop.fset:
            return None, InternalFieldType.READ_ONLY_PROPERTY
        return None, InternalFieldType.PROPERTY

    if field_name == "_custom_field_data":
        return field, InternalFieldType.CUSTOM_FIELD_DATA

    try:
        return field, StrToInternalFieldType[field.get_internal_type()]
    except KeyError as error:
        raise NotImplementedError(f"Unsupported field type {meta.app_label}.{meta.model_name}.{field_name}") from error


def source_pk_to_uuid(
    content_type: ContentTypeStr,
    pk: Uid,
    # Namespace is defined as random constant UUID combined with settings.SECRET_KEY
    namespace=uuid5(UUID("33c07af8-e425-43b2-b8d0-52289dfe7cf2"), settings.SECRET_KEY),
) -> UUID:
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
    """Base class for Generator Adapters."""

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
