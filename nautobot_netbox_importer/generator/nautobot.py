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

from diffsync import DiffSync
from diffsync import DiffSyncModel
from diffsync.enum import DiffSyncModelFlags
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Max
from nautobot.core.utils.lookup import get_model_from_name

from .base import DONT_IMPORT_TYPES
from .base import EMPTY_VALUES
from .base import INTEGER_AUTO_FIELD_TYPES
from .base import INTERNAL_TYPE_TO_ANNOTATION
from .base import REFERENCE_INTERNAL_TYPES
from .base import BaseAdapter
from .base import ContentTypeStr
from .base import DjangoModelMeta
from .base import FieldName
from .base import GenericForeignKey
from .base import GenericForeignValue
from .base import InternalFieldType
from .base import NautobotBaseModel
from .base import NautobotBaseModelType
from .base import NautobotField
from .base import PydanticField
from .base import RecordData
from .base import StrToInternalFieldType
from .base import Uid
from .base import get_nautobot_field_and_type
from .base import logger
from .base import normalize_datetime


class ValidationIssue(NamedTuple):
    """Validation issue."""

    uid: Uid
    name: str
    error: ValidationError


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
        self._validation_issues: Optional[Dict[ContentTypeStr, Set[ValidationIssue]]] = None
        self.wrappers: Dict[ContentTypeStr, NautobotModelWrapper] = {}

    @property
    def validation_issues(self) -> Dict[ContentTypeStr, Set[ValidationIssue]]:
        """Re-run clean() on all instances that failed validation."""
        if self._validation_issues is not None:
            return self._validation_issues

        self._validation_issues = {}
        for wrapper in self.wrappers.values():
            issues = wrapper.get_validation_issues()
            if issues:
                self._validation_issues[wrapper.content_type] = issues

        return self._validation_issues

    def get_or_create_wrapper(self, content_type: ContentTypeStr) -> "NautobotModelWrapper":
        """Get or create a Nautobot model wrapper."""
        if content_type in self.wrappers:
            return self.wrappers[content_type]

        return NautobotModelWrapper(self, content_type)


# pylint: disable=too-few-public-methods
class NautobotFieldWrapper:
    """Wrapper for a Nautobot field."""

    def __init__(self, name: FieldName, internal_type: InternalFieldType, field: Optional[NautobotField] = None):
        """Initialize the wrapper."""
        self.name = name
        self.internal_type = internal_type
        self.field = field

        # Forced fields needs to be saved in a separate step after the initial save.
        self.force = self.name == "created"


NautobotFields = MutableMapping[FieldName, NautobotFieldWrapper]


