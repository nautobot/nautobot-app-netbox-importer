"""Generic DiffSync Source Importer."""
import datetime
import json
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
from typing import Union
from uuid import UUID

from dateutil import parser as datetime_parser
from diffsync.exceptions import ObjectNotFound as DiffSyncObjectNotFound
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist as DjangoFieldDoesNotExist
from django.db.models import Field as DjangoField
from nautobot.core.models.tree_queries import TreeModel

from .base import EMPTY_VALUES
from .base import INTEGER_INTERNAL_TYPES
from .base import ONLY_ID_IDENTIFIERS
from .base import REFERENCE_INTERNAL_TYPES
from .base import BaseAdapter
from .base import ContentTypeStr
from .base import ContentTypeValue
from .base import FieldName
from .base import InternalFieldTypeStr
from .base import NautobotBaseModel
from .base import NautobotBaseModelType
from .base import RecordData
from .base import Uid
from .base import logger
from .base import source_pk_to_uuid
from .nautobot import IMPORT_ORDER
from .nautobot import ImporterModel
from .nautobot import NautobotAdapter
from .nautobot import NautobotModelWrapper


class SourceRecord(NamedTuple):
    """Source Data Item."""

    content_type: ContentTypeStr
    data: RecordData


SourceDataGenerator = Callable[[], Iterable[SourceRecord]]
SourceFieldImporter = Callable[[RecordData, RecordData], None]
SourceFieldImporterFactory = Callable[["SourceField"], None]
SourceFieldDefinition = Union[
    None,  # Ignore field
    FieldName,  # Rename field
    SourceFieldImporterFactory,  # Field importer factory
]


class ReferencesForwarding(NamedTuple):
    """Forward references to another model."""

    content_type: ContentTypeStr
    field_name: FieldName


