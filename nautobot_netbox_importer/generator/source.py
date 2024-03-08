# pylint: disable=too-many-lines
"""Generic DiffSync Source Generator."""

import datetime
import json
from enum import Enum
from enum import auto
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import List
from typing import Mapping
from typing import NamedTuple
from typing import Optional
from typing import OrderedDict
from typing import Set
from typing import Tuple
from typing import Union
from uuid import UUID

from diffsync import DiffSyncModel
from diffsync.enum import DiffSyncModelFlags
from nautobot.core.models.tree_queries import TreeModel

from nautobot_netbox_importer.base import NOTHING
from nautobot_netbox_importer.base import ContentTypeStr
from nautobot_netbox_importer.base import ContentTypeValue
from nautobot_netbox_importer.base import FieldName
from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.base import Uid
from nautobot_netbox_importer.base import logger as default_logger
from nautobot_netbox_importer.summary import DiffSyncSummary
from nautobot_netbox_importer.summary import FieldSummary
from nautobot_netbox_importer.summary import ImportSummary
from nautobot_netbox_importer.summary import SourceModelStats
from nautobot_netbox_importer.summary import SourceModelSummary
from nautobot_netbox_importer.summary import serialize_to_summary

from .base import AUTO_ADD_FIELDS
from .base import EMPTY_VALUES
from .base import BaseAdapter
from .base import DjangoField
from .base import InternalFieldType
from .base import NautobotBaseModel
from .base import NautobotBaseModelType
from .base import normalize_datetime
from .base import source_pk_to_uuid
from .exceptions import NautobotModelNotFound
from .exceptions import NetBoxImporterException
from .nautobot import IMPORT_ORDER
from .nautobot import DiffSyncBaseModel
from .nautobot import NautobotAdapter
from .nautobot import NautobotField
from .nautobot import NautobotModelWrapper


class SourceFieldImporterIssue(NetBoxImporterException):
    """Raised when an error occurs during field import.

    Raising this exception gathers the issue and continues with the next importer.
    """

    def __init__(self, message: str, field: "SourceField"):
        """Initialize the exception."""
        super().__init__(message)
        self.field = field


class InvalidChoiceValueIssue(SourceFieldImporterIssue):
    """Raised when an invalid choice value is encountered."""

    def __init__(self, field: "SourceField", value: Any, replacement: Any = NOTHING):
        """Initialize the exception."""
        message = f"Invalid choice value: `{value}`"
        if replacement is not NOTHING:
            message += f", replaced with `{replacement}`"
        super().__init__(message, field)


class SourceRecord(NamedTuple):
    """Source Data Item."""

    content_type: ContentTypeStr
    data: RecordData


class ImporterPass(Enum):
    """Importer Pass."""

    DEFINE_STRUCTURE = 1
    IMPORT_DATA = 2


class PreImportResult(Enum):
    """Pre Import Response."""

    SKIP_RECORD = False
    USE_RECORD = True


class SourceFieldSource(Enum):
    """Defines the source of the SourceField."""

    AUTO = auto()  # Automatically added fields like primary keys and AUTO_ADD_FIELDS
    CACHE = auto()  # Fields added by caching data during customization
    DATA = auto()  # Fields added from input data
    CUSTOM = auto()  # Fields added by customizing the importer
    SIBLING = auto()  # Fields defined as siblings of other fields, imported by other field importer
    IDENTIFIER = auto()  # Fields used as identifiers


PreImport = Callable[[RecordData, ImporterPass], PreImportResult]
SourceDataGenerator = Callable[[], Iterable[SourceRecord]]
SourceFieldImporter = Callable[[RecordData, DiffSyncBaseModel], None]
SourceFieldImporterFallback = Callable[["SourceField", RecordData, DiffSyncBaseModel, Exception], None]
SourceFieldImporterFactory = Callable[["SourceField"], None]
SourceFieldDefinition = Union[
    None,  # Ignore field
    FieldName,  # Rename field
    SourceFieldImporterFactory,  # Field importer factory
]


SourceReferences = Dict[Uid, Set["SourceModelWrapper"]]
ForwardReferences = Callable[["SourceModelWrapper", SourceReferences], None]
SourceContentType = Union[ContentTypeValue, "SourceModelWrapper", NautobotModelWrapper, NautobotBaseModelType]


