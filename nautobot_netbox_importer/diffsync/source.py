"""Generic Nautobot DiffSync Importer."""
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
from typing import NamedTuple
from typing import Optional
from typing import OrderedDict
from typing import Set
from typing import Tuple
from typing import Union
from uuid import UUID

from diffsync.exceptions import ObjectNotFound as DiffSyncObjectNotFound
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
from .base import get_content_type_id
from .base import get_internal_field_type
from .base import get_source_value
from .base import logger
from .base import source_pk_to_uuid
from .nautobot import IMPORT_ORDER
from .nautobot import ImporterModel
from .nautobot import NautobotAdapter
from .nautobot import NautobotModelWrapper
from .nautobot import get_nautobot_instance_data


class SourceRecord(NamedTuple):
    """Source Data Item."""

    content_type: ContentTypeStr
    data: RecordData


SourceDataGenerator = Callable[[], Iterable[SourceRecord]]
SourceFieldImporter = Callable[[RecordData, RecordData], None]
SourceFieldImporterFactory = Callable[["SourceModelWrapper", FieldName], None]
SourceFieldDefinition = Union[
    None,  # Ignore field
    FieldName,  # Rename field
    SourceFieldImporterFactory,  # Field importer factory
]


class AddFieldDuplicity(Enum):
    """Add field duplicity."""

    IGNORE = auto()
    REPLACE = auto()
    FAIL = auto()


class ReferencesForwarding(NamedTuple):
    """Forward references to another model."""

    content_type: ContentTypeStr
    field_name: FieldName