class SourceAdapter(BaseAdapter):
    """Source DiffSync Adapter."""

    def __init__(self, name: str, *args, **kwargs):
        """Initialize the SourceAdapter."""
        super().__init__(name, *args, **kwargs)

        self.wrappers: OrderedDict[ContentTypeStr, SourceModelWrapper] = OrderedDict()
        self.nautobot = NautobotAdapter()
        self.ignored_fields: Set[FieldName] = set()
        self.ignored_content_types: Set[ContentTypeStr] = set()

        # From Nautobot to Source content type mapping
        # When multiple source content types are mapped to single nautobot content type, mapping is set to `None`
        self.content_types_back_mapping: Dict[ContentTypeStr, Optional[ContentTypeStr]] = {}

    def configure(
        self,
        ignore_fields: Optional[Iterable[FieldName]] = None,
        ignore_content_types: Optional[Iterable[ContentTypeStr]] = None,
    ) -> None:
        """Configure the adapter."""
        if ignore_fields:
            self.ignored_fields.update(ignore_fields)
        if ignore_content_types:
            self.ignored_content_types.update(ignore_content_types)

    # pylint: disable=too-many-arguments, too-many-branches
    def configure_model(
        self,
        content_type: ContentTypeStr,
        nautobot_content_type: Optional[ContentTypeStr] = None,
        extend_content_type: Optional[ContentTypeStr] = None,
        identifiers: Optional[Iterable[FieldName]] = None,
        fields: Optional[Mapping[FieldName, SourceFieldDefinition]] = None,
        default_reference: Optional[RecordData] = None,
    ) -> "SourceModelWrapper":
        """Dynamically create and configure a wrapper for a given source content type."""
        if extend_content_type:
            extend_wrapper = self.wrappers[extend_content_type]
            if nautobot_content_type and nautobot_content_type != extend_wrapper.nautobot.content_type:
                raise ValueError(f"Extension should have the same Nautobot content type {nautobot_content_type}")
            nautobot_content_type = extend_wrapper.nautobot.content_type
        else:
            extend_wrapper = None
            nautobot_content_type = nautobot_content_type or content_type
            if nautobot_content_type in self.content_types_back_mapping:
                if self.content_types_back_mapping[nautobot_content_type] != content_type:
                    self.content_types_back_mapping[nautobot_content_type] = None
            else:
                self.content_types_back_mapping[nautobot_content_type] = content_type

        if content_type in self.wrappers:
            wrapper = self.wrappers[content_type]
        else:
            nautobot_wrapper = self.nautobot.get_or_create_wrapper(nautobot_content_type)
            wrapper = SourceModelWrapper(self, content_type, nautobot_wrapper, extend_wrapper)

        if identifiers:
            wrapper.set_identifiers(identifiers)
        if fields:
            wrapper.set_fields(**fields)
        if default_reference:
            wrapper.set_default_reference(**default_reference)

        return wrapper

    def get_or_create_wrapper(
        self,
        value: Union[None, ContentTypeValue, "SourceModelWrapper", NautobotModelWrapper, NautobotBaseModelType],
    ) -> "SourceModelWrapper":
        """Get a source Wrapper for a given content type."""
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
            pass
        elif isinstance(value, int):
            raise NotImplementedError("Integer content type")
        elif isinstance(value, Iterable) and len(value) == 2:
            value = ".".join(value)
        else:
            raise ValueError(f"Invalid content type {value}")

        if map_back and value in self.content_types_back_mapping:
            back_mapping = self.content_types_back_mapping.get(value, None)
            if not back_mapping:
                raise ValueError(f"Unambiguous content type back mapping {value}")
            value = back_mapping

        if value in self.wrappers:
            return self.wrappers[value]

        return self.configure_model(value)

    def get_nautobot_content_type_instance(self, content_type: ContentTypeValue) -> ContentType:
        """Get the Django content type ID for a given content type."""
        if isinstance(content_type, int):
            raise NotImplementedError("Integer content type not implemented")
        if not isinstance(content_type, str):
            if not len(content_type) == 2:
                raise ValueError(f"Invalid content type {content_type}")
            content_type = ".".join(content_type)

        wrapper = self.get_or_create_wrapper(content_type)

        return wrapper.nautobot.content_type_instance

    def import_data(self, get_source_data: SourceDataGenerator) -> None:
        """Import data from the source."""

        def create_structure(content_type: ContentTypeStr, data: RecordData):
            if content_type in self.wrappers:
                wrapper = self.wrappers[content_type]
                if wrapper is None:
                    return
            else:
                wrapper = self.configure_model(content_type)

            for field_name in data.keys():
                if field_name.startswith("_") or field_name in self.ignored_fields:
                    wrapper.add_field(field_name, None, from_data=True)
                else:
                    wrapper.add_field(field_name, field_name, from_data=True)

        # First pass to enhance pre-defined wrappers structure
        for content_type, data in get_source_data():
            if content_type not in self.ignored_content_types:
                create_structure(content_type, data)

        # Create importers, wrappers structure is updated as needed
        while True:
            wrappers = [wrapper for wrapper in self.wrappers.values() if wrapper.importers is None]
            if not wrappers:
                break
            for wrapper in wrappers:
                wrapper.create_importers()

        # Second pass to import actual data
        for content_type, data in get_source_data():
            if content_type in self.ignored_content_types:
                continue
            wrapper = self.wrappers.get(content_type, None)
            if wrapper:
                wrapper.import_record(data)

        # Post processing
        while any(wrapper.post_import() for wrapper in self.wrappers.values()):
            pass

    def import_nautobot(self) -> NautobotAdapter:
        """Import all Nautobot data."""
        for nautobot_wrapper in self.get_imported_nautobot_wrappers():
            importer_model = nautobot_wrapper.importer
            if not importer_model:
                raise TypeError(f"Missing importer_model for {nautobot_wrapper.content_type}")

            for nautobot_instance in nautobot_wrapper.model.objects.all():
                data = nautobot_wrapper.get_data_from_instance(nautobot_instance)
                try:
                    instance = importer_model(**data, diffsync=self.nautobot)
                    self.nautobot.add(instance)
                except Exception:
                    logger.error("Failed to create instance %s", data, exc_info=True)
                    raise

            # pylint: disable=protected-access
            model_name = importer_model._modelname
            self.top_level.append(model_name)
            setattr(self, model_name, importer_model)
            setattr(self.nautobot, model_name, getattr(self, model_name))

        return self.nautobot

    def get_imported_nautobot_wrappers(self) -> Generator[NautobotModelWrapper, None, None]:
        """Get a list of Nautobot model wrappers in the order of import."""
        result = OrderedDict()

        for wrapper in self.wrappers.values():
            if wrapper and wrapper.imported_count > 0 and wrapper.nautobot.content_type not in result:
                result[wrapper.nautobot.content_type] = wrapper.nautobot

        for content_type in IMPORT_ORDER:
            if content_type in result:
                yield result[content_type]
                del result[content_type]

        yield from result.values()