class SourceAdapter(BaseAdapter):
    """Source DiffSync Adapter."""

    def __init__(
        self,
        get_source_data: SourceDataGenerator,
        *args,
        nautobot: Optional[NautobotAdapter] = None,
        logger=None,
        **kwargs,
    ):
        """Initialize the SourceAdapter."""
        super().__init__(*args, **kwargs)

        self.get_source_data = get_source_data
        self.wrappers: OrderedDict[ContentTypeStr, SourceModelWrapper] = OrderedDict()
        self.nautobot = nautobot or NautobotAdapter()
        self.content_type_ids_mapping: Dict[int, SourceModelWrapper] = {}
        self.logger = logger or default_logger
        self.summary = ImportSummary()

        # From Nautobot to Source content type mapping
        # When multiple source content types are mapped to the single nautobot content type, mapping is set to `None`
        self._content_types_back_mapping: Dict[ContentTypeStr, Optional[ContentTypeStr]] = {}

    # pylint: disable=too-many-arguments,too-many-branches,too-many-locals
    def configure_model(
        self,
        content_type: ContentTypeStr,
        nautobot_content_type: ContentTypeStr = "",
        extend_content_type: ContentTypeStr = "",
        identifiers: Optional[Iterable[FieldName]] = None,
        fields: Optional[Mapping[FieldName, SourceFieldDefinition]] = None,
        default_reference: Optional[RecordData] = None,
        flags: Optional[DiffSyncModelFlags] = None,
        nautobot_flags: Optional[DiffSyncModelFlags] = None,
        pre_import: Optional[PreImport] = None,
        disable_related_reference: Optional[bool] = None,
        forward_references: Optional[ForwardReferences] = None,
    ) -> "SourceModelWrapper":
        """Create if not exist and configure a wrapper for a given source content type.

        Create Nautobot content type wrapper as well.
        """
        content_type = content_type.lower()
        nautobot_content_type = nautobot_content_type.lower()
        extend_content_type = extend_content_type.lower()

        if extend_content_type:
            if nautobot_content_type:
                raise ValueError(f"Can't specify both nautobot_content_type and extend_content_type {content_type}")
            extends_wrapper = self.wrappers[extend_content_type]
            nautobot_content_type = extends_wrapper.nautobot.content_type
        else:
            extends_wrapper = None

        if content_type in self.wrappers:
            wrapper = self.wrappers[content_type]
            if nautobot_content_type and wrapper.nautobot.content_type != nautobot_content_type:
                raise ValueError(
                    f"Content type {content_type} already mapped to {wrapper.nautobot.content_type} "
                    f"can't map to {nautobot_content_type}"
                )
        else:
            nautobot_wrapper = self.nautobot.get_or_create_wrapper(nautobot_content_type or content_type)
            wrapper = SourceModelWrapper(self, content_type, nautobot_wrapper)
            if not extends_wrapper:
                if nautobot_wrapper.content_type in self._content_types_back_mapping:
                    if self._content_types_back_mapping[nautobot_wrapper.content_type] != content_type:
                        self._content_types_back_mapping[nautobot_wrapper.content_type] = None
                else:
                    self._content_types_back_mapping[nautobot_wrapper.content_type] = content_type

        if extends_wrapper:
            wrapper.extends_wrapper = extends_wrapper

        if identifiers:
            wrapper.set_identifiers(identifiers)
        for field_name, definition in (fields or {}).items():
            wrapper.add_field(field_name, SourceFieldSource.CUSTOM).set_definition(definition)
        if default_reference:
            wrapper.set_default_reference(default_reference)
        if flags is not None:
            wrapper.flags = flags
        if nautobot_flags is not None:
            wrapper.nautobot.flags = nautobot_flags
        if pre_import:
            wrapper.pre_import = pre_import
        if disable_related_reference is not None:
            wrapper.disable_related_reference = disable_related_reference
        if forward_references:
            wrapper.forward_references = forward_references

        return wrapper

    def disable_model(self, content_type: ContentTypeStr, disable_reason: str) -> None:
        """Disable model importing."""
        self.get_or_create_wrapper(content_type).disable_reason = disable_reason

    def summarize(self, diffsync_summary: DiffSyncSummary) -> None:
        """Summarize the import."""
        self.summary.diffsync = diffsync_summary

        wrapper_to_id = {value: key for key, value in self.content_type_ids_mapping.items()}

        for content_type in sorted(self.wrappers):
            wrapper = self.wrappers.get(content_type)
            if wrapper:
                self.summary.source.append(wrapper.get_summary(wrapper_to_id.get(wrapper, None)))

        for content_type in sorted(self.nautobot.wrappers):
            wrapper = self.nautobot.wrappers.get(content_type)
            if wrapper:
                self.summary.nautobot.append(wrapper.get_summary())

    def get_or_create_wrapper(self, value: Union[None, SourceContentType]) -> "SourceModelWrapper":
        """Get a source Wrapper for a given content type."""
        # Enable mapping back from Nautobot content type, when using Nautobot model or wrapper
        map_back = False

        if not value:
            raise ValueError("Missing value")

        if isinstance(value, SourceModelWrapper):
            return value

        if isinstance(value, type(NautobotBaseModel)):
            map_back = True
            value = value._meta.label.lower()  # type: ignore
        elif isinstance(value, NautobotModelWrapper):
            map_back = True
            value = value.content_type

        if isinstance(value, str):
            value = value.lower()
        elif isinstance(value, int):
            if value not in self.content_type_ids_mapping:
                raise ValueError(f"Content type not found {value}")
            return self.content_type_ids_mapping[value]
        elif isinstance(value, Iterable) and len(value) == 2:
            value = ".".join(value).lower()
        else:
            raise ValueError(f"Invalid content type {value}")

        if map_back and value in self._content_types_back_mapping:
            back_mapping = self._content_types_back_mapping.get(value, None)
            if not back_mapping:
                raise ValueError(f"Ambiguous content type back mapping {value}")
            value = back_mapping

        if value in self.wrappers:
            return self.wrappers[value]

        return self.configure_model(value)

    def get_nautobot_content_type_uid(self, content_type: ContentTypeValue) -> int:
        """Get the Django content type ID for a given content type."""
        if isinstance(content_type, int):
            wrapper = self.content_type_ids_mapping.get(content_type, None)
            if not wrapper:
                raise ValueError(f"Content type not found {content_type}")
            return wrapper.nautobot.content_type_instance.pk
        if not isinstance(content_type, str):
            if not len(content_type) == 2:
                raise ValueError(f"Invalid content type {content_type}")
            content_type = ".".join(content_type)

        wrapper = self.get_or_create_wrapper(content_type)

        return wrapper.nautobot.content_type_instance.pk

    def load(self) -> None:
        """Load data from the source."""
        self.import_data()
        self.post_import()

    def import_data(self) -> None:
        """Import data from the source."""
        get_source_data = self.get_source_data

        # First pass to enhance pre-defined wrappers structure
        for content_type, data in get_source_data():
            if content_type in self.wrappers:
                wrapper = self.wrappers[content_type]
            else:
                wrapper = self.configure_model(content_type)
            wrapper.first_pass(data)

        # Create importers, wrappers structure is updated as needed
        while True:
            wrappers = [
                wrapper
                for wrapper in self.wrappers.values()
                if wrapper.importers is None and not wrapper.disable_reason
            ]
            if not wrappers:
                break
            for wrapper in wrappers:
                wrapper.create_importers()

        # Second pass to import actual data
        for content_type, data in get_source_data():
            self.wrappers[content_type].second_pass(data)

    def post_import(self) -> None:
        """Post import processing."""
        while any(wrapper.post_import() for wrapper in self.wrappers.values()):
            pass

        for nautobot_wrapper in self.get_imported_nautobot_wrappers():
            diffsync_class = nautobot_wrapper.diffsync_class
            # pylint: disable=protected-access
            model_name = diffsync_class._modelname
            self.top_level.append(model_name)
            setattr(self, model_name, diffsync_class)
            setattr(self.nautobot, model_name, getattr(self, model_name))

    def get_imported_nautobot_wrappers(self) -> Generator[NautobotModelWrapper, None, None]:
        """Get a list of Nautobot model wrappers in the order of import."""
        result = OrderedDict()

        for wrapper in self.wrappers.values():
            if (
                wrapper
                and not wrapper.disable_reason
                and wrapper.stats.created > 0
                and wrapper.nautobot.content_type not in result
            ):
                result[wrapper.nautobot.content_type] = wrapper.nautobot

        for content_type in IMPORT_ORDER:
            if content_type in result:
                yield result[content_type]
                del result[content_type]

        yield from result.values()