# pylint: disable=too-many-instance-attributes
class SourceModelWrapper:
    """Definition of a source model mapping to Nautobot model."""

    def __init__(self, adapter: "SourceAdapter", content_type: ContentTypeStr, nautobot_wrapper: NautobotModelWrapper):
        """Initialize the SourceModelWrapper."""
        if content_type in adapter.wrappers:
            raise ValueError(f"Duplicate content type {content_type}")

        adapter.not_initialized_wrappers.add(self)
        adapter.wrappers[content_type] = self

        self.adapter = adapter
        self.content_type = content_type
        self.importers: List[SourceFieldImporter] = []
        self.references: Dict[Uid, Set[SourceModelWrapper]] = {}
        self.uid_to_pk_cache: Dict[Uid, Uid] = {}
        self.cached_data: Dict[Uid, RecordData] = {}
        self.references_forwarding: Optional[ReferencesForwarding] = None
        self.imported_count = 0
        self.identifiers = ONLY_ID_IDENTIFIERS

        self.default_reference_pk: Optional[Uid] = None

        self.nautobot = nautobot_wrapper

        self.can_add_fields = True
        self.fields: Dict[FieldName, SourceFieldDefinition] = {}
        self.add_field(self.nautobot.pk_name, None, duplicity=AddFieldDuplicity.FAIL)

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
        """Set references forwarding to another model."""
        self.references_forwarding = ReferencesForwarding(content_type, field_name)

    def set_fields(self, *field_names: FieldName, **fields: SourceFieldDefinition) -> None:
        """Set fields definitions."""
        for field_name in field_names:
            self.add_field(field_name, field_name, duplicity=AddFieldDuplicity.REPLACE)
        for field_name, definition in fields.items():
            self.add_field(field_name, definition, duplicity=AddFieldDuplicity.REPLACE)

    def add_field(self, name: FieldName, definition: SourceFieldDefinition, duplicity=AddFieldDuplicity.FAIL) -> None:
        """Add a field definition for a source field."""
        if name in self.fields or name in self.nautobot.ignored_fields:
            if duplicity == AddFieldDuplicity.IGNORE:
                return
            if duplicity == AddFieldDuplicity.FAIL:
                raise ValueError(f"Duplicate field {name}")
            if duplicity != AddFieldDuplicity.REPLACE:
                raise NotImplementedError(f"Unsupported duplicity {duplicity}")

        if not self.can_add_fields:
            if definition is None:
                self.nautobot.ignore_fields(name)
                return
            raise ValueError(f"Can't add field {name} to {self.content_type}, it's already imported")

        print(f"Adding field {self.content_type} {name} {definition}")
        if definition is None:
            logger.warning("Skipping field %s %s", self.content_type, name)
        else:
            logger.debug("Adding field %s %s %s", self.content_type, name, definition)
        self.fields[name] = definition

    def add_role_importer(self, source_name: FieldName, role_wrapper: "SourceModelWrapper") -> None:
        """Add a field definition for a role field."""
        nautobot_name = "role_id"

        def importer(source: RecordData, target: RecordData) -> None:
            value = source.get(source_name, None)
            if value in EMPTY_VALUES:
                return

            if value:
                uuid = role_wrapper.get_pk_from_uid(value)
                target[nautobot_name] = uuid
                role_wrapper.add_reference(uuid, self)
            else:
                raise ValueError(f"Invalid value {value} for field {source_name}")

        self.add_importer(importer, nautobot_name, "RoleField")

    def create_importers(self) -> None:
        """Create importers for all fields."""
        self.can_add_fields = False
        for field_name, definition in self.fields.items():
            if definition is None:
                continue

            if isinstance(definition, FieldName):
                try:
                    self.add_default_importer(field_name, definition)
                except Exception:
                    logger.error("Failed to create importer for %s %s", self.content_type, field_name)
                    raise
                continue

            if callable(definition):
                try:
                    definition(self, field_name)
                except Exception:
                    logger.error("Failed to create importer for %s %s", self.content_type, field_name)
                    raise
                continue

            raise NotImplementedError(f"Unsupported field definition {definition}")

    def add_importer(
        self,
        definition: SourceFieldImporter,
        nautobot_field: Optional[FieldName] = None,
        field_type: Optional[InternalFieldTypeStr] = None,
    ) -> None:
        """Add a field importer."""
        self.importers.append(definition)
        if nautobot_field:
            if not field_type:
                raise ValueError("Missing field_type")
            self.nautobot.add_field(nautobot_field, field_type)

    def get_pk_from_uid(self, uid: Uid) -> Uid:
        """Get a source primary key for a given source uid."""
        if uid in self.uid_to_pk_cache:
            return self.uid_to_pk_cache[uid]
        if self.nautobot.pk_type == "UUIDField":
            return source_pk_to_uuid(self.content_type, uid)

        if self.nautobot.pk_type == "AutoField":
            self.nautobot.last_id += 1
            result = self.nautobot.last_id
        else:
            raise ValueError(f"Unsupported pk_type {self.nautobot.pk_type}")

        self.uid_to_pk_cache[uid] = result
        return result

    def get_pk_from_identifiers(self, data: Union[Uid, Iterable[Uid]]) -> Uid:
        """Get a source primary key for a given source identifiers."""
        if self.identifiers is ONLY_ID_IDENTIFIERS:
            if not isinstance(data, Uid):
                raise ValueError(f"Invalid identifiers {data} for {self.identifiers}")
            return self.get_pk_from_uid(data)

        if not isinstance(data, list):
            data = list(data)  # type: ignore
        if len(self.identifiers) != len(data):
            raise ValueError(f"Invalid identifiers {data} for {self.identifiers}")

        uid = json.dumps(data)
        if uid in self.uid_to_pk_cache:
            return self.uid_to_pk_cache[uid]

        filter_kwargs = {self.identifiers[index]: value for index, value in enumerate(data)}
        try:
            nautobot_instance = self.nautobot.model.objects.get(**filter_kwargs)
            self.cached_data[uid] = get_nautobot_instance_data(nautobot_instance, self.nautobot.fields)
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
        # print(f"Importing item {self.content_type} {uid} {data}")
        instance = self.adapter.get_or_none(importer_model, {"id": uid})

        target_data = {}
        if uid:
            target_data["id"] = uid

        for importer in self.importers:
            importer(data, target_data)

        for field_name in self.nautobot.ignored_fields:
            if field_name in target_data:
                del target_data[field_name]

        # print(f"Importing as {target_data}")

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

    def get_type_and_field(self, target_name: FieldName) -> Tuple[InternalFieldTypeStr, Optional[DjangoField]]:
        """Get a field type and field for a given target field name."""
        meta = self.nautobot.model._meta

        if target_name == "custom_field_data":
            return "CustomFieldData", meta.get_field("_custom_field_data")

        try:
            field = meta.get_field(target_name)
        except DjangoFieldDoesNotExist:
            return "Any", None

        return get_internal_field_type(field), field

    def add_default_importer(self, source_name: FieldName, nautobot_name: FieldName) -> None:
        """Add a default importer for a given source field."""
        internal_type, nautobot_field = self.get_type_and_field(nautobot_name)

        if not nautobot_field:
            importer = _property_importer_factory(source_name, nautobot_name)
        elif internal_type == "CustomFieldData":
            importer = _property_importer_factory(source_name, nautobot_name)
        elif internal_type == "JSONField":
            importer = _json_importer_factory(source_name, nautobot_name)
        elif internal_type == "DateField":
            importer = _date_importer_factory(source_name, nautobot_name)
        elif internal_type == "DateTimeField":
            importer = _datetime_importer_factory(source_name, nautobot_name)
        elif internal_type == "ManyToManyField":
            importer = _m2m_importer_factory(self, nautobot_field, source_name, nautobot_name)
        elif internal_type == "StatusField":
            nautobot_name = f"{nautobot_name}_id"
            importer = _status_importer_factory(self, nautobot_field, source_name, nautobot_name)
        elif internal_type == "GenericForeignKey":
            importer = _generic_relation_importer_factory(self, source_name, nautobot_name)
        elif internal_type in REFERENCE_INTERNAL_TYPES:
            nautobot_name = f"{nautobot_name}_id"
            importer = _relation_importer_factory(self, nautobot_field, source_name, nautobot_name)
        elif internal_type in INTEGER_INTERNAL_TYPES:
            importer = _integer_importer_factory(nautobot_field, source_name, nautobot_name)
        else:
            importer = _field_importer_factory(nautobot_field, source_name, nautobot_name)

        self.add_importer(importer, nautobot_name, internal_type)

    def get(self, uid: Uid) -> ImporterModel:
        """Get a single item from the source."""
        try:
            result = self.adapter.get(self.nautobot.get_importer(), {"id": uid})
            if not isinstance(result, ImporterModel):
                raise TypeError(f"Invalid result type {result}")
            return result
        except DiffSyncObjectNotFound:
            if uid in self.cached_data:
                return self.import_record(self.cached_data[uid])
            raise

    def get_default_reference_pk(self) -> Uid:
        """Get the default reference to this model."""
        if self.default_reference_pk:
            return self.default_reference_pk
        raise ValueError("Missing default reference")

    def cache_data(self, data: RecordData) -> Uid:
        """Cache data for optional later use.

        If `data` are referenced by other models, they will be imported automatically, otherwise they will be ignored.
        """
        for field_name in data.keys():
            self.add_field(field_name, field_name, AddFieldDuplicity.IGNORE)

        uid = self.get_pk_from_data(data)
        self.cached_data[uid] = data
        return uid

    def set_default_reference(self, **data: Any) -> None:
        """Set the default reference to this model."""
        self.default_reference_pk = self.cache_data(data)

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

            content_types = set(wrapper.nautobot.get_content_type().id for wrapper in content_types)  # type: ignore
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


