"""Nautobot DiffSync Importer."""
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Mapping
from typing import MutableMapping
from typing import NamedTuple
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from uuid import UUID

from diffsync import DiffSyncModel
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Max
from nautobot.core.utils.lookup import get_model_from_name

from .base import EMPTY_VALUES
from .base import INTERNAL_TYPE_TO_ANNOTATION
from .base import REFERENCE_INTERNAL_TYPES
from .base import BaseAdapter
from .base import ContentTypeStr
from .base import DjangoFieldDoesNotExist
from .base import DjangoModelMeta
from .base import FieldName
from .base import GenericForeignKey
from .base import GenericForeignValue
from .base import InternalFieldTypeStr
from .base import NautobotBaseModel
from .base import NautobotBaseModelType
from .base import NautobotField
from .base import PydanticField
from .base import RecordData
from .base import Uid
from .base import logger
from .base import normalize_datetime

# Helper to determine the import order of models.
# Due to dependencies among Nautobot models, certain models must be imported first to ensure successful `instance.save()` calls without errors.
# Models listed here take precedence over others, which are sorted by the order they're introduced to the importer.
# Models listed, but not imported, here will be ignored.
# Obsoleted models can be kept here to ensure backward compatibility.
IMPORT_ORDER: Iterable[ContentTypeStr] = (
    "extras.customfield",
    "extras.customfieldchoice",
    "extras.status",
    "extras.role",
    "dcim.locationtype",
    "dcim.location",
    "tenancy.tenantgroup",
    "tenancy.tenant",
    "users.user",
    "circuits.circuit",
    "circuits.circuittermination",
    "circuits.circuittype",
    "circuits.provider",
    "circuits.providernetwork",
    "dcim.devicetype",
    "dcim.consoleport",
    "dcim.consoleporttemplate",
    "dcim.device",
    "dcim.devicebay",
    "dcim.frontport",
    "dcim.frontporttemplate",
    "dcim.interface",
    "dcim.interfacetemplate",
    "dcim.powerfeed",
    "dcim.poweroutlet",
    "dcim.poweroutlettemplate",
    "dcim.powerpanel",
    "dcim.powerport",
    "dcim.powerporttemplate",
    "dcim.rack",
    "dcim.rearport",
    "dcim.rearporttemplate",
    "dcim.cable",
    "ipam.prefix",
)


class NautobotAdapter(BaseAdapter):
    """Nautobot DiffSync Adapter."""

    def __init__(self, *args, **kwargs):
        """Initialize the adapter."""
        super().__init__("Nautobot", *args, **kwargs)
        self._validation_errors: Optional[Dict[ContentTypeStr, Set[ValidationError]]] = None
        self.wrappers: Dict[ContentTypeStr, NautobotModelWrapper] = {}

    @property
    def validation_errors(self) -> Dict[ContentTypeStr, Set[ValidationError]]:
        """Re-run clean() on all instances that failed validation."""
        if self._validation_errors is not None:
            return self._validation_errors

        self._validation_errors = {}
        for wrapper in self.wrappers.values():
            for uid in wrapper.get_clean_failures():
                instance = wrapper.model.objects.get(pk=uid)
                try:
                    instance.clean()
                except ValidationError as error:
                    self._validation_errors.setdefault(wrapper.content_type, set()).add(error)

        return self._validation_errors

    def get_or_create_wrapper(self, content_type: ContentTypeStr) -> "NautobotModelWrapper":
        """Get or create a Nautobot model wrapper."""
        if content_type in self.wrappers:
            return self.wrappers[content_type]

        nautobot_wrapper = NautobotModelWrapper(content_type)
        self.wrappers[content_type] = nautobot_wrapper
        return nautobot_wrapper


class NautobotFieldWrapper(NamedTuple):
    """Wrapper for a Nautobot field."""

    name: FieldName
    internal_type: InternalFieldTypeStr
    field: Optional[NautobotField] = None


NautobotFields = MutableMapping[FieldName, NautobotFieldWrapper]