# pylint: disable=too-many-instance-attributes
class SourceModelWrapper:
    """Definition of a source model mapping to Nautobot model."""

    def __init__(self, adapter: SourceAdapter, content_type: ContentTypeStr, nautobot_wrapper: NautobotModelWrapper):
        """Initialize the SourceModelWrapper."""
        if content_type in adapter.wrappers:
            raise ValueError(f"Duplicate content type {content_type}")
        adapter.wrappers[content_type] = self
        self.adapter = adapter
        self.content_type = content_type
        self.nautobot = nautobot_wrapper
        if self.nautobot.disabled:
            self.disable_reason = f"Nautobot content type: `{nautobot_wrapper.content_type}` not found"
        else:
            self.disable_reason = ""

        # Source field names when referencing this model
        self.identifiers: Optional[List[FieldName]] = None

        # Used to autofill `content_types` field
        self.disable_related_reference = False
        self.references: SourceReferences = {}
        self.forward_references: Optional[ForwardReferences] = None

        # Whether importing record data exteds existing record
        self.extends_wrapper: Optional[SourceModelWrapper] = None

        # Importers are created after all fields are defined
        self.importers: Optional[Set[SourceFieldImporter]] = None

        # Default reference to this model
        self.default_reference_uid: Optional[Uid] = None

        # Caching
        self._uid_to_pk_cache: Dict[Uid, Uid] = {}
        self._cached_data: Dict[Uid, RecordData] = {}

        self.stats = SourceModelStats()
        self.flags = DiffSyncModelFlags.NONE

        # Source fields defintions
        self.fields: OrderedDict[FieldName, SourceField] = OrderedDict()
        self.pre_import: Optional[PreImport] = None

        if self.disable_reason:
            self.adapter.logger.debug("Created disabled %s", self)
            return

        pk_field = self.add_field(nautobot_wrapper.pk_field.name, SourceFieldSource.AUTO)
        pk_field.set_nautobot_field()
        pk_field.processed = True

        if issubclass(nautobot_wrapper.model, TreeModel):
            for name in ("tree_id", "lft", "rght", "level"):
                self.disable_field(name, "Tree fields doesn't need to be imported")

        self.adapter.logger.debug("Created %s", self)

    def __str__(self) -> str:
        """Return a string representation of the wrapper."""
        return f"{self.__class__.__name__}<{self.content_type} -> {self.nautobot.content_type}>"

    def cache_record_uids(self, source: RecordData, nautobot_uid: Optional[Uid] = None) -> Uid:
        """Cache record identifier mappings.

        When `nautobot_uid` is not provided, it is generated from the source data and caching is processed there.
        """
        if not nautobot_uid:
            return self.get_pk_from_data(source)

        if self.identifiers:
            identifiers_data = [source[field_name] for field_name in self.identifiers]
            self._uid_to_pk_cache[json.dumps(identifiers_data)] = nautobot_uid

        source_uid = source.get(self.nautobot.pk_field.name, None)
        if source_uid and source_uid not in self._uid_to_pk_cache:
            self._uid_to_pk_cache[source_uid] = nautobot_uid

        self._uid_to_pk_cache[nautobot_uid] = nautobot_uid

        return nautobot_uid

    def first_pass(self, data: RecordData) -> None:
        """Firts pass of data import."""
        if self.pre_import:
            if self.pre_import(data, ImporterPass.DEFINE_STRUCTURE) != PreImportResult.USE_RECORD:
                self.stats.first_pass_skipped += 1
                return

        self.stats.first_pass_used += 1

        if self.disable_reason:
            return

        for field_name in data.keys():
            self.add_field(field_name, SourceFieldSource.DATA)

    def second_pass(self, data: RecordData) -> None:
        """Second pass of data import."""
        if self.disable_reason:
            return

        if self.pre_import:
            if self.pre_import(data, ImporterPass.IMPORT_DATA) != PreImportResult.USE_RECORD:
                self.stats.second_pass_skipped += 1
                return

        self.stats.second_pass_used += 1

        self.import_record(data)

    def get_summary(self, content_type_id) -> SourceModelSummary:
        """Get a summary of the model."""
        fields = [field.get_summary() for field in self.fields.values()]

        return SourceModelSummary(
            content_type=self.content_type,
            content_type_id=content_type_id,
            extends_content_type=self.extends_wrapper and self.extends_wrapper.content_type,
            nautobot_content_type=self.nautobot.content_type,
            disable_reason=self.disable_reason,
            identifiers=self.identifiers,
            disable_related_reference=self.disable_related_reference,
            forward_references=self.forward_references and self.forward_references.__name__ or None,
            pre_import=self.pre_import and self.pre_import.__name__ or None,
            fields=sorted(fields, key=lambda field: field.name),
            flags=str(self.flags),
            default_reference_uid=serialize_to_summary(self.default_reference_uid),
            stats=self.stats,
        )

    def set_identifiers(self, identifiers: Iterable[FieldName]) -> None:
        """Set identifiers for the model."""
        if self.identifiers:
            if list(identifiers) == self.identifiers:
                return
            raise ValueError(
                f"Different identifiers were already set up | original: `{self.identifiers}` | new: `{identifiers}`"
            )

        if list(identifiers) == [self.nautobot.pk_field.name]:
            return

        self.identifiers = list(identifiers)
        for identifier in self.identifiers:
            self.add_field(identifier, SourceFieldSource.IDENTIFIER)

    def disable_field(self, field_name: FieldName, reason: str) -> "SourceField":
        """Disable field importing."""
        field = self.add_field(field_name, SourceFieldSource.CUSTOM)
        field.disable(reason)
        return field

    def format_field_name(self, name: FieldName) -> str:
        """Format a field name for logging."""
        return f"{self.content_type}->{name}"

    def add_field(self, name: FieldName, source: SourceFieldSource) -> "SourceField":
        """Add a field definition for a source field."""
        if self.importers is not None:
            raise ValueError(f"Can't add field {self.format_field_name(name)}, model's importers already created.")

        if name not in self.fields:
            return SourceField(self, name, source)

        field = self.fields[name]
        field.sources.add(source)
        return field

    def create_importers(self) -> None:
        """Create importers for all fields."""
        if self.importers is not None:
            raise RuntimeError(f"Importers already created for {self.content_type}")

        if not self.extends_wrapper:
            for field_name in AUTO_ADD_FIELDS:
                if hasattr(self.nautobot.model, field_name):
                    self.add_field(field_name, SourceFieldSource.AUTO)

        while True:
            fields = [field for field in self.fields.values() if not field.processed]
            if not fields:
                break

            for field in fields:
                try:
                    field.create_importer()
                except Exception:
                    self.adapter.logger.error("Failed to create importer for %s", field)
                    raise

        self.importers = set(field.importer for field in self.fields.values() if field.importer)

    def get_pk_from_uid(self, uid: Uid) -> Uid:
        """Get a source primary key for a given source uid."""
        if uid in self._uid_to_pk_cache:
            return self._uid_to_pk_cache[uid]

        if self.nautobot.pk_field.internal_type == InternalFieldType.UUID_FIELD:
            if self.extends_wrapper:
                result = self.extends_wrapper.get_pk_from_uid(uid)
            else:
                result = source_pk_to_uuid(self.content_type or self.content_type, uid)
        elif self.nautobot.pk_field.is_auto_increment:
            self.nautobot.last_id += 1
            result = self.nautobot.last_id
        else:
            raise ValueError(f"Unsupported pk_type {self.nautobot.pk_field.internal_type}")

        self._uid_to_pk_cache[uid] = result
        self._uid_to_pk_cache[result] = result

        return result

    def get_pk_from_identifiers(self, data: Union[Uid, Iterable[Uid]]) -> Uid:
        """Get a source primary key for a given source identifiers."""
        if not self.identifiers:
            if isinstance(data, (UUID, str, int)):
                return self.get_pk_from_uid(data)

            raise ValueError(f"Invalid identifiers {data} for {self.identifiers}")

        if not isinstance(data, list):
            data = list(data)  # type: ignore
        if len(self.identifiers) != len(data):
            raise ValueError(f"Invalid identifiers {data} for {self.identifiers}")

        identifiers_uid = json.dumps(data)
        if identifiers_uid in self._uid_to_pk_cache:
            return self._uid_to_pk_cache[identifiers_uid]

        filter_kwargs = {self.identifiers[index]: value for index, value in enumerate(data)}
        try:
            nautobot_instance = self.nautobot.model.objects.get(**filter_kwargs)
            nautobot_uid = getattr(nautobot_instance, self.nautobot.pk_field.name)
            if not nautobot_uid:
                raise ValueError(f"Invalid args {filter_kwargs} for {nautobot_instance}")
            self._uid_to_pk_cache[identifiers_uid] = nautobot_uid
            self._uid_to_pk_cache[nautobot_uid] = nautobot_uid
            return nautobot_uid
        except self.nautobot.model.DoesNotExist:  # type: ignore
            return self.get_pk_from_uid(identifiers_uid)

    def get_pk_from_data(self, data: RecordData) -> Uid:
        """Get a source primary key for a given source data."""
        if not self.identifiers:
            return self.get_pk_from_uid(data[self.nautobot.pk_field.name])

        data_uid = data.get(self.nautobot.pk_field.name, None)
        if data_uid and data_uid in self._uid_to_pk_cache:
            return self._uid_to_pk_cache[data_uid]

        result = self.get_pk_from_identifiers(data[field_name] for field_name in self.identifiers)

        if data_uid:
            self._uid_to_pk_cache[data_uid] = result

        return result

    def import_record(self, data: RecordData, target: Optional[DiffSyncBaseModel] = None) -> DiffSyncBaseModel:
        """Import a single item from the source."""
        self.adapter.logger.debug("Importing record %s %s", self, data)
        if self.importers is None:
            raise RuntimeError(f"Importers not created for {self}")

        if target:
            uid = getattr(target, self.nautobot.pk_field.name)
        else:
            uid = self.get_pk_from_data(data)
            target = self.get_or_create(uid)

        for importer in self.importers:
            try:
                importer(data, target)
            # pylint: disable=broad-exception-caught
            except Exception as error:
                self.nautobot.add_issue(
                    error.__class__.__name__,
                    getattr(error, "message", "") or str(error),
                    target=target,
                    field=error.field.nautobot if isinstance(error, SourceFieldImporterIssue) else None,
                )

        self.stats.imported += 1
        self.adapter.logger.debug("Imported %s %s", uid, target.get_attrs())

        return target

    def get_or_create(self, uid: Uid, fail_missing=False) -> DiffSyncBaseModel:
        """Get an existing DiffSync Model instance from the source or create a new one.

        Use Nautobot data as defaults if available.
        """
        filter_kwargs = {self.nautobot.pk_field.name: uid}
        diffsync_class = self.nautobot.diffsync_class
        result = self.adapter.get_or_none(diffsync_class, filter_kwargs)
        if result:
            if not isinstance(result, DiffSyncBaseModel):
                raise TypeError(f"Invalid instance type {result}")
            return result

        result = diffsync_class(**filter_kwargs, diffsync=self.adapter)  # type: ignore
        result.model_flags = self.flags

        cached_data = self._cached_data.get(uid, None)
        if cached_data:
            fail_missing = False
            self.import_record(cached_data, result)
            self.stats.imported_from_cache += 1

        nautobot_diffsync_instance = self.nautobot.find_or_create(filter_kwargs)
        if nautobot_diffsync_instance:
            fail_missing = False
            for key, value in nautobot_diffsync_instance.get_attrs().items():
                if value not in EMPTY_VALUES:
                    setattr(result, key, value)

        if fail_missing:
            raise ValueError(f"Missing {self} {uid} in Nautobot or cached data")

        self.adapter.add(result)
        self.stats.created += 1
        if self.flags == DiffSyncModelFlags.IGNORE:
            self.nautobot.stats.source_ignored += 1
        else:
            self.nautobot.stats.source_created += 1

        return result

    def get_default_reference_uid(self) -> Uid:
        """Get the default reference to this model."""
        if self.default_reference_uid:
            return self.default_reference_uid
        raise ValueError("Missing default reference")

    def cache_record(self, data: RecordData) -> Uid:
        """Cache data for optional later use.

        If record is referenced by other models, it will be imported automatically; otherwise, it will be ignored.
        """
        uid = self.get_pk_from_data(data)
        if uid in self._cached_data:
            return uid

        if self.importers is None:
            for field_name in data.keys():
                self.add_field(field_name, SourceFieldSource.CACHE)

        self._cached_data[uid] = data
        self.stats.pre_cached += 1

        self.adapter.logger.debug("Cached %s %s %s", self, uid, data)

        return uid

    def set_default_reference(self, data: RecordData) -> None:
        """Set the default reference to this model."""
        self.default_reference_uid = self.cache_record(data)

    def post_import(self) -> bool:
        """Post import processing.

        Assigns referenced content_types to the imported models.

        Returns False if no post processing is needed, otherwise True.
        """
        if not self.references:
            return False

        references = self.references
        self.references = {}

        if self.forward_references:
            self.forward_references(self, references)
            return True

        for uid, content_types in references.items():
            # Keep this even when no content_types field is present, to create referenced cached data
            instance = self.get_or_create(uid, fail_missing=True)
            if "content_types" not in self.nautobot.fields:
                continue

            content_types = set(wrapper.nautobot.content_type_instance.pk for wrapper in content_types)
            target_content_types = getattr(instance, "content_types", None)
            if target_content_types != content_types:
                if target_content_types:
                    target_content_types.update(content_types)
                else:
                    instance.content_types = content_types
                self.adapter.update(instance)

        return True

    def add_reference(self, related_wrapper: "SourceModelWrapper", uid: Uid) -> None:
        """Add a reference from this content type to related record."""
        if self.disable_related_reference:
            return
        self.adapter.logger.debug(
            "Adding reference from: %s to: %s %s", self.content_type, related_wrapper.content_type, uid
        )
        if not uid:
            raise ValueError(f"Invalid uid {uid}")
        related_wrapper.references.setdefault(uid, set()).add(self)