# pylint: disable=too-many-instance-attributes
class SourceModelWrapper:
    """Definition of a source model mapping to Nautobot model."""

    def __init__(
        self,
        adapter: SourceAdapter,
        content_type: ContentTypeStr,
        nautobot_wrapper: NautobotModelWrapper,
        extend_wrapper: Optional["SourceModelWrapper"] = None,
    ):
        """Initialize the SourceModelWrapper."""
        if content_type in adapter.wrappers:
            raise ValueError(f"Duplicate content type {content_type}")
        adapter.wrappers[content_type] = self
        self.adapter = adapter
        self.content_type = content_type
        self.nautobot = nautobot_wrapper

        # Source field names when referencing this model
        self.identifiers = ONLY_ID_IDENTIFIERS

        # Used to autofill `content_types` field
        self.references: Dict[Uid, Set[SourceModelWrapper]] = {}
        self.references_forwarding: Optional[ReferencesForwarding] = None

        # Whether importing record data exteds existing record
        self.extend_wrapper = extend_wrapper

        # Importers
        self.importers: Optional[List[SourceFieldImporter]] = None

        # Default reference to this model
        self.default_reference_uid: Optional[Uid] = None

        # Caching
        self._uid_to_pk_cache: Dict[Uid, Uid] = {}
        self._cached_data: Dict[Uid, RecordData] = {}

        # Stats
        self.imported_count = 0

        # Source fields defintions
        self.fields: OrderedDict[FieldName, SourceField] = OrderedDict()
        self.add_field(self.nautobot.pk_name, None)
        self.fields[self.nautobot.pk_name].nautobot_name = self.nautobot.pk_name
        if issubclass(self.nautobot.model, TreeModel):
            self.set_fields(
                tree_id=None,
                lft=None,
                rght=None,
                level=None,
            )

        logger.debug("Created wrapper for %s", content_type)

    def set_identifiers(self, identifiers: Iterable[FieldName]) -> None:
        """Set identifiers for the model."""
        if self.identifiers is not ONLY_ID_IDENTIFIERS:
            raise ValueError(f"Duplicate identifiers {identifiers} for {self.identifiers}")

        if list(identifiers) != self.identifiers:
            self.identifiers = list(identifiers)

    def set_references_forwarding(self, content_type: ContentTypeStr, field_name: FieldName) -> None:
        """Set references forwarding to another model.

        When other models reference this model, they will be forwarded to `content_type` source model wrapper, based on `field_name`.
        e.g. References to Site, Region or Location are forwarded to LocationType.
        """
        self.references_forwarding = ReferencesForwarding(content_type, field_name)

    def set_fields(self, *field_names: FieldName, **fields: SourceFieldDefinition) -> None:
        """Set fields definitions."""
        for field_name in field_names:
            self.add_field(field_name, field_name)
        for field_name, definition in fields.items():
            self.add_field(field_name, definition)

    def format_field_name(self, name: FieldName) -> str:
        """Format a field name for logging."""
        return f"{self.content_type}->{name}"

    def add_field(self, name: FieldName, definition: SourceFieldDefinition, from_data: bool = False) -> None:
        """Add a field definition for a source field."""
        if self.importers is not None:
            raise ValueError(f"Can't add field {self.format_field_name(name)}, model's importers already created.")
        if name in self.fields:
            if from_data:
                # Do not update the definition from data when already defined
                self.fields[name].from_data = True
            else:
                self.fields[name].reset_definition(definition)
        else:
            self.fields[name] = SourceField(self, name, definition, from_data)

    def create_importers(self) -> None:
        """Create importers for all fields."""
        if self.importers is not None:
            raise RuntimeError(f"Importers already created for {self.content_type}")

        while True:
            fields = [field_name for field_name, field in self.fields.items() if not field.processed]
            if not fields:
                break

            for field_name in fields:
                try:
                    self.fields[field_name].create_importer()
                except Exception:
                    logger.error("Failed to create importer for %s", self.format_field_name(field_name))
                    raise

        self.importers = [field.importer for field in self.fields.values() if field.importer]

    def get_pk_from_uid(self, uid: Uid) -> Uid:
        """Get a source primary key for a given source uid."""
        if uid in self._uid_to_pk_cache:
            return self._uid_to_pk_cache[uid]

        if self.nautobot.pk_type == "UUIDField":
            if self.extend_wrapper:
                result = self.extend_wrapper.get_pk_from_uid(uid)
            else:
                result = source_pk_to_uuid(self.content_type or self.content_type, uid)
        elif self.nautobot.pk_type == "AutoField":
            self.nautobot.last_id += 1
            result = self.nautobot.last_id
        else:
            raise ValueError(f"Unsupported pk_type {self.nautobot.pk_type}")

        self._uid_to_pk_cache[uid] = result
        return result

    def get_pk_from_identifiers(self, data: Union[Uid, Iterable[Uid]]) -> Uid:
        """Get a source primary key for a given source identifiers."""
        if self.identifiers is ONLY_ID_IDENTIFIERS:
            if isinstance(data, (UUID, str, int)):
                return self.get_pk_from_uid(data)

            raise ValueError(f"Invalid identifiers {data} for {self.identifiers}")

        if not isinstance(data, list):
            data = list(data)  # type: ignore
        if len(self.identifiers) != len(data):
            raise ValueError(f"Invalid identifiers {data} for {self.identifiers}")

        uid = json.dumps(data)
        if uid in self._uid_to_pk_cache:
            return self._uid_to_pk_cache[uid]

        filter_kwargs = {self.identifiers[index]: value for index, value in enumerate(data)}
        try:
            nautobot_instance = self.nautobot.model.objects.get(**filter_kwargs)
            self._uid_to_pk_cache[uid] = nautobot_instance.id
            return nautobot_instance.id
        except self.nautobot.model.DoesNotExist:  # type: ignore
            return self.get_pk_from_uid(uid)

    def get_pk_from_data(self, data: RecordData) -> Uid:
        """Get a source primary key for a given source data."""
        if self.identifiers is ONLY_ID_IDENTIFIERS:
            return self.get_pk_from_uid(data["id"])
        return self.get_pk_from_identifiers(data[field_name] for field_name in self.identifiers)

    def import_record(self, data: RecordData) -> ImporterModel:
        """Import a single item from the source."""
        logger.debug("Importing item %s %s", self.content_type, data)
        nautobot_content_type = self.nautobot.content_type
        importer_model = self.nautobot.get_importer()
        uid = self.get_pk_from_data(data)
        instance = self.adapter.get_or_none(importer_model, {"id": uid})

        target_data = {}
        if uid:
            target_data["id"] = uid

        if self.importers is None:
            raise RuntimeError(f"Importers not created for {self.content_type}")

        for importer in self.importers:
            importer(data, target_data)

        try:
            if instance:
                logger.debug("Updating instance %s %s with %s", nautobot_content_type, instance, target_data)
                if not isinstance(instance, ImporterModel):
                    raise TypeError(f"Invalid instance type {instance}")
                for key, value in target_data.items():
                    if value not in EMPTY_VALUES:
                        setattr(instance, key, value)
                self.adapter.update(instance)
            else:
                logger.debug("Adding instance %s %s", nautobot_content_type, target_data)
                instance = importer_model(**target_data, diffsync=self.adapter)
                self.adapter.add(instance)
                self.nautobot.imported_count += 1

            self.imported_count += 1
            return instance
        except Exception:
            logger.error("Failed to create or add instance %s %s %s %s", nautobot_content_type, data, uid, target_data)
            raise

    def get(self, uid: Uid) -> ImporterModel:
        """Get a single item from the source."""
        try:
            result = self.adapter.get(self.nautobot.get_importer(), {"id": uid})
            if not isinstance(result, ImporterModel):
                raise TypeError(f"Invalid result type {result}")
            return result
        except DiffSyncObjectNotFound:
            if uid in self._cached_data:
                return self.import_record(self._cached_data[uid])
            raise

    def get_default_reference_uid(self) -> Uid:
        """Get the default reference to this model."""
        if self.default_reference_uid:
            return self.default_reference_uid
        raise ValueError("Missing default reference")

    def cache_data(self, data: RecordData) -> Uid:
        """Cache data for optional later use.

        If `data` are referenced by other models, they will be imported automatically, otherwise they will be ignored.
        """
        uid = self.get_pk_from_data(data)
        if uid in self._cached_data:
            return uid

        if self.importers is None:
            for field_name in data.keys():
                self.add_field(field_name, field_name, from_data=True)

        self._cached_data[uid] = data
        return uid

    def set_default_reference(self, **data: Any) -> None:
        """Set the default reference to this model."""
        self.default_reference_uid = self.cache_data(data)

    def post_import(self) -> bool:
        """Post import processing.

        Assigns referenced content_types to the imported models.

        Returns False if no post processing is needed, otherwise True.
        """
        if not self.references:
            return False

        references = self.references
        self.references = {}

        if self.references_forwarding:
            forward_to = self.adapter.get_or_create_wrapper(self.references_forwarding.content_type)
            field_name = self.references_forwarding.field_name
            for uid, content_types in references.items():
                instance = self.get(uid)
                for content_type in content_types:
                    forward_to.add_reference(getattr(instance, field_name), content_type)
            return True

        for uid, content_types in references.items():
            instance = self.get(uid)
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

    def add_reference(self, uid: Uid, wrapper: "SourceModelWrapper") -> None:
        """Add a reference from one content type to another."""
        logger.debug("Adding reference %s %s %s", self.content_type, uid, wrapper.content_type)
        if uid in self.references:
            self.references[uid].add(wrapper)
        else:
            self.references[uid] = {wrapper}