# pylint: disable=too-many-instance-attributes
class NautobotModelWrapper:
    """Wrapper for a Nautobot model."""

    def __init__(self, content_type: ContentTypeStr):
        """Initialize the wrapper."""
        self._content_type_instance = None
        self.content_type = content_type
        try:
            self._model = get_model_from_name(content_type)
            self.disabled = False
        except TypeError:
            self.disabled = True

        self.fields: NautobotFields = {}
        self.importer: Optional[Type[ImporterModel]] = None
        self._clean_failures: Set[Uid] = set()

        self.last_id = 0

        if self.disabled:
            logger.warning("Skipping unknown model %s", content_type)
            self._pk_field = None
        else:
            self._pk_field = self.add_field(self.model_meta.pk.name)  # type: ignore
            if not self._pk_field:
                raise ValueError(f"Missing pk field for {self.content_type}")

            if self._pk_field.internal_type == "AutoField":
                self.last_id = (
                    self.model.objects.aggregate(Max(self._pk_field.name))[f"{self._pk_field.name}__max"] or 0
                )

        self.constructor_kwargs: Dict[FieldName, Any] = {}
        self.imported_count = 0

    @property
    def pk_field(self) -> NautobotFieldWrapper:
        """Get the pk field."""
        if not self._pk_field:
            raise ValueError(f"Missing pk field for {self.content_type}")
        return self._pk_field

    def get_clean_failures(self) -> Set[Uid]:
        """Get the set of instances that failed to clean."""
        failures = self._clean_failures
        self._clean_failures = set()
        return failures

    @property
    def model(self) -> NautobotBaseModelType:
        """Get the Nautobot model."""
        if self.disabled:
            raise NotImplementedError("Cannot use disabled model")

        return self._model

    @property
    def model_meta(self) -> DjangoModelMeta:
        """Get the Nautobot model meta."""
        return self.model._meta  # type: ignore

    def get_importer(self) -> Type["ImporterModel"]:
        """Get the DiffSync model for this wrapper."""
        if self.importer:
            return self.importer

        annotations = {}
        attributes = []
        identifiers = []

        class_definition = {
            "__annotations__": annotations,
            "_attributes": attributes,
            "_identifiers": identifiers,
            "_modelname": self.content_type.replace(".", "_"),
            "_wrapper": self,
        }

        annotations[self.pk_field.name] = INTERNAL_TYPE_TO_ANNOTATION[self.pk_field.internal_type]
        identifiers.append(self.pk_field.name)
        class_definition[self.pk_field.name] = PydanticField()

        for field in self.fields.values():
            if field.name in identifiers:
                continue
            if field.internal_type == "GenericForeignKey":
                annotation = Tuple[ContentTypeStr, UUID]
            elif field.internal_type in REFERENCE_INTERNAL_TYPES:
                related_model = getattr(field.field, "related_model")
                if not related_model:
                    raise ValueError(f"Missing related model for field {field.name}")
                referenced_internal_type = related_model._meta.pk.get_internal_type()
                annotation = INTERNAL_TYPE_TO_ANNOTATION[referenced_internal_type]
                if field.internal_type == "ManyToManyField":
                    annotation = Set[annotation]
            else:
                annotation = INTERNAL_TYPE_TO_ANNOTATION[field.internal_type]

            attributes.append(field.name)
            annotations[field.name] = Optional[annotation]
            class_definition[field.name] = PydanticField(default=None)

        logger.debug("Creating model %s", class_definition)
        try:
            self.importer = type(class_definition["_modelname"], (ImporterModel,), class_definition)
        except Exception:
            logger.error("Failed to create model %s", class_definition, exc_info=True)
            raise

        return self.importer

    def _field_from_name(self, field_name: FieldName) -> Optional[NautobotFieldWrapper]:
        meta = self.model_meta

        if field_name == "custom_field_data":
            return NautobotFieldWrapper(field_name, "CustomFieldData", meta.get_field("_custom_field_data"))

        try:
            field = meta.get_field(field_name)
        except DjangoFieldDoesNotExist:
            if not hasattr(self.model, field_name):
                return None
            return NautobotFieldWrapper(field_name, "Property")

        if isinstance(field, GenericForeignKey):
            # GenericForeignKey is not a real field, doesn't have `get_internal_type` method
            return NautobotFieldWrapper(field_name, "GenericForeignKey", field)

        if not hasattr(field, "get_internal_type"):
            raise NotImplementedError(f"Unsupported field type {self.content_type} {field_name}")

        internal_type = field.get_internal_type()
        if internal_type in REFERENCE_INTERNAL_TYPES and internal_type != "ManyToManyField":
            # Reference fields are converted to id fields
            return NautobotFieldWrapper(f"{field_name}_id", internal_type, field)
        return NautobotFieldWrapper(field_name, internal_type, field)

    def add_field(self, field_name: FieldName) -> Optional[NautobotFieldWrapper]:
        """Add a field to the model."""
        if self.importer:
            raise RuntimeError("Cannot add fields after the importer has been created")

        field = self._field_from_name(field_name)
        if not field:
            return None

        if field.name in self.fields:
            existing_field = self.fields[field.name]
            if existing_field.internal_type != field.internal_type:
                raise ValueError(f"Field {field.name} already exists with different type {self.fields[field.name]}")
            return existing_field

        logger.debug("Adding nautobot field %s %s %s", self.content_type, field.name, field.internal_type)
        self.fields[field.name] = field
        return field

    @property
    def content_type_instance(self) -> ContentType:
        """Get the Nautobot content type instance for a given content type."""
        if not self._content_type_instance:
            self._content_type_instance = ContentType.objects.get_for_model(self.model)
        return self._content_type_instance

    def set_instance_defaults(self, **defaults: Any) -> None:
        """Set default values for a Nautobot instance constructor."""
        self.constructor_kwargs = defaults

    def get_data_from_instance(self, instance: NautobotBaseModel) -> RecordData:
        """Get the data for a Nautobot instance."""
        # pylint: disable=too-many-return-statements
        def get_value(field_name, internal_type) -> Any:
            value = getattr(instance, field_name, None)
            if value in EMPTY_VALUES:
                return None
            if internal_type == "GenericForeignKey":
                return (value._meta.label.lower(), value.pk)  # type: ignore
            if internal_type == "ManyToManyField":
                return set(item.pk for item in value.all()) or None  # type: ignore
            if internal_type == "Property":
                return str(value)
            if internal_type == "CustomFieldData":
                return value
            if internal_type == "DateTimeField":
                return normalize_datetime(value)
            return value

        result = {field.name: get_value(field.name, field.internal_type) for field in self.fields.values()}
        result[self.pk_field.name] = instance.pk
        return result

    # pylint: disable=too-many-statements,too-many-branches
    def save_nautobot_instance(self, instance: NautobotBaseModel, values: RecordData) -> None:
        """Save a Nautobot instance."""

        def set_custom_field_data(value: Optional[Mapping]):
            custom_field_data = getattr(instance, "custom_field_data", None)
            if custom_field_data is None:
                raise TypeError("Missing custom_field_data")
            custom_field_data.clear()
            if value:
                custom_field_data.update(value)

        def set_generic_foreign_key(field, value: Optional[GenericForeignValue]):
            if not isinstance(field, GenericForeignKey):
                raise TypeError(f"Invalid field type {field}")

            if value:
                foreign_model = get_model_from_name(value[0])
                setattr(instance, field.ct_field, ContentType.objects.get_for_model(foreign_model))
                setattr(instance, field.fk_field, value[1])
            else:
                setattr(instance, field.fk_field, None)
                setattr(instance, field.ct_field, None)

        def set_empty(field, field_name: FieldName):
            if field.blank and not field.null:
                setattr(instance, field_name, "")
            else:
                setattr(instance, field_name, None)

        m2m_fields = set()

        for field_name, value in values.items():
            field_wrapper = self.fields[field_name]
            if field_wrapper.internal_type == "ManyToManyField":
                m2m_fields.add(field_name)
            elif field_wrapper.internal_type == "CustomFieldData":
                set_custom_field_data(value)
            elif field_wrapper.internal_type == "Property":
                setattr(instance, field_name, value)
            elif field_wrapper.internal_type == "GenericForeignKey":
                set_generic_foreign_key(field_wrapper.field, value)
            elif value in EMPTY_VALUES:
                set_empty(field_wrapper.field, field_name)
            else:
                setattr(instance, field_name, value)

        try:
            instance.save()
        except Exception:
            logger.error("Save failed: %s %s", instance, instance.__dict__, exc_info=True)
            raise

        for field_name in m2m_fields:
            field = getattr(instance, field_name)
            value = values[field_name]
            if value:
                field.set(value)
            else:
                field.clear()

        try:
            instance.clean()
        # `clean()` can be called again by getting `validation_errors` property after importing all data
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            uid = instance.pk
            if not isinstance(uid, (UUID, str, int)):
                raise TypeError(f"Invalid uid {uid}") from exc
            self._clean_failures.add(uid)


class ImporterModel(DiffSyncModel):
    """Base class for all DiffSync models."""

    _wrapper: NautobotModelWrapper

    @classmethod
    def create(cls, diffsync: BaseAdapter, ids: dict, attrs: dict) -> Optional[DiffSyncModel]:
        """Create this model instance, both in Nautobot and in DiffSync."""
        instance = cls._wrapper.model(**cls._wrapper.constructor_kwargs, **ids)

        # Created needs to be set after saving the instance
        created = attrs.pop("created", None)
        cls._wrapper.save_nautobot_instance(instance, attrs)
        if created:
            setattr(instance, "created", created)
            instance.save()

        return super().create(diffsync, ids, attrs)

    def update(self, attrs: dict) -> Optional[DiffSyncModel]:
        """Update this model instance, both in Nautobot and in DiffSync."""
        uid = getattr(self, self._wrapper.pk_field.name, None)
        if not uid:
            raise NotImplementedError("Cannot update model without pk")

        model = self._wrapper.model
        instance = model.objects.get(pk=uid)
        # Sync "created" only on create
        attrs.pop("created", None)
        self._wrapper.save_nautobot_instance(instance, attrs)

        return super().update(attrs)