# pylint: disable=too-many-public-methods
class SourceField:
    """Source Field."""

    def __init__(self, wrapper: SourceModelWrapper, name: FieldName, source: SourceFieldSource):
        """Initialize the SourceField."""
        self.wrapper = wrapper
        wrapper.fields[name] = self
        self.name = name
        self.definition: SourceFieldDefinition = name
        self.sources = set((source,))
        self.processed = False
        self._nautobot: Optional[NautobotField] = None
        self.importer: Optional[SourceFieldImporter] = None
        self.default_value: Any = None
        self.disable_reason: str = ""

    def __str__(self) -> str:
        """Return a string representation of the field."""
        return self.wrapper.format_field_name(self.name)

    @property
    def nautobot(self) -> NautobotField:
        """Get the Nautobot field wrapper."""
        if not self._nautobot:
            raise RuntimeError(f"Missing Nautobot field for {self}")
        return self._nautobot

    def get_summary(self) -> FieldSummary:
        """Get a summary of the field."""
        return FieldSummary(
            name=self.name,
            nautobot_name=self._nautobot and self._nautobot.name,
            nautobot_internal_type=self._nautobot and self._nautobot.internal_type.value,
            nautobot_can_import=self._nautobot and self._nautobot.can_import,
            importer=self.importer and self.importer.__name__,
            definition=serialize_to_summary(self.definition),
            sources=sorted(source.name for source in self.sources),
            default_value=serialize_to_summary(self.default_value),
            disable_reason=self.disable_reason,
            required=self._nautobot.required if self._nautobot else False,
        )

    def disable(self, reason: str) -> None:
        """Disable field importing."""
        self.definition = None
        self.importer = None
        self.processed = True
        self.disable_reason = reason

    def handle_sibling(self, sibling: Union["SourceField", FieldName], nautobot_name: FieldName = "") -> "SourceField":
        """Specify, that this field importer handles other field."""
        if not self.importer:
            raise RuntimeError(f"Call `handle sibling` after setting importer for {self}")

        if isinstance(sibling, FieldName):
            sibling = self.wrapper.add_field(sibling, SourceFieldSource.SIBLING)

        sibling.set_nautobot_field(nautobot_name or self.nautobot.name)
        sibling.importer = self.importer
        sibling.processed = True

        if self.nautobot.can_import and not sibling.nautobot.can_import:
            self.disable(f"Can't import {self} based on {sibling}")

        return sibling

    def add_issue(self, issue_type: str, message: str, target: Optional[DiffSyncModel] = None) -> None:
        """Add an importer issue to the Nautobot Model Wrapper."""
        self.wrapper.nautobot.add_issue(issue_type, message, target=target, field=self.nautobot)

    def set_definition(self, definition: SourceFieldDefinition) -> None:
        """Customize field definition."""
        if self.processed:
            raise RuntimeError(f"Field already processed. {self}")

        if self.definition != definition:
            if self.definition != self.name:
                self.add_issue(
                    "OverrideDefinition",
                    f"Overriding field definition | Original: `{self.definition}` | New: `{definition}`",
                )
            self.definition = definition

    def create_importer(self) -> None:
        """Create importer for the field."""
        if self.processed:
            return
        self.processed = True

        if self.definition is None:
            return

        if isinstance(self.definition, FieldName):
            self.set_importer(nautobot_name=self.definition)
        elif callable(self.definition):
            self.definition(self)
        else:
            raise NotImplementedError(f"Unsupported field definition {self.definition}")

    def get_source_value(self, source: RecordData) -> Any:
        """Get a value from the source data, returning a default value if the value is empty."""
        if self.name not in source:
            return self.default_value

        result = source[self.name]
        return self.default_value if result in EMPTY_VALUES else result

    def set_nautobot_value(self, target: DiffSyncModel, value: Any) -> None:
        """Set a value to the Nautobot model."""
        if value in EMPTY_VALUES:
            if hasattr(target, self.nautobot.name):
                delattr(target, self.nautobot.name)
        else:
            setattr(target, self.nautobot.name, value)

    def set_nautobot_field(self, nautobot_name: FieldName = "") -> NautobotField:
        """Set a Nautobot field name for the field."""
        result = self.wrapper.nautobot.add_field(nautobot_name or self.name)
        if result.field:
            default_value = getattr(result.field, "default", None)
            if default_value not in EMPTY_VALUES and not isinstance(default_value, Callable):
                self.default_value = default_value
        self._nautobot = result
        if result.name == "last_updated":
            self.disable("Last updated field is updated with each write")
        return result

    # pylint: disable=too-many-branches
    def set_importer(
        self,
        importer: Optional[SourceFieldImporter] = None,
        nautobot_name: Optional[FieldName] = "",
        override=False,
    ) -> Optional[SourceFieldImporter]:
        """Sets the importer and Nautobot field if not already specified.

        If `nautobot_name` is not provided, the field name is used.

        Passing None to `nautobot_name` indicates that there is custom mapping without a direct relationship to a Nautobot field.
        """
        if self.disable_reason:
            raise RuntimeError(f"Can't set importer for disabled {self}")
        if self.importer and not override:
            raise RuntimeError(f"Importer already set for {self}")
        if not self._nautobot and nautobot_name is not None:
            self.set_nautobot_field(nautobot_name)

        if importer:
            self.importer = importer
            return importer

        if self.disable_reason or not self.nautobot.can_import:
            return None

        internal_type = self.nautobot.internal_type

        if internal_type == InternalFieldType.JSON_FIELD:
            self.set_json_importer()
        elif internal_type == InternalFieldType.DATE_FIELD:
            self.set_date_importer()
        elif internal_type == InternalFieldType.DATE_TIME_FIELD:
            self.set_datetime_importer()
        elif internal_type == InternalFieldType.UUID_FIELD:
            self.set_uuid_importer()
        elif internal_type == InternalFieldType.MANY_TO_MANY_FIELD:
            self.set_m2m_importer()
        elif internal_type == InternalFieldType.STATUS_FIELD:
            self.set_status_importer()
        elif self.nautobot.is_reference:
            self.set_relation_importer()
        elif getattr(self.nautobot.field, "choices", None):
            self.set_choice_importer()
        elif self.nautobot.is_integer:
            self.set_integer_importer()
        else:
            self.set_value_importer()

        return self.importer

    def set_value_importer(self) -> None:
        """Set a value importer."""

        def value_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = self.get_source_value(source)
            self.set_nautobot_value(target, value)

        self.set_importer(value_importer)

    def set_json_importer(self) -> None:
        """Set a JSON field importer."""

        def json_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(self.name, None)
            if isinstance(value, str) and value:
                value = json.loads(value)
            self.set_nautobot_value(target, value)

        self.set_importer(json_importer)

    def set_choice_importer(self) -> None:
        """Set a choice field importer."""
        field_choices = getattr(self.nautobot.field, "choices", None)
        if not field_choices:
            raise ValueError(f"Invalid field_choices for {self}")

        def get_choices(items: Iterable) -> Generator[Tuple[Any, Any], None, None]:
            for key, value in items:
                if isinstance(value, (list, tuple)):
                    yield from get_choices(value)
                else:
                    yield key, value

        choices = dict(get_choices(field_choices))

        def choice_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = self.get_source_value(source)
            if value in choices:
                self.set_nautobot_value(target, value)
            elif self.nautobot.required:
                # Set the choice value even it's not valid in Nautobot as it's required
                self.set_nautobot_value(target, value)
                raise InvalidChoiceValueIssue(self, value)
            elif value in EMPTY_VALUES:
                self.set_nautobot_value(target, value)
            else:
                raise InvalidChoiceValueIssue(self, value, None)

        self.set_importer(choice_importer)

    def set_integer_importer(self) -> None:
        """Set an integer field importer."""

        def integer_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            source_value = self.get_source_value(source)
            if source_value in EMPTY_VALUES:
                self.set_nautobot_value(target, source_value)
            else:
                source_value = float(source_value)
                value = int(source_value)
                self.set_nautobot_value(target, value)
                if value != source_value:
                    raise SourceFieldImporterIssue(f"Invalid source value {source_value}, truncated to {value}", self)

        self.set_importer(integer_importer)

    def set_relation_importer(self, related_wrapper: Optional[SourceModelWrapper] = None) -> None:
        """Set a relation importer."""
        wrapper = self.wrapper
        if not related_wrapper:
            if self.name == "parent":
                related_wrapper = wrapper
            else:
                related_wrapper = wrapper.adapter.get_or_create_wrapper(self.nautobot.related_model)

        if self.nautobot.is_content_type:
            self.set_content_type_importer()
            return

        if self.default_value in EMPTY_VALUES and related_wrapper.default_reference_uid:
            self.default_value = related_wrapper.default_reference_uid

        if not (self.default_value is None or isinstance(self.default_value, UUID)):
            raise NotImplementedError(f"Default value {self.default_value} is not a UUID")

        def relation_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = self.get_source_value(source)
            if value in EMPTY_VALUES:
                self.set_nautobot_value(target, value)
            else:
                if isinstance(value, (UUID, str, int)):
                    result = related_wrapper.get_pk_from_uid(value)
                else:
                    result = related_wrapper.get_pk_from_identifiers(value)
                self.set_nautobot_value(target, result)
                wrapper.add_reference(related_wrapper, result)

        self.set_importer(relation_importer)

    def set_content_type_importer(self) -> None:
        """Set a content type importer."""
        adapter = self.wrapper.adapter

        def content_type_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            content_type = source.get(self.name, None)
            if content_type not in EMPTY_VALUES:
                content_type = adapter.get_nautobot_content_type_uid(content_type)
            self.set_nautobot_value(target, content_type)

        self.set_importer(content_type_importer)

    def set_m2m_importer(self) -> None:
        """Set a many to many importer."""
        if not isinstance(self.nautobot.field, DjangoField):
            raise NotImplementedError(f"Unsupported m2m importer {self}")

        related_wrapper = self.wrapper.adapter.get_or_create_wrapper(self.nautobot.related_model)

        if related_wrapper.content_type == "contenttypes.contenttype":
            self.set_content_types_importer()
        elif related_wrapper.identifiers:
            self.set_identifiers_importer(related_wrapper)
        else:
            self.set_uuids_importer(related_wrapper)

    def set_identifiers_importer(self, related_wrapper: SourceModelWrapper) -> None:
        """Set a identifiers importer."""

        def identifiers_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            values = source.get(self.name, None)
            if values not in EMPTY_VALUES:
                if not isinstance(values, (list, set)):
                    raise ValueError(f"Invalid value {values} for field {self.name}")
                values = set(related_wrapper.get_pk_from_identifiers(item) for item in values)

            self.set_nautobot_value(target, values)

        self.set_importer(identifiers_importer)

    def set_content_types_importer(self) -> None:
        """Set a content types importer."""
        adapter = self.wrapper.adapter

        def content_types_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            values = source.get(self.name, None)
            if values in EMPTY_VALUES:
                return

            if not isinstance(values, (list, set)):
                raise ValueError(f"Invalid value {values} for field {self.name}")

            nautobot_values = set()
            for item in values:
                try:
                    nautobot_values.add(adapter.get_nautobot_content_type_uid(item))
                except NautobotModelNotFound:
                    self.add_issue("InvalidContentType", f"Invalid content type {item}, skipping", target)

            self.set_nautobot_value(target, nautobot_values)

        self.set_importer(content_types_importer)

    def set_uuids_importer(self, related_wrapper: SourceModelWrapper) -> None:
        """Set a UUIDs importer."""

        def uuids_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(self.name, None)
            if value in EMPTY_VALUES:
                self.set_nautobot_value(target, value)
            if isinstance(value, (UUID, str, int)):
                self.set_nautobot_value(target, {related_wrapper.get_pk_from_uid(value)})
            elif isinstance(value, (list, set, tuple)):
                self.set_nautobot_value(target, set(related_wrapper.get_pk_from_uid(item) for item in value))
            else:
                raise SourceFieldImporterIssue(f"Invalid value {value} for field {self.name}", self)

        self.set_importer(uuids_importer)

    def set_datetime_importer(self) -> None:
        """Set a datetime importer."""

        def datetime_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(self.name, None)
            if value not in EMPTY_VALUES:
                value = normalize_datetime(value)
            self.set_nautobot_value(target, value)

        self.set_importer(datetime_importer)

    def set_relation_and_type_importer(self, type_field: "SourceField") -> None:
        """Set a relation UUID importer based on the type field."""

        def relation_and_type_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            source_uid = source.get(self.name, None)
            source_type = source.get(type_field.name, None)
            if source_type in EMPTY_VALUES or source_uid in EMPTY_VALUES:
                if source_uid not in EMPTY_VALUES or source_type not in EMPTY_VALUES:
                    raise ValueError(
                        f"Both {self}=`{source_uid}` and {type_field}=`{source_type}` must be empty or not empty."
                    )
                return

            type_wrapper = self.wrapper.adapter.get_or_create_wrapper(source_type)
            uid = type_wrapper.get_pk_from_uid(source_uid)
            self.set_nautobot_value(target, uid)
            type_field.set_nautobot_value(target, type_wrapper.nautobot.content_type_instance.pk)
            self.wrapper.add_reference(type_wrapper, uid)

        self.set_importer(relation_and_type_importer)
        self.handle_sibling(type_field, type_field.name)

    def set_uuid_importer(self) -> None:
        """Set an UUID importer."""
        if self.name.endswith("_id"):
            type_field = self.wrapper.fields.get(self.name[:-3] + "_type", None)
            if type_field and type_field.nautobot.is_content_type:
                # Handles `<field name>_id` and `<field name>_type` fields combination
                self.set_relation_and_type_importer(type_field)
                return

        def uuid_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(self.name, None)
            if value not in EMPTY_VALUES:
                value = UUID(value)
            self.set_nautobot_value(target, value)

        self.set_importer(uuid_importer)

    def set_date_importer(self) -> None:
        """Set a date importer."""

        def date_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            value = source.get(self.name, None)
            if value not in EMPTY_VALUES and not isinstance(value, datetime.date):
                value = datetime.date.fromisoformat(str(value))
            self.set_nautobot_value(target, value)

        self.set_importer(date_importer)

    def set_status_importer(self) -> None:
        """Set a status importer."""
        status_wrapper = self.wrapper.adapter.get_or_create_wrapper("extras.status")
        if not self.default_value:
            self.default_value = status_wrapper.default_reference_uid

        if not (self.default_value is None or isinstance(self.default_value, UUID)):
            raise NotImplementedError(f"Default value {self.default_value} is not a UUID")

        def status_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            status = source.get(self.name, None)
            if status:
                value = status_wrapper.cache_record({"name": status[0].upper() + status[1:]})
            else:
                value = self.default_value

            self.set_nautobot_value(target, value)
            if value:
                self.wrapper.add_reference(status_wrapper, value)

        self.set_importer(status_importer)