class SourceAdapter(BaseAdapter):
    """Source DiffSync Adapter."""

    def __init__(self, name: str, *args, **kwargs):
        """Initialize the SourceAdapter."""
        super().__init__(name, *args, **kwargs)

        self.wrappers: OrderedDict[ContentTypeStr, SourceModelWrapper] = OrderedDict()
        self.not_initialized_wrappers: Set[SourceModelWrapper] = set()
        self.ignored_fields: Set[FieldName] = set()
        self.ignored_models: Set[ContentTypeStr] = set()
        self.content_type_back_mapping: Dict[ContentTypeStr, Optional[ContentTypeStr]] = {}

    def print_summary(self, validation_errors) -> None:
        """Print a summary of the import."""
        print("= Summary ======================================")

        for wrapper in self.get_imported_nautobot_wrappers():
            print(f"  {wrapper.content_type}: {wrapper.imported_count}")

        if validation_errors:
            print("- Validation errors: ---------------------------")
            for model_type, errors in validation_errors.items():
                print(f"  {model_type}: {len(errors)}")
                for error in errors:
                    print(f"    {error}")
            print("Total validation errors:", len(validation_errors))
        else:
            print("- No validation errors ------------------------")

        print("================================================")

    def ignore_fields(self, *field_names: FieldName) -> None:
        """Skip fields during import."""
        self.ignored_fields.update(field_names)

    def get_or_create_wrapper(
        self,
        value: Union[None, ContentTypeValue, SourceModelWrapper, NautobotModelWrapper, NautobotBaseModelType],
        map_back: bool = False,
    ) -> SourceModelWrapper:
        """Get a source Wrapper for a given content type."""
        if not value:
            raise ValueError("Missing value")

        if isinstance(value, SourceModelWrapper):
            return value

        if isinstance(value, type(NautobotBaseModel)):
            value = value._meta.label.lower()  # type: ignore
        elif isinstance(value, NautobotModelWrapper):
            value = value.content_type

        if isinstance(value, str):
            pass
        elif isinstance(value, int):
            raise NotImplementedError("Integer content type")
        elif isinstance(value, Iterable) and len(value) == 2:
            value = ".".join(value)
        else:
            raise ValueError(f"Invalid content type {value}")

        if map_back and value in self.content_type_back_mapping:
            back_mapping = self.content_type_back_mapping.get(value, None)
            if not back_mapping:
                raise ValueError(f"Unambiguous content type back mapping {value}")
            value = back_mapping

        if value in self.wrappers:
            return self.wrappers[value]

        return self.define_model(value)

    def ignore_models(self, *content_types: ContentTypeStr) -> None:
        """Disable import of a source model."""
        for content_type in content_types:
            self.ignored_models.add(content_type)

    def define_model(
        self,
        content_type: ContentTypeStr,
        nautobot_content_type: Optional[ContentTypeStr] = None,
        identifiers: Optional[Iterable[FieldName]] = None,
    ) -> SourceModelWrapper:
        """Dynamically create a wrapper for a given source content type."""
        if not nautobot_content_type:
            nautobot_content_type = content_type

        if nautobot_content_type != content_type:
            if nautobot_content_type in self.content_type_back_mapping:
                self.content_type_back_mapping[content_type] = None
            else:
                self.content_type_back_mapping[nautobot_content_type] = content_type

        if nautobot_content_type in self.wrappers:
            nautobot_wrapper = self.wrappers[nautobot_content_type].nautobot
        elif nautobot_content_type != content_type:
            nautobot_wrapper = self.define_model(nautobot_content_type).nautobot
        else:
            nautobot_wrapper = NautobotModelWrapper(nautobot_content_type)

        wrapper = SourceModelWrapper(self, content_type, nautobot_wrapper)
        if identifiers:
            wrapper.set_identifiers(identifiers)

        return wrapper

    def import_data(self, get_source_data: SourceDataGenerator) -> None:
        """Import data from the source."""

        def create_structure(content_type: ContentTypeStr, data: RecordData):
            if content_type in self.ignored_models:
                return
            if content_type in self.wrappers:
                wrapper = self.wrappers[content_type]
                if wrapper is None:
                    return
            else:
                wrapper = self.define_model(content_type)

            for field_name in data.keys():
                if field_name in wrapper.fields:
                    continue
                if field_name.startswith("_") or field_name in self.ignored_fields:
                    wrapper.add_field(field_name, None, AddFieldDuplicity.FAIL)
                    continue
                wrapper.add_field(field_name, field_name, AddFieldDuplicity.FAIL)

        # First pass to create wrappers structure
        for content_type, data in get_source_data():
            create_structure(content_type, data)

        # Create importers and enhance structure
        while self.not_initialized_wrappers:
            wrapper = self.not_initialized_wrappers.pop()
            wrapper.create_importers()

        # Second pass to import actual data
        for content_type, data in get_source_data():
            if content_type in self.ignored_models:
                continue
            wrapper = self.wrappers.get(content_type, None)
            if wrapper:
                wrapper.import_record(data)

        # Post processing
        while any(wrapper.post_import() for wrapper in self.wrappers.values()):
            pass

    def import_nautobot(self) -> NautobotAdapter:
        """Import all Nautobot data."""
        nautobot = NautobotAdapter()

        for wrapper in self.get_imported_nautobot_wrappers():
            importer_model = wrapper.importer
            if not importer_model:
                raise TypeError(f"Missing importer_model for {wrapper.content_type}")

            for nautobot_instance in wrapper.model.objects.all():
                data = get_nautobot_instance_data(nautobot_instance, wrapper.fields)
                try:
                    instance = importer_model(**data, diffsync=nautobot)
                    nautobot.add(instance)
                except Exception:
                    logger.error("Failed to create instance %s", data, exc_info=True)
                    raise

            # pylint: disable=protected-access
            model_name = importer_model._modelname
            self.top_level.append(model_name)
            setattr(self, model_name, importer_model)
            setattr(nautobot, model_name, getattr(self, model_name))

        return nautobot

    def get_imported_nautobot_wrappers(self) -> Generator[NautobotModelWrapper, None, None]:
        """Get a list of Nautobot model wrappers in the order of import."""
        wrappers = OrderedDict()

        for wrapper in self.wrappers.values():
            if wrapper and wrapper.imported_count > 0 and wrapper.nautobot.content_type not in wrappers:
                wrappers[wrapper.nautobot.content_type] = wrapper.nautobot

        for content_type in IMPORT_ORDER:
            if content_type in wrappers:
                yield wrappers[content_type]
                del wrappers[content_type]

        yield from wrappers.values()


