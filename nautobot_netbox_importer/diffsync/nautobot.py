"""Generic Nautobot DiffSync Importer."""

from typing import Any
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import MutableMapping
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from uuid import UUID

from diffsync import DiffSync
from diffsync import DiffSyncModel
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from nautobot.core.utils.lookup import get_model_from_name
from pydantic import Field as PydanticField

from .base import EMPTY_VALUES
from .base import INTERNAL_TYPE_TO_ANNOTATION
from .base import REFERENCE_INTERNAL_TYPES
from .base import ContentTypeStr
from .base import FieldName
from .base import InternalFieldTypeStr
from .base import NautobotBaseModel
from .base import RecordData
from .base import logger

NautobotFields = MutableMapping[FieldName, InternalFieldTypeStr]

# Helper to get the order of models to import. Not all models needs to be here.
IMPORT_ORDER: Iterable[ContentTypeStr] = (
    "extras.customfield",
    "extras.customfieldchoice",
    "extras.status",
    "extras.role",
    "dcim.location",
    "dcim.locationtype",
    "tenancy.tenant",
    "tenancy.tenantgroup",
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
    "dcim.manufacturer",
    "dcim.platform",
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
    "ipam.rir",
    "ipam.vlan",
    "ipam.vlangroup",
    "virtualization.cluster",
    "virtualization.clustergroup",
    "virtualization.clustertype",
    "virtualization.virtualmachine",
    "virtualization.vminterface",
)


class NautobotModelWrapper:
    """Wrapper for a Nautobot model."""

    def __init__(self, content_type: ContentTypeStr):
        """Initialize the wrapper."""
        self.content_type = content_type
        self.model = get_model_from_name(content_type)
        self.fields: NautobotFields = {}
        self.importer: Optional[Type[ImporterModel]] = None

        pk_field = self.model._meta.pk
        self.pk_type = pk_field.get_internal_type()
        self.pk_name = pk_field.name
        if self.pk_name != "id":
            raise NotImplementedError("Primary key field must be named 'id'")
        self.add_field(self.pk_name, self.pk_type)
        self.constructor_kwargs: Dict[FieldName, Any] = {}

    def get_importer(self) -> Type["ImporterModel"]:
        """Get the DiffSync model for this model."""
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
        logger.debug("Adding nautobot field %s %s %s", self.content_type, field_name, internal_type)
        if field_name in self.fields and self.fields[field_name] != internal_type:
            raise ValueError(f"Field {field_name} already exists with different type {self.fields[field_name]}")
        self.fields[field_name] = internal_type

    def get_content_type(self) -> ContentType:
        """Get the Nautobot content type ID for a given content type."""
        return ContentType.objects.get_for_model(get_model_from_name(self.content_type))

    def set_instance_defaults(self, **defaults: Any) -> None:
        """Set default values for a Nautobot instance constructor."""
        self.constructor_kwargs = defaults


class ImporterModel(DiffSyncModel):
    """Base class for all DiffSync models."""

    _wrapper: NautobotModelWrapper

    @classmethod
    def create(cls, diffsync: DiffSync, ids: dict, attrs: dict) -> Optional[DiffSyncModel]:
        """Create this model instance, both in Nautobot and in DiffSync."""
        instance = cls._wrapper.model(**cls._wrapper.constructor_kwargs, **ids)
        if not isinstance(diffsync, NautobotAdapter):
            raise TypeError(f"Invalid diffsync type {diffsync}")
        diffsync.save_nautobot_instance(instance, attrs, cls._wrapper.fields)
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
        self.diffsync.save_nautobot_instance(instance, attrs, self._wrapper.fields)
        return super().update(attrs)


class NautobotAdapter(DiffSync):
    """Nautobot DiffSync Adapter."""

    def __init__(self, name="Nautobot", *args, **kwargs):
        """Initialize the adapter."""
        super().__init__(name, *args, **kwargs)
        self.clean_failures: Set[NautobotBaseModel] = set()

    def get_validation_errors(self, log=True) -> Generator[Tuple[NautobotBaseModel, ValidationError], None, None]:
        """Re-run clean() on all instances that failed validation."""
        for instance in self.clean_failures:
            instance = instance.__class__.objects.get(id=instance.id)
            try:
                instance.clean()
            except ValidationError as error:
                yield instance, error
                if log:
                    logger.error("Clean failed: %s %s", instance, instance.__dict__, exc_info=True)

    def save_nautobot_instance(self, instance: NautobotBaseModel, values: RecordData, fields: NautobotFields) -> None:
        """Save a Nautobot instance."""
        m2m_fields = {}

        # TBD: Fails with dcim.rack
        # _FORCE_FIELDS = ("created", "last_updated",)
        # force_fields = set()

        def set_value(field_name: FieldName, value: Any, internal_type: InternalFieldTypeStr):
            # if field_name in _FORCE_FIELDS:
            #     force_fields.add(field_name)

            if internal_type == "ManyToManyField":
                m2m_fields[field_name] = value
                return

            if internal_type == "CustomFieldData":
                custom_field_data = getattr(instance, "custom_field_data", None)
                if custom_field_data is None:
                    raise TypeError("Missing custom_field_data")
                custom_field_data.clear()
                if value:
                    custom_field_data.update(value)
                return

            if internal_type == "Any":
                setattr(instance, field_name, value)
                return

            field = instance._meta.get_field(field_name)  # type: ignore

            if internal_type == "GenericForeignKey":
                if value:
                    foreign_model = get_model_from_name(value[0])
                    setattr(instance, field.ct_field, ContentType.objects.get_for_model(foreign_model))
                    setattr(instance, field.fk_field, value[1])
                else:
                    setattr(instance, field.fk_field, None)
                    setattr(instance, field.ct_field, None)
                return

            if value in EMPTY_VALUES:
                if field.default not in EMPTY_VALUES:
                    setattr(instance, field_name, field.default)
                elif field.blank and not field.null:
                    setattr(instance, field_name, "")
                else:
                    setattr(instance, field_name, None)
            else:
                setattr(instance, field_name, value)

        for field_name, value in values.items():
            set_value(field_name, value, fields[field_name])

        try:
            instance.clean()
        # `clean()` can be called again by `get_validation_errors()` after adding everything to the database
        # pylint: disable=broad-exception-caught
        except Exception:
            self.clean_failures.add(instance)

        try:
            instance.save()
        except Exception:
            logger.error("Save failed: %s %s", instance, instance.__dict__, exc_info=True)
            raise

        # See `force_fields` above
        # if force_fields:
        #     instance.save(update_fields=force_fields)

        for field_name, value in m2m_fields.items():
            field = getattr(instance, field_name)
            if value:
                field.set(value)
            else:
                field.clear()


def get_nautobot_instance_data(instance: NautobotBaseModel, fields: NautobotFields) -> RecordData:
    """Get the data for a Nautobot instance."""

    def get_value(field_name, internal_type) -> Any:
        value = getattr(instance, field_name, None)
        if value in EMPTY_VALUES:
            return None
        if internal_type == "GenericForeignKey":
            return (value._meta.label.lower(), value.pk)  # type: ignore
        if internal_type == "ManyToManyField":
            return set(item.id for item in value.all()) or None  # type: ignore
        if internal_type == "Any":
            return str(value)
        if internal_type == "CustomFieldData":
            return value
        return value

    result = {field_name: get_value(field_name, internal_type) for field_name, internal_type in fields.items()}
    result["id"] = instance.id
    return result