# pylint: disable=too-many-instance-attributes
class NautobotModelWrapper:
    """Wrapper for a Nautobot model."""

    def __init__(self, adapter: NautobotAdapter, content_type: ContentTypeStr):
        """Initialize the wrapper."""
        self._diffsync_class: Optional[Type[DiffSyncBaseModel]] = None
        self._clean_failures: Set[Uid] = set()
        self._content_type_instance = None
        self.flags = DiffSyncModelFlags.SKIP_UNMATCHED_DST

        self.adapter = adapter
        adapter.wrappers[content_type] = self
        self.content_type = content_type
        try:
            self._model = get_model_from_name(content_type)
            self.disabled = False
        except TypeError:
            self._model = None
            self.disabled = True

        self.fields: NautobotFields = {}

        self.last_id = 0

        if self.disabled:
            logger.info("Skipping unknown model %s", content_type)
            self._pk_field = None
        else:
            self._pk_field = self.add_field(self.model_meta.pk.name)  # type: ignore
            if not self._pk_field:
                raise ValueError(f"Missing pk field for {self.content_type}")

            if self._pk_field.internal_type in INTEGER_AUTO_FIELD_TYPES:
                self.last_id = (
                    self.model.objects.aggregate(Max(self._pk_field.name))[f"{self._pk_field.name}__max"] or 0
                )

        self.constructor_kwargs: Dict[FieldName, Any] = {}
        self.imported_count = 0

        logger.debug("Created %s", self)

    def __str__(self) -> str:
        """Return a string representation of the wrapper."""
        return f"{self.__class__.__name__}<{self.content_type}>"

    @property
    def pk_field(self) -> NautobotFieldWrapper:
        """Get the pk field."""
        if not self._pk_field:
            raise ValueError(f"Missing pk field for {self.content_type}")
        return self._pk_field

    @property
    def model(self) -> NautobotBaseModelType:
        """Get the Nautobot model."""
        if self._model:
            return self._model
        raise NotImplementedError("Cannot use disabled model")

    @property
    def model_meta(self) -> DjangoModelMeta:
        """Get the Nautobot model meta."""
        return self.model._meta  # type: ignore

    @property
    def diffsync_class(self) -> Type["DiffSyncBaseModel"]:
        """Get `DiffSyncModel` class for this wrapper."""
        if self._diffsync_class:
            return self._diffsync_class

        if self.disabled:
            raise RuntimeError("Cannot create importer for disabled model")

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
            if field.name in identifiers or field.internal_type in DONT_IMPORT_TYPES:
                continue
            if field.internal_type == InternalFieldType.GENERIC_FOREIGN_KEY:
                annotation = Tuple[ContentTypeStr, UUID]
            elif field.internal_type in REFERENCE_INTERNAL_TYPES:
                related_model = getattr(field.field, "related_model")
                if not related_model:
                    raise ValueError(f"Missing related model for field {field.name}")
                referenced_internal_type = StrToInternalFieldType[related_model._meta.pk.get_internal_type()]
                annotation = INTERNAL_TYPE_TO_ANNOTATION[referenced_internal_type]
                if field.internal_type == InternalFieldType.MANY_TO_MANY_FIELD:
                    annotation = Set[annotation]
            else:
                annotation = INTERNAL_TYPE_TO_ANNOTATION[field.internal_type]

            attributes.append(field.name)
            annotations[field.name] = Optional[annotation]
            class_definition[field.name] = PydanticField(default=None)

        try:
            self._diffsync_class = type(class_definition["_modelname"], (DiffSyncBaseModel,), class_definition)
        except Exception:
            logger.error("Failed to create DiffSync Model %s", class_definition, exc_info=True)
            raise

        logger.debug("Created DiffSync Model %s", class_definition)

        return self._diffsync_class

    def find_or_create(self, identifiers_kwargs: dict) -> Optional[DiffSyncModel]:
        """Find a DiffSync instance based on filter kwargs or create a new instance from Nautobot if possible."""
        result = self.adapter.get_or_none(self.diffsync_class, identifiers_kwargs)
        if result:
            return result

        try:
            nautobot_instance = self.model.objects.get(**identifiers_kwargs)
        except self.model.DoesNotExist:  # type: ignore
            return None

        diffsync_class = self.diffsync_class

        uid = getattr(nautobot_instance, self.pk_field.name)
        kwargs = {self.pk_field.name: uid}
        if identifiers_kwargs != kwargs:
            result = self.adapter.get_or_none(diffsync_class, kwargs)
            if result:
                return result

        result = diffsync_class(**kwargs, diffsync=self.adapter)  # type: ignore
        result.model_flags = self.flags
        self._nautobot_to_diffsync(nautobot_instance, result)
        self.adapter.add(result)

        return result

    def get_validation_issues(self) -> Set[ValidationIssue]:
        """Get the set of instances that failed to clean."""
        result = set()

        for uid in self._clean_failures:
            try:
                instance = self.model.objects.get(id=uid)
            except self.model.DoesNotExist as error:  # type: ignore
                # This can happen with Tree models, some issue is there. Ignore for now, just add the validation issue.
                result.add(
                    ValidationIssue(
                        uid,
                        "",
                        ValidationError(f"Instance was not found, event it was saved. {error}"),
                    )
                )
            else:
                try:
                    instance.clean()
                except ValidationError as error:
                    result.add(ValidationIssue(uid, str(instance), error))
                # pylint: disable-next=broad-exception-caught
                except Exception as error:
                    result.add(ValidationIssue(uid, str(instance), ValidationError(f"Unknown error: {error}")))

        self._clean_failures = set()

        return result

    def add_field(self, field_name: FieldName) -> NautobotFieldWrapper:
        """Add a field to the model."""
        if self._diffsync_class:
            raise RuntimeError("Cannot add fields after the DiffSync Model has been created")

        nautobot_field, internal_type = get_nautobot_field_and_type(self.model, field_name)

        if (
            internal_type in REFERENCE_INTERNAL_TYPES
            and internal_type not in [InternalFieldType.MANY_TO_MANY_FIELD, InternalFieldType.GENERIC_FOREIGN_KEY]
            and not field_name.endswith("_id")
        ):
            # Reference fields are converted to id fields
            field_name = f"{field_name}_id"

        if field_name in self.fields:
            field = self.fields[field_name]
            if field.internal_type != internal_type:
                raise ValueError(f"Field {field_name} already exists with different type {self.fields[field_name]}")
        else:
            logger.debug("Adding nautobot field %s %s %s", self.content_type, field_name, internal_type)
            field = NautobotFieldWrapper(field_name, internal_type, nautobot_field)
            self.fields[field_name] = field

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

    def _nautobot_to_diffsync(self, source: NautobotBaseModel, target: "DiffSyncBaseModel") -> None:
        """Copy data from Nautobot instance to DiffSync Model."""

        def set_value(field_name, internal_type) -> None:
            if internal_type in DONT_IMPORT_TYPES:
                return

            value = getattr(source, field_name, None)
            if value in EMPTY_VALUES:
                return

            if internal_type == InternalFieldType.GENERIC_FOREIGN_KEY:
                setattr(target, field_name, (value._meta.label.lower(), value.pk))  # type: ignore
            elif internal_type == InternalFieldType.MANY_TO_MANY_FIELD:
                values = value.all()  # type: ignore
                if values:
                    setattr(target, field_name, set(item.pk for item in values))
            elif internal_type == InternalFieldType.PROPERTY:
                setattr(target, field_name, str(value))
            elif internal_type == InternalFieldType.DATE_TIME_FIELD:
                setattr(target, field_name, normalize_datetime(value))
            else:
                setattr(target, field_name, value)

        for field in self.fields.values():
            set_value(field.name, field.internal_type)

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
        force_fields = {}

        for field_name, value in values.items():
            field_wrapper = self.fields[field_name]
            if field_wrapper.internal_type in DONT_IMPORT_TYPES:
                return

            if field_wrapper.internal_type == InternalFieldType.MANY_TO_MANY_FIELD:
                m2m_fields.add(field_name)
            elif field_wrapper.internal_type == InternalFieldType.CUSTOM_FIELD_DATA:
                set_custom_field_data(value)
            elif field_wrapper.internal_type == InternalFieldType.GENERIC_FOREIGN_KEY:
                set_generic_foreign_key(field_wrapper.field, value)
            elif value in EMPTY_VALUES:
                set_empty(field_wrapper.field, field_name)
            elif field_wrapper.force:
                force_fields[field_name] = value
            else:
                setattr(instance, field_name, value)

        try:
            instance.save()
        except Exception:
            logger.error("Save failed: %s %s", instance, instance.__dict__, exc_info=True)
            raise

        if force_fields:
            # These fields has to be set after the initial save to override any default values.
            for field_name, value in force_fields.items():
                setattr(instance, field_name, value)
            instance.save()

        for field_name in m2m_fields:
            field = getattr(instance, field_name)
            value = values[field_name]
            if value:
                field.set(value)
            else:
                field.clear()

        try:
            instance.clean()
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            # `clean()` can be called again by getting `validation_issues` property after importing all data
            uid = getattr(instance, self.pk_field.name, None)
            if not isinstance(uid, (UUID, str, int)):
                raise TypeError(f"Invalid uid {uid}") from exc
            self._clean_failures.add(uid)


class DiffSyncBaseModel(DiffSyncModel):
    """Base class for all DiffSync models."""

    _wrapper: NautobotModelWrapper

    @classmethod
    def create(cls, diffsync: DiffSync, ids: dict, attrs: dict) -> Optional["DiffSyncBaseModel"]:
        """Create this model instance, both in Nautobot and in DiffSync."""
        instance = cls._wrapper.model(**cls._wrapper.constructor_kwargs, **ids)

        cls._wrapper.save_nautobot_instance(instance, attrs)

        return super().create(diffsync, ids, attrs)

    def update(self, attrs: dict) -> Optional["DiffSyncBaseModel"]:
        """Update this model instance, both in Nautobot and in DiffSync."""
        uid = getattr(self, self._wrapper.pk_field.name, None)
        if not uid:
            raise NotImplementedError("Cannot update model without pk")

        model = self._wrapper.model
        filter_kwargs = {self._wrapper.pk_field.name: uid}
        instance = model.objects.get(**filter_kwargs)
        self._wrapper.save_nautobot_instance(instance, attrs)

        return super().update(attrs)