def _property_importer_factory(source_name: FieldName, nautobot_name: FieldName) -> SourceFieldImporter:
    def importer(source: RecordData, target: RecordData) -> None:
        value = source.get(source_name, None)
        if value not in EMPTY_VALUES:
            target[nautobot_name] = value

    return importer


def _integer_importer_factory(
    field: DjangoField,
    source_name: FieldName,
    nautobot_name: FieldName,
) -> SourceFieldImporter:
    default_value = None if field.default in EMPTY_VALUES else field.default

    def importer(source: RecordData, target: RecordData) -> None:
        value = get_source_value(source, source_name, default_value)
        if value in EMPTY_VALUES:
            return

        float_value = float(value)
        if not float_value.is_integer():
            raise ValueError(f"Invalid value {value} for field {source_name}")

        target[nautobot_name] = int(float_value)

    return importer


def _field_importer_factory(
    field: DjangoField,
    source_name: FieldName,
    nautobot_name: FieldName,
) -> SourceFieldImporter:
    default_value = None if field.default in EMPTY_VALUES else field.default

    def importer(source: RecordData, target: RecordData) -> None:
        value = get_source_value(source, source_name, default_value)
        if value not in EMPTY_VALUES:
            target[nautobot_name] = value

    return importer


def _generic_relation_importer_factory(
    wrapper: SourceModelWrapper,
    source_name: FieldName,
    nautobot_name: FieldName,
) -> SourceFieldImporter:
    # TBD: Consider storing the content_type and related id in separate fields for ImporterModel
    type_name = f"{source_name}_type"
    id_name = f"{source_name}_id"
    wrapper.nautobot.ignore_fields(type_name, id_name)

    def importer(source: RecordData, target: RecordData) -> None:
        content_type = source.get(type_name, None)
        if not content_type:
            return

        related_wrapper = wrapper.adapter.get_or_create_wrapper(content_type)

        value = source.get(id_name, None)
        if value is None:
            raise ValueError(f"Missing {id_name} for {type_name} {related_wrapper.content_type}")

        result = related_wrapper.get_pk_from_identifiers(value)
        target[nautobot_name] = (related_wrapper.content_type, result)
        related_wrapper.add_reference(result, wrapper)

    return importer


