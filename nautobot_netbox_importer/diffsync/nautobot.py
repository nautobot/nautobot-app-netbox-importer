"""Generic Nautobot DiffSync Importer."""

from typing import Any
from typing import Dict
from typing import Iterable
from typing import MutableMapping
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
from pydantic import Field as PydanticField

from .base import EMPTY_VALUES
from .base import INTERNAL_TYPE_TO_ANNOTATION
from .base import REFERENCE_INTERNAL_TYPES
from .base import BaseAdapter
from .base import ContentTypeStr
from .base import FieldName
from .base import GenericForeignKey
from .base import InternalFieldTypeStr
from .base import NautobotBaseModel
from .base import NautobotBaseModelType
from .base import RecordData
from .base import Uid
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


# pylint: disable=too-many-instance-attributes
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

        if self.pk_type == "UUIDField":
            self.last_id = 0
        elif self.pk_type == "AutoField":
            self.last_id = self.model.objects.aggregate(Max("id"))["id__max"] or 0
        else:
            raise ValueError(f"Unsupported pk_type {self.pk_type}")

        self.constructor_kwargs: Dict[FieldName, Any] = {}
        self.imported_count = 0
        # TBD: Merge ignored_fields to fields
        self.ignored_fields: Set[FieldName] = set(self.pk_name)

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
            if field_name in self.ignored_fields:
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

    def ignore_fields(self, *field_names: FieldName) -> None:
        """Skip a fields when importing."""
        self.ignored_fields.update(field_names)

    def add_field(self, field_name: FieldName, internal_type: InternalFieldTypeStr) -> None:
        """Add a field to the model."""
        # TBD: Lock down the fields after the importer is created
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
    def create(cls, diffsync: BaseAdapter, ids: dict, attrs: dict) -> Optional[DiffSyncModel]:
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


class NautobotAdapter(BaseAdapter):
    """Nautobot DiffSync Adapter."""

    def __init__(self, *args, **kwargs):
        """Initialize the adapter."""
        super().__init__("Nautobot", *args, **kwargs)
        self.clean_failures: Dict[NautobotBaseModelType, Set[Uid]] = {}
        self.validation_errors: Optional[Dict[ContentTypeStr, Set[ValidationError]]] = None

    def get_validation_errors(self) -> Dict[ContentTypeStr, Set[ValidationError]]:
        """Re-run clean() on all instances that failed validation."""
        if self.validation_errors is not None:
            return self.validation_errors

        self.validation_errors = {}

        failures = self.clean_failures
        self.clean_failures = {}

        for model_type, uids in failures.items():
            errors = None
            for uid in uids:
                instance = model_type.objects.get(id=uid)
                try:
                    instance.clean()
                except ValidationError as error:
                    if errors:
                        errors.add(error)
                    else:
                        errors = set([error])
                        self.validation_errors[model_type._meta.label.lower()] = errors  # type: ignore

        return self.validation_errors

    # pylint: disable=too-many-statements
    def save_nautobot_instance(self, instance: NautobotBaseModel, values: RecordData, fields: NautobotFields) -> None:
        """Save a Nautobot instance."""

        def set_custom_field(value: Any):
            # TBD: Consider just updating without removing
            custom_field_data = getattr(instance, "custom_field_data", None)
            if custom_field_data is None:
                raise TypeError("Missing custom_field_data")
            custom_field_data.clear()
            if value:
                custom_field_data.update(value)

        def set_generic_foreign_key(field: GenericForeignKey, value: Any):
            if value:
                foreign_model = get_model_from_name(value[0])
                setattr(instance, field.ct_field, ContentType.objects.get_for_model(foreign_model))
                setattr(instance, field.fk_field, value[1])
            else:
                setattr(instance, field.fk_field, None)
                setattr(instance, field.ct_field, None)

        def set_empty(field_name: FieldName, value: Any):
            if value in EMPTY_VALUES:
                if field.default not in EMPTY_VALUES:
                    setattr(instance, field_name, field.default)
                elif field.blank and not field.null:
                    setattr(instance, field_name, "")
                else:
                    setattr(instance, field_name, None)
            else:
                setattr(instance, field_name, value)

        def save():
            try:
                instance.clean()
            # `clean()` can be called again by `iter_validation_errors()` after adding everything to the database
            # pylint: disable=broad-exception-caught
            except Exception as exc:
                uid = instance.id
                if not isinstance(uid, Uid):
                    raise TypeError(f"Invalid uid {uid}") from exc
                if instance.__class__ in self.clean_failures:
                    self.clean_failures[instance.__class__].add(uid)
                else:
                    self.clean_failures[instance.__class__] = set([uid])

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

            internal_type = fields[field_name]
            if internal_type == "ManyToManyField":
                m2m_fields[field_name] = value
            elif internal_type == "CustomFieldData":
                set_custom_field(value)
            elif internal_type == "Any":
                setattr(instance, field_name, value)
            else:
                field = instance._meta.get_field(field_name)  # type: ignore
                if internal_type == "GenericForeignKey":
                    set_generic_foreign_key(field, value)
                elif value in EMPTY_VALUES:
                    set_empty(field_name, value)
                else:
                    setattr(instance, field_name, value)

        save()


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