# pylint: disable=too-many-public-methods
class SourceField:
    """Source Field."""

    def __init__(
        self,
        wrapper: SourceModelWrapper,
        name: FieldName,
        definition: SourceFieldDefinition,
        from_data=False,
    ):
        """Initialize the SourceField."""
        self.wrapper = wrapper
        self.name = name
        self.from_data = from_data
        self.is_custom = not from_data
        self.definition = definition
        self.processed = False
        if definition is None:
            logger.warning("Skipping field %s", wrapper.format_field_name(name))
        else:
            logger.warning("Adding field %s", wrapper.format_field_name(name))
        self.nautobot_name: FieldName = ""
        self.importer: Optional[SourceFieldImporter] = None
        self.internal_type: InternalFieldTypeStr = "None"
        self.django_field: Optional[DjangoField] = None
        self.default_value: Any = None

    def __str__(self) -> str:
        """Return a string representation of the field."""
        return self.wrapper.format_field_name(self.name)

    def reset_definition(self, definition: SourceFieldDefinition) -> None:
        """Set a custom definition for the field."""
        if self.processed:
            raise RuntimeError(f"Field already processed. {self.wrapper.format_field_name(self.name)}")
        if self.is_custom:
            raise RuntimeError(
                f"Can't reset custom definition for a non-custom field {self.wrapper.format_field_name(self.name)}"
            )
        self.is_custom = True
        self.definition = definition

    def create_importer(self) -> None:
        """Create importer for the field."""
        if self.processed:
            raise RuntimeError(f"Field {self.wrapper.format_field_name(self.name)} already processed")
        self.processed = True

        if self.definition is None:
            return

        if isinstance(self.definition, FieldName):
            self.set_default_importer(self.definition)
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

    def set_nautobot_field(self, nautobot_name: FieldName) -> None:
        """Set a Nautobot field name for the field."""
        meta = self.wrapper.nautobot.model._meta

        if nautobot_name == "custom_field_data":
            self.django_field = meta.get_field("_custom_field_data")
            self.internal_type = "CustomFieldData"
        else:
            try:
                self.django_field = meta.get_field(nautobot_name)
                if isinstance(self.django_field, GenericForeignKey):
                    # GenericForeignKey is not a real field, doesn't have `get_internal_type` method
                    self.internal_type = "GenericForeignKey"
                elif hasattr(self.django_field, "get_internal_type"):
                    self.internal_type = self.django_field.get_internal_type()
                    if self.internal_type in REFERENCE_INTERNAL_TYPES and self.internal_type != "ManyToManyField":
                        # Reference fields are converted to id fields
                        nautobot_name = f"{nautobot_name}_id"
                else:
                    raise NotImplementedError(f"Unsupported field type {self}")
            except DjangoFieldDoesNotExist:
                if not hasattr(self.wrapper.nautobot.model, nautobot_name):
                    logger.warning(
                        "Missing Nautobot field or property %s, skipping",
                        self.wrapper.format_field_name(nautobot_name),
                    )
                    return
                self.internal_type = "Property"

        self.nautobot_name = nautobot_name
        self.wrapper.nautobot.add_field(nautobot_name, self.internal_type)
        if self.django_field:
            self.default_value = getattr(self.django_field, "default", None)
            if self.default_value in EMPTY_VALUES:
                self.default_value = None

    def set_importer(self, importer: Optional[SourceFieldImporter]) -> None:
        """Set field importer."""
        self.importer = importer

    def set_default_importer(self, nautobot_name: FieldName) -> None:
        """Set default field importer."""
        self.set_nautobot_field(nautobot_name)
        if self.internal_type == "None":
            return

        if self.internal_type == "Property":
            self.set_property_importer()
        elif self.internal_type == "CustomFieldData":
            self.set_property_importer()
        elif self.internal_type == "JSONField":
            self.set_json_importer()
        elif self.internal_type == "DateField":
            self.set_date_importer()
        elif self.internal_type == "DateTimeField":
            self.set_datetime_importer()
        elif self.internal_type == "ManyToManyField":
            self.set_m2m_importer()
        elif self.internal_type == "StatusField":
            self.set_status_importer()
        elif self.internal_type == "GenericForeignKey":
            self.set_generic_relation_importer()
        elif self.internal_type in REFERENCE_INTERNAL_TYPES:
            self.set_relation_importer()
        elif self.internal_type in INTEGER_INTERNAL_TYPES:
            self.set_integer_importer()
        else:
            self.set_field_importer()

    def set_property_importer(self) -> None:
        """Set a property importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            value = source.get(self.name, None)
            if value not in EMPTY_VALUES:
                target[self.nautobot_name] = value

        self.set_importer(importer)

    def set_role_importer(self, role_wrapper: "SourceModelWrapper") -> None:
        """Set a role field importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            value = source.get(self.name, None)
            if value in EMPTY_VALUES:
                return

            uuid = role_wrapper.get_pk_from_uid(value)  # type: ignore
            target[self.nautobot_name] = uuid
            role_wrapper.add_reference(uuid, self.wrapper)

        self.set_nautobot_field("role")
        self.set_importer(importer)

    def set_json_importer(self) -> None:
        """Set a JSON field importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            value = source.get(self.name, None)
            if value in EMPTY_VALUES:
                return

            if isinstance(value, str):
                value = json.loads(value)

            target[self.nautobot_name] = value

        self.set_importer(importer)

    def set_integer_importer(self) -> None:
        """Set an integer field importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            value = self.get_source_value(source)
            if value in EMPTY_VALUES:
                return

            float_value = float(value)
            if not float_value.is_integer():
                raise ValueError(f"Invalid value {value} for field {self}")

            target[self.nautobot_name] = int(float_value)

        self.set_importer(importer)

    def set_field_importer(self) -> None:
        """Set a field importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            value = self.get_source_value(source)
            if value not in EMPTY_VALUES:
                target[self.nautobot_name] = value

        self.set_importer(importer)

    def set_generic_relation_importer(self) -> None:
        """Set a generic relation importer."""
        # TBD: Consider storing the content_type and related id in separate fields for ImporterModel
        type_name = f"{self.name}_type"
        id_name = f"{self.name}_id"
        self.wrapper.add_field(type_name, None)
        self.wrapper.add_field(id_name, None)

        def importer(source: RecordData, target: RecordData) -> None:
            content_type = source.get(type_name, None)
            if not content_type:
                return

            related_wrapper = self.wrapper.adapter.get_or_create_wrapper(content_type)

            value = source.get(id_name, None)
            if value is None:
                raise ValueError(f"Missing {id_name} for {type_name} {related_wrapper.content_type}")

            result = related_wrapper.get_pk_from_identifiers(value)
            target[self.nautobot_name] = (related_wrapper.content_type, result)
            related_wrapper.add_reference(result, self.wrapper)

        self.set_importer(importer)

    def set_relation_importer(self) -> None:
        """Set a relation importer."""
        if isinstance(self.django_field, DjangoField):
            related_wrapper = self.wrapper.adapter.get_or_create_wrapper(self.django_field.related_model)

            if related_wrapper.nautobot.pk_type == "UUIDField":
                return self.set_uuid_importer(related_wrapper)

            if related_wrapper.content_type == "contenttypes.contenttype":
                return self.set_content_type_importer()

        raise NotImplementedError(f"Unsupported relation importer {self}")

    def set_content_type_importer(self) -> None:
        """Set a content type importer."""
        adapter = self.wrapper.adapter

        def importer(source: RecordData, target: RecordData) -> None:
            content_type = source.get(self.name, None)
            if content_type:
                target[self.nautobot_name] = adapter.get_nautobot_content_type_instance(content_type).pk

        self.set_importer(importer)

    def set_uuid_importer(self, related_wrapper: SourceModelWrapper) -> None:
        """Set a UUID importer."""
        if self.default_value in EMPTY_VALUES and related_wrapper.default_reference_uid:
            self.default_value = related_wrapper.default_reference_uid

        if not (self.default_value is None or isinstance(self.default_value, UUID)):
            raise NotImplementedError(f"Default value {self.default_value} is not a UUID")

        def importer(source: RecordData, target: RecordData) -> None:
            value = self.get_source_value(source)
            if value in EMPTY_VALUES:
                return

            if isinstance(value, (UUID, str, int)):
                result = related_wrapper.get_pk_from_uid(value)
            else:
                result = related_wrapper.get_pk_from_identifiers(value)
            target[self.nautobot_name] = result
            related_wrapper.add_reference(result, self.wrapper)

        self.set_importer(importer)

    def set_m2m_importer(self) -> None:
        """Set a many to many importer."""
        if not isinstance(self.django_field, DjangoField):
            raise NotImplementedError(f"Unsupported m2m importer {self}")

        related_wrapper = self.wrapper.adapter.get_or_create_wrapper(self.django_field.related_model)

        if related_wrapper.content_type == "contenttypes.contenttype":
            self.set_content_types_importer()
        elif related_wrapper.identifiers is not ONLY_ID_IDENTIFIERS:
            self.set_identifiers_importer(related_wrapper)
        else:
            self.set_uuids_importer(related_wrapper)

    def set_identifiers_importer(self, related_wrapper: SourceModelWrapper) -> None:
        """Set a identifiers importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            values = source.get(self.name, None)
            if values in EMPTY_VALUES:
                return

            if not isinstance(values, (list, set)):
                raise ValueError(f"Invalid value {values} for field {self.name}")

            target[self.nautobot_name] = set(related_wrapper.get_pk_from_identifiers(item) for item in values)

        self.set_importer(importer)

    def set_content_types_importer(self) -> None:
        """Set a content types importer."""
        adapter = self.wrapper.adapter

        def importer(source: RecordData, target: RecordData) -> None:
            values = source.get(self.name, None)
            if values in EMPTY_VALUES:
                return

            if not isinstance(values, (list, set)):
                raise ValueError(f"Invalid value {values} for field {self.name}")

            target[self.nautobot_name] = set(adapter.get_nautobot_content_type_instance(item).pk for item in values)

        self.set_importer(importer)

    def set_uuids_importer(self, related_wrapper: SourceModelWrapper) -> None:
        """Set a UUIDs importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            value = source.get(self.name, None)
            if value in EMPTY_VALUES:
                return

            if isinstance(value, (UUID, str, int)):
                target[self.nautobot_name] = {related_wrapper.get_pk_from_uid(value)}
            elif isinstance(value, (list, set, tuple)):
                target[self.nautobot_name] = set(related_wrapper.get_pk_from_uid(item) for item in value)
            else:
                raise ValueError(f"Invalid value {value} for field {self.name}")

        self.set_importer(importer)

    def set_datetime_importer(self) -> None:
        """Set a datetime importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            value = source.get(self.name, None)
            if value in EMPTY_VALUES:
                return

            if not isinstance(value, datetime.datetime):
                value = datetime_parser.isoparse(str(value))

            target[self.nautobot_name] = value

        self.set_importer(importer)

    def set_date_importer(self) -> None:
        """Set a date importer."""

        def importer(source: RecordData, target: RecordData) -> None:
            value = source.get(self.name, None)
            if value in EMPTY_VALUES:
                return

            if not isinstance(value, datetime.date):
                value = datetime.date.fromisoformat(str(value))

            target[self.nautobot_name] = value

        self.set_importer(importer)

    def set_status_importer(self) -> None:
        """Set a status importer."""
        status_wrapper = self.wrapper.adapter.get_or_create_wrapper("extras.status")
        if not self.default_value:
            self.default_value = status_wrapper.default_reference_uid

        if not (self.default_value is None or isinstance(self.default_value, UUID)):
            raise NotImplementedError(f"Default value {self.default_value} is not a UUID")

        def importer(source: RecordData, target: RecordData) -> None:
            status = source.get(self.name, None)
            if status:
                value = status_wrapper.cache_data({"name": status[0].upper() + status[1:]})
            else:
                value = self.default_value
                if not value:
                    return

            target[self.nautobot_name] = value
            status_wrapper.add_reference(value, self.wrapper)

        self.set_importer(importer)