def _relation_importer_factory(
    wrapper: SourceModelWrapper,
    field: DjangoField,
    source_name: FieldName,
    nautobot_name: FieldName,
) -> SourceFieldImporter:
    related_wrapper = wrapper.adapter.get_or_create_wrapper(field.related_model, map_back=True)

    if related_wrapper.nautobot.pk_type == "UUIDField":
        return _uuid_importer_factory(wrapper, field, source_name, nautobot_name, related_wrapper)

    if related_wrapper.content_type == "contenttypes.contenttype":
        return _content_type_importer_factory(wrapper, source_name, nautobot_name)

    raise NotImplementedError(f"Unsupported relation importer {wrapper.content_type} field {field}")


def _content_type_importer_factory(
    wrapper: SourceModelWrapper,
    source_name: FieldName,
    nautobot_name: FieldName,
) -> SourceFieldImporter:
    def importer(source: RecordData, target: RecordData) -> None:
        content_type = source.get(source_name, None)
        if not content_type:
            return

        related_wrapper = wrapper.adapter.get_or_create_wrapper(content_type)
        target[nautobot_name] = related_wrapper.nautobot.get_content_type().id  # type: ignore

    return importer


def _uuid_importer_factory(
    wrapper: SourceModelWrapper,
    field: DjangoField,
    source_name: FieldName,
    nautobot_name: FieldName,
    related_wrapper: SourceModelWrapper,
) -> SourceFieldImporter:
    default_value = related_wrapper.default_reference_pk if field.default in EMPTY_VALUES else field.default

    if not (default_value is None or isinstance(default_value, UUID)):
        raise NotImplementedError(f"Default value {default_value} is not a UUID")

    def importer(source: RecordData, target: RecordData) -> None:
        value = get_source_value(source, source_name, default_value)
        if value in EMPTY_VALUES:
            return

        if isinstance(value, Uid):
            result = related_wrapper.get_pk_from_uid(value)
        else:
            result = related_wrapper.get_pk_from_identifiers(value)
        target[nautobot_name] = result
        related_wrapper.add_reference(result, wrapper)

    return importer


