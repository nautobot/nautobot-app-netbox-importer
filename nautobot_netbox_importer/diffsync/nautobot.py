"""Nautobot DiffSync Importer."""

from typing import Any
from typing import Dict
from typing import Iterable
from typing import Mapping
from typing import MutableMapping
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from uuid import UUID

from diffsync import DiffSyncModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Max
from nautobot.core.utils.lookup import get_model_from_name
from pydantic import Field as PydanticField

from .base import EMPTY_VALUES
from .base import INTERNAL_TYPE_TO_ANNOTATION
from .base import REFERENCE_INTERNAL_TYPES
from .base import BaseAdapter
from .base import ContentTypeStr
from .base import FieldName
from .base import GenericForeignValue
from .base import InternalFieldTypeStr
from .base import NautobotBaseModel
from .base import RecordData
from .base import Uid
from .base import logger

NautobotFields = MutableMapping[FieldName, InternalFieldTypeStr]

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
                instance = wrapper.model.objects.get(id=uid)
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


# pylint: disable=too-many-instance-attributes
class NautobotModelWrapper:
    """Wrapper for a Nautobot model."""

    def __init__(self, content_type: ContentTypeStr):
        """Initialize the wrapper."""
        self._content_type_instance = None
        self.content_type = content_type
        self.model = get_model_from_name(content_type)
        self.fields: NautobotFields = {}
        self.importer: Optional[Type[ImporterModel]] = None
        self._clean_failures: Set[Uid] = set()

        pk_field = self.model._meta.pk
        self.pk_type = pk_field.get_internal_type()
        self.pk_name = pk_field.name
        if self.pk_name != "id":
            raise NotImplementedError("Primary key field must be named 'id'")
        self.add_field(self.pk_name, self.pk_type)

        if self.pk_type == "UUIDField":
            self.last_id = 0
        elif self.pk_type == "AutoField":
            self.last_id = self.model.objects.aggregate(Max("id"))["id__max"] or 0
        else:
            raise ValueError(f"Unsupported pk_type {self.pk_type}")

        self.constructor_kwargs: Dict[FieldName, Any] = {}
        self.imported_count = 0

    def get_clean_failures(self) -> Set[Uid]:
        """Get the set of instances that failed to clean."""
        failures = self._clean_failures
        self._clean_failures = set()
        return failures

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

        meta = self.model._meta
        if not meta.pk:
            raise NotImplementedError("Missing primary key field")

        annotations[self.pk_name] = INTERNAL_TYPE_TO_ANNOTATION[self.pk_type]
        identifiers.append(self.pk_name)
        class_definition[self.pk_name] = PydanticField()

        for field_name, internal_type in self.fields.items():
            if field_name in identifiers:
                continue
            if internal_type == "GenericForeignKey":
                annotation = Tuple[ContentTypeStr, UUID]
            elif internal_type in REFERENCE_INTERNAL_TYPES:
                field = meta.get_field(field_name)
                related_model = field.related_model
                if not related_model:
                    raise ValueError(f"Missing related model for field {field_name}")
                referenced_internal_type = related_model._meta.pk.get_internal_type()
                annotation = INTERNAL_TYPE_TO_ANNOTATION[referenced_internal_type]
                if internal_type == "ManyToManyField":
                    annotation = Set[annotation]
            else:
                annotation = INTERNAL_TYPE_TO_ANNOTATION[internal_type]

            attributes.append(field_name)
            annotations[field_name] = Optional[annotation]
            class_definition[field_name] = PydanticField(default=None)

        logger.debug("Creating model %s", class_definition)
        try:
            self.importer = type(class_definition["_modelname"], (ImporterModel,), class_definition)
        except Exception:
            logger.error("Failed to create model %s", class_definition, exc_info=True)
            raise

        return self.importer

    def add_field(self, field_name: FieldName, internal_type: InternalFieldTypeStr) -> None:
        """Add a field to the model."""
        if self.importer:
            raise RuntimeError("Cannot add fields after the importer has been created")

        logger.debug("Adding nautobot field %s %s %s", self.content_type, field_name, internal_type)
        if field_name in self.fields and self.fields[field_name] != internal_type:
            raise ValueError(f"Field {field_name} already exists with different type {self.fields[field_name]}")
        self.fields[field_name] = internal_type

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

        def get_value(field_name, internal_type) -> Any:
            value = getattr(instance, field_name, None)
            if value in EMPTY_VALUES:
                return None
            if internal_type == "GenericForeignKey":
                return (value._meta.label.lower(), value.pk)  # type: ignore
            if internal_type == "ManyToManyField":
                return set(item.id for item in value.all()) or None  # type: ignore
            if internal_type == "Property":
                return str(value)
            if internal_type == "CustomFieldData":
                return value
            return value

        result = {field_name: get_value(field_name, internal_type) for field_name, internal_type in self.fields.items()}
        result["id"] = instance.id
        return result

    # pylint: disable=too-many-statements
    def save_nautobot_instance(self, instance: NautobotBaseModel, values: RecordData) -> None:
        """Save a Nautobot instance."""

        def set_custom_field_data(value: Optional[Mapping]):
            custom_field_data = getattr(instance, "custom_field_data", None)
            if custom_field_data is None:
                raise TypeError("Missing custom_field_data")
            custom_field_data.clear()
            if value:
                custom_field_data.update(value)

        def set_generic_foreign_key(field: GenericForeignKey, value: Optional[GenericForeignValue]):
            if value:
                foreign_model = get_model_from_name(value[0])
                setattr(instance, field.ct_field, ContentType.objects.get_for_model(foreign_model))
                setattr(instance, field.fk_field, value[1])
            else:
                setattr(instance, field.fk_field, None)
                setattr(instance, field.ct_field, None)

        def set_empty(field_name: FieldName):
            if field.default not in EMPTY_VALUES:
                setattr(instance, field_name, field.default)
            elif field.blank and not field.null:
                setattr(instance, field_name, "")
            else:
                setattr(instance, field_name, None)

        def save():
            try:
                instance.clean()
            # `clean()` can be called again by getting `validation_errors` property after importing all data
            # pylint: disable=broad-exception-caught
            except Exception as exc:
                uid = instance.id
                if not isinstance(uid, (UUID, str, int)):
                    raise TypeError(f"Invalid uid {uid}") from exc
                self._clean_failures.add(uid)

            try:
                instance.save()
            except Exception:
                logger.error("Save failed: %s %s", instance, instance.__dict__, exc_info=True)
                raise

            # See `force_fields` below
            # if force_fields:
            #     instance.save(update_fields=force_fields)

            for field_name, value in m2m_fields.items():
                field = getattr(instance, field_name)
                if value:
                    field.set(value)
                else:
                    field.clear()

        # TBD: Fails with dcim.rack
        # _FORCE_FIELDS = ("created", "last_updated",)
        # force_fields = set()
        # Possible to implement for other models?

        m2m_fields = {}

        for field_name, value in values.items():
            # if field_name in _FORCE_FIELDS:
            #     force_fields.add(field_name)
            #     continue

            internal_type = self.fields[field_name]
            if internal_type == "ManyToManyField":
                m2m_fields[field_name] = value
            elif internal_type == "CustomFieldData":
                set_custom_field_data(value)
            elif internal_type == "Property":
                setattr(instance, field_name, value)
            else:
                field = instance._meta.get_field(field_name)  # type: ignore
                if internal_type == "GenericForeignKey":
                    set_generic_foreign_key(field, value)
                elif value in EMPTY_VALUES:
                    set_empty(field_name)
                else:
                    setattr(instance, field_name, value)

        save()


class ImporterModel(DiffSyncModel):
    """Base class for all DiffSync models."""

    _wrapper: NautobotModelWrapper

    @classmethod
    def create(cls, diffsync: BaseAdapter, ids: dict, attrs: dict) -> Optional[DiffSyncModel]:
        """Create this model instance, both in Nautobot and in DiffSync."""
        instance = cls._wrapper.model(**cls._wrapper.constructor_kwargs, **ids)
        if not isinstance(diffsync, NautobotAdapter):
            raise TypeError(f"Invalid diffsync type {diffsync}")
        cls._wrapper.save_nautobot_instance(instance, attrs)
        return super().create(diffsync, ids, attrs)

    def update(self, attrs: dict) -> Optional[DiffSyncModel]:
        """Update this model instance, both in Nautobot and in DiffSync."""
        uid = getattr(self, "id", None)
        if not uid:
            raise NotImplementedError("Cannot update model without id")

        model = self._wrapper.model
        instance = model.objects.get(id=uid)
        if not isinstance(self.diffsync, NautobotAdapter):
            raise TypeError(f"Invalid diffsync type {self.diffsync}")
        self._wrapper.save_nautobot_instance(instance, attrs)
        return super().update(attrs)