def _m2m_importer_factory(
    wrapper: SourceModelWrapper,
    field: DjangoField,
    source_name: FieldName,
    nautobot_name: FieldName,
) -> SourceFieldImporter:
    related_wrapper = wrapper.adapter.get_or_create_wrapper(field.related_model, map_back=True)

    if related_wrapper.content_type == "contenttypes.contenttype":
        return _content_types_importer_factory(source_name, nautobot_name)

    if related_wrapper.identifiers is not ONLY_ID_IDENTIFIERS:
        return _identifiers_importer_factory(related_wrapper, source_name, nautobot_name)

    return _uuids_importer_factory(source_name, nautobot_name, related_wrapper)


def _identifiers_importer_factory(
    related_wrapper: SourceModelWrapper,
    source_name: FieldName,
    nautobot_name: FieldName,
) -> SourceFieldImporter:
    def importer(source: RecordData, target: RecordData) -> None:
        values = source.get(source_name, None)
        if values in EMPTY_VALUES:
            return

        if not isinstance(values, (list, set)):
            raise ValueError(f"Invalid value {values} for field {source_name}")

        target[nautobot_name] = set(related_wrapper.get_pk_from_identifiers(item) for item in values)

    return importer


def _content_types_importer_factory(source_name: FieldName, nautobot_name: FieldName) -> SourceFieldImporter:
    def importer(source: RecordData, target: RecordData) -> None:
        values = source.get(source_name, None)
        if values in EMPTY_VALUES:
            return

        if not isinstance(values, (list, set)):
            raise ValueError(f"Invalid value {values} for field {source_name}")

        target[nautobot_name] = set(get_content_type_id(item) for item in values)

    return importer


def _uuids_importer_factory(
    source_name: FieldName,
    nautobot_name: FieldName,
    related_wrapper: SourceModelWrapper,
) -> SourceFieldImporter:
    def importer(source: RecordData, target: RecordData) -> None:
        value = source.get(source_name, None)
        if value in EMPTY_VALUES:
            return

        if isinstance(value, (UUID, str, int)):
            target[nautobot_name] = {related_wrapper.get_pk_from_uid(value)}
        elif isinstance(value, (list, set, tuple)):
            target[nautobot_name] = set(related_wrapper.get_pk_from_uid(item) for item in value)
        else:
            raise ValueError(f"Invalid value {value} for field {source_name}")

    return importer


def _datetime_importer_factory(source_name: FieldName, nautobot_name: FieldName) -> SourceFieldImporter:
    def importer(source: RecordData, target: RecordData) -> None:
        value = source.get(source_name, None)
        if value in EMPTY_VALUES:
            return

        if not isinstance(value, datetime.datetime):
            value = datetime.datetime.fromisoformat(str(value))

        target[nautobot_name] = value

    return importer


def _json_importer_factory(source_name: FieldName, nautobot_name: FieldName) -> SourceFieldImporter:
    def importer(source: RecordData, target: RecordData) -> None:
        value = source.get(source_name, None)
        if value in EMPTY_VALUES:
            return

        if isinstance(value, str):
            value = json.loads(value)

        target[nautobot_name] = value

    return importer


def _date_importer_factory(source_name: FieldName, nautobot_name: FieldName) -> SourceFieldImporter:
    def importer(source: RecordData, target: RecordData) -> None:
        value = source.get(source_name, None)
        if value in EMPTY_VALUES:
            return

        if not isinstance(value, datetime.date):
            value = datetime.date.fromisoformat(str(value))

        target[nautobot_name] = value

    return importer


def _status_importer_factory(
    wrapper: SourceModelWrapper,
    field: DjangoField,
    source_name: FieldName,
    nautobot_name: FieldName,
) -> SourceFieldImporter:
    status_wrapper = wrapper.adapter.get_or_create_wrapper("extras.status")
    default_value = status_wrapper.default_reference_pk if field.default in EMPTY_VALUES else field.default

    if not (default_value is None or isinstance(default_value, UUID)):
        raise NotImplementedError(f"Default value {default_value} is not a UUID")

    def importer(source: RecordData, target: RecordData) -> None:
        value = source.get(source_name, None)
        if not value:
            value = default_value
            if not value:
                return
            status_wrapper.add_reference(default_value, wrapper)  # type: ignore
        else:
            name = value[0].upper() + value[1:]
            value = status_wrapper.get_pk_from_identifiers([name])
            if value not in status_wrapper.cached_data:
                status_wrapper.cached_data[value] = {"name": name}

        target[nautobot_name] = value
        status_wrapper.add_reference(value, wrapper)

    return importer
