"""Nautobot DiffSync Importer."""

from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Set, Type

from diffsync import DiffSync, DiffSyncModel
from diffsync.enum import DiffSyncModelFlags
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max
from django.db.transaction import atomic
from nautobot.core.utils.lookup import get_model_from_name
from nautobot.extras.models import Tag

from nautobot_netbox_importer.base import FieldName, RecordData, logger
from nautobot_netbox_importer.summary import (
    ImporterIssue,
    ImportSummary,
    NautobotModelStats,
    NautobotModelSummary,
    get_issue_tag,
)

from .base import (
    AUTO_ADD_FIELDS,
    EMPTY_VALUES,
    INTERNAL_TYPE_TO_ANNOTATION,
    BaseAdapter,
    ContentTypeStr,
    DjangoField,
    DjangoModelMeta,
    InternalFieldType,
    NautobotBaseModel,
    NautobotBaseModelType,
    PydanticField,
    StrToInternalFieldType,
    Uid,
    get_nautobot_field_and_type,
    normalize_datetime,
    source_pk_to_uuid,
)
from .exceptions import NautobotModelNotFound

_AUTO_INCREMENT_TYPES: Iterable[InternalFieldType] = (
    InternalFieldType.AUTO_FIELD,
    InternalFieldType.BIG_AUTO_FIELD,
)

_INTEGER_TYPES: Iterable[InternalFieldType] = (
    InternalFieldType.AUTO_FIELD,
    InternalFieldType.BIG_AUTO_FIELD,
    InternalFieldType.BIG_INTEGER_FIELD,
    InternalFieldType.INTEGER_FIELD,
    InternalFieldType.POSITIVE_INTEGER_FIELD,
    InternalFieldType.POSITIVE_SMALL_INTEGER_FIELD,
    InternalFieldType.SMALL_INTEGER_FIELD,
)

_REFERENCE_TYPES: Iterable[InternalFieldType] = (
    InternalFieldType.FOREIGN_KEY,
    InternalFieldType.FOREIGN_KEY_WITH_AUTO_RELATED_NAME,
    InternalFieldType.MANY_TO_MANY_FIELD,
    InternalFieldType.ONE_TO_ONE_FIELD,
    InternalFieldType.ROLE_FIELD,
    InternalFieldType.STATUS_FIELD,
    InternalFieldType.TREE_NODE_FOREIGN_KEY,
)

_DONT_IMPORT_TYPES: Iterable[InternalFieldType] = (
    InternalFieldType.NOT_FOUND,
    InternalFieldType.PRIVATE_PROPERTY,
    InternalFieldType.READ_ONLY_PROPERTY,
)


# Helper to determine the import order of models.
# Due to dependencies among Nautobot models, certain models must be imported first to ensure successful `instance.save()` calls without errors.
# Models listed here take precedence over others, which are sorted by the order they're introduced to the importer.
# Models listed, but not imported, here will be ignored.
# Obsoleted models can be kept here to ensure backward compatibility.
# More information about the import order can be found in the app documentation: https://docs.nautobot.com/projects/netbox-importer/en/latest/dev/import_order/
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
    "dcim.consoleserverport",
    "dcim.consoleserverporttemplate",
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
        self.wrappers: Dict[ContentTypeStr, NautobotModelWrapper] = {}
        self.trace_issues = False

    def get_or_create_wrapper(self, content_type: ContentTypeStr) -> "NautobotModelWrapper":
        """Get or create a Nautobot model wrapper."""
        if content_type in self.wrappers:
            return self.wrappers[content_type]

        return NautobotModelWrapper(self, content_type)

    @atomic
    def tag_issues(self, summary: ImportSummary) -> None:
        """Tag all records with any ImporterIssue."""
        logger.info("Tagging all instance with issues")

        for item in summary.nautobot:
            self.get_or_create_wrapper(item.content_type).tag_issues(item.issues)


class NautobotField:
    """Wrapper for a Nautobot field."""

    def __init__(self, name: FieldName, internal_type: InternalFieldType, field: Optional[DjangoField] = None):
        """Initialize the wrapper."""
        self.name = name
        self.internal_type = internal_type
        self.field = field
        self.required = not (getattr(field, "null", False) or getattr(field, "blank", False)) if field else False

        # Forced fields needs to be saved in a separate step after the initial save.
        self.force = self.name == "created"

    def __str__(self) -> str:
        """Return a string representation of the wrapper."""
        return f"{self.__class__.__name__}<{self.name} {self.internal_type}>"

    @property
    def related_model(self) -> NautobotBaseModelType:
        """Get the related model for a reference field."""
        if not isinstance(self.field, DjangoField):
            raise NotImplementedError(f"Unsupported relation importer {self}")

        return getattr(self.field, "related_model")

    @property
    def related_meta(self) -> DjangoModelMeta:
        """Get the Nautobot model meta."""
        return self.related_model._meta  # type: ignore

    @property
    def is_reference(self) -> bool:
        """Check if the field is a reference."""
        return self.internal_type in _REFERENCE_TYPES

    @property
    def is_integer(self) -> bool:
        """Check if the field is an integer."""
        return self.internal_type in _INTEGER_TYPES

    @property
    def is_auto_increment(self) -> bool:
        """Check if the field is an integer."""
        return self.internal_type in _AUTO_INCREMENT_TYPES

    @property
    def is_content_type(self) -> bool:
        """Check if the field is a content type."""
        if not self.is_reference:
            return False

        return self.related_model == ContentType

    @property
    def can_import(self) -> bool:
        """Determine if this field can be imported."""
        return self.internal_type not in _DONT_IMPORT_TYPES


NautobotFields = MutableMapping[FieldName, NautobotField]


# pylint: disable=too-many-instance-attributes
class NautobotModelWrapper:
    """Wrapper for a Nautobot model."""

    def __init__(self, adapter: NautobotAdapter, content_type: ContentTypeStr):
        """Initialize the wrapper."""
        self._diffsync_class: Optional[Type[DiffSyncBaseModel]] = None
        self._issues: List[ImporterIssue] = []
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

            if self._pk_field.is_auto_increment:
                self.last_id = (
                    self.model.objects.aggregate(Max(self._pk_field.name))[f"{self._pk_field.name}__max"] or 0
                )

            for field_name in AUTO_ADD_FIELDS:
                if hasattr(self.model, field_name):
                    self.add_field(field_name)

        self.constructor_kwargs: Dict[FieldName, Any] = {}
        self.stats = NautobotModelStats()

        logger.debug("Created %s", self)

    def __str__(self) -> str:
        """Return a string representation of the wrapper."""
        return f"{self.__class__.__name__}<{self.content_type}>"

    @property
    def pk_field(self) -> NautobotField:
        """Get the pk field."""
        if not self._pk_field:
            raise ValueError(f"Missing pk field for {self.content_type}")
        return self._pk_field

    @property
    def model(self) -> NautobotBaseModelType:
        """Get the Nautobot model."""
        if self._model:
            return self._model
        raise NautobotModelNotFound(self.content_type)

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
            if field.name in identifiers or not field.can_import:
                continue

            if field.is_reference:
                related_type = StrToInternalFieldType[field.related_meta.pk.get_internal_type()]  # type: ignore
                annotation = INTERNAL_TYPE_TO_ANNOTATION[related_type]
                if field.internal_type == InternalFieldType.MANY_TO_MANY_FIELD:
                    annotation = Set[annotation]
            else:
                annotation = INTERNAL_TYPE_TO_ANNOTATION[field.internal_type]

            attributes.append(field.name)
            if not field.required:
                annotation = Optional[annotation]
            annotations[field.name] = annotation
            class_definition[field.name] = PydanticField(default=None)

        try:
            result = type(class_definition["_modelname"], (DiffSyncBaseModel,), class_definition)
            self._diffsync_class = result
        except Exception:
            logger.error("Failed to create DiffSync Model %s", class_definition, exc_info=True)
            raise

        logger.debug("Created DiffSync Model %s", class_definition)

        return result

    def get_summary(self) -> NautobotModelSummary:
        """Get the summary."""
        issues = sorted(self.get_importer_issues())
        if issues:
            self.stats.issues = len(issues)

        return NautobotModelSummary(
            content_type=self.content_type,
            content_type_id=None if self.disabled else self.content_type_instance.pk,
            stats=self.stats,
            issues=issues,
            flags=str(self.flags),
            disabled=self.disabled,
        )

    # pylint: disable=too-many-arguments
    def add_issue(  # noqa: PLR0913
        self,
        issue_type="",
        message="",
        uid: Uid = "",
        data: Optional[Mapping] = None,
        diffsync_instance: Optional[DiffSyncModel] = None,
        nautobot_instance: Optional[NautobotBaseModel] = None,
        error: Optional[Exception] = None,
        nautobot_name="",
    ) -> ImporterIssue:
        """Add a new importer issue.

        This function register an issue and returns the issue object. All input arguments are optional, internal logic
        tries to fill in as much information as possible based on the arguments provided.

        It can be called in any import stage.

        Args:
            issue_type (Optional[str]): The type of the issue, e.g. "SaveFailed". Can be determined from `error.__class__`.
            message (Optional[str]): A message to be included in the issue. Can be determined from `error`.
            uid (Optional[Uid]): The UID of the instance that caused the issue. Can be determined from instances.
            data (Optional[Mapping]): The data that caused the issue.
            diffsync_instance (Optional[DiffSyncModel]): The DiffSync instance that caused the issue.
            nautobot_instance (Optional[NautobotBaseModel]): The Nautobot instance that caused the issue.
            error (Optional[Exception]): The error that caused the issue.
            nautobot_name (Optional[str]): The name of the Nautobot instance that caused the issue.
                This is determined after the import, before creating summaries.

        Examples can be found by looking at calls to this function in the code.
        """
        issue = self._create_issue(
            issue_type, message, uid, data, diffsync_instance, nautobot_instance, error, nautobot_name
        )
        self._issues.append(issue)
        return issue

    # pylint: disable=too-many-arguments,too-many-branches
    def _create_issue(  # noqa: PLR0912, PLR0913
        self,
        issue_type="",
        message="",
        uid: Uid = "",
        data: Optional[Mapping] = None,
        diffsync_instance: Optional[DiffSyncModel] = None,
        nautobot_instance: Optional[NautobotBaseModel] = None,
        error: Optional[Exception] = None,
        nautobot_name="",
    ) -> ImporterIssue:
        """Create an issue."""
        if not issue_type:
            if error:
                issue_type = getattr(error, "issue_type", None) or error.__class__.__name__
            else:
                issue_type = "Unknown"

        if diffsync_instance:
            if not uid:
                uid = getattr(diffsync_instance, self.pk_field.name)
            if not data:
                data = diffsync_instance.__dict__

        if nautobot_instance:
            if not uid:
                uid = getattr(nautobot_instance, self.pk_field.name)
            if not data:
                data = nautobot_instance.__dict__
            if not nautobot_name:
                try:
                    nautobot_name = str(nautobot_instance)
                # pylint: disable=broad-exception-caught
                except Exception:  # noqa: S110
                    # Can happen for non-complete Nautobot instances. Pass silently, just don't set the name.
                    pass

        # Convert data to `dict[str, str]`
        data_dict = {
            key: str(value) for key, value in (data or {}).items() if isinstance(key, str) and not key.startswith("_")
        }

        if not uid:
            uid = data_dict.get(self.pk_field.name, "")

        def get_message():
            if message:
                yield message
            if error:
                yield str(error)

        issue = ImporterIssue(
            uid=str(uid),
            name=nautobot_name,
            issue_type=issue_type,
            message=" ".join(get_message()),
            data=data_dict,
        )

        logger.warning(str(issue))
        if error and self.adapter.trace_issues:
            logger.error("Issue traceback", exc_info=error)

        return issue

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

    def get_importer_issues(self) -> List[ImporterIssue]:
        """Get importer issues for this model.

        This will also run `clean` on all instances that failed `clean()` after saving.
        """
        result = []

        for issue in self._issues:
            if not issue.uid or (issue.name and issue.issue_type != "CleanFailed"):
                # Just copy an issue, can't, or doesn't need to, be cleaned or extended.
                result.append(issue)
                continue

            try:
                nautobot_instance = self.model.objects.get(id=issue.uid)
            except self.model.DoesNotExist as error:  # type: ignore
                if issue.issue_type == "CleanFailed":
                    # This can happen with Tree models, not sure why. Ignore for now, just add the importer issue.
                    result.append(
                        self._create_issue(
                            uid=issue.uid,
                            error=error,
                            message="Instance was not found, even it was saved.",
                        )
                    )
                result.append(issue)
                continue

            if issue.issue_type == "CleanFailed":
                # Re-run clean on the instance, add the issue if it fails.
                try:
                    nautobot_instance.clean()
                # pylint: disable=broad-exception-caught
                except Exception as error:
                    result.append(
                        self._create_issue(
                            uid=issue.uid,
                            data=issue.data,
                            nautobot_instance=nautobot_instance,
                            error=error,
                        )
                    )
                continue

            # Extend the issue with the Nautobot instance.
            result.append(
                self._create_issue(
                    issue_type=issue.issue_type,
                    message=issue.message,
                    uid=issue.uid,
                    data=issue.data,
                    nautobot_instance=nautobot_instance,
                )
            )

        self._issues = []

        return result

    def add_field(self, field_name: FieldName) -> NautobotField:
        """Add a field to the model."""
        if self._diffsync_class:
            raise RuntimeError("Cannot add fields after the DiffSync Model has been created")

        nautobot_field, internal_type = get_nautobot_field_and_type(self.model, field_name)

        if (
            internal_type in _REFERENCE_TYPES
            and internal_type != InternalFieldType.MANY_TO_MANY_FIELD
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
            field = NautobotField(field_name, internal_type, nautobot_field)
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
            value = getattr(source, field_name, None)
            if value in EMPTY_VALUES:
                return

            if internal_type == InternalFieldType.MANY_TO_MANY_FIELD:
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
            if field.can_import:
                set_value(field.name, field.internal_type)

    def save_nautobot_instance(self, instance: NautobotBaseModel, values: RecordData) -> bool:
        """Save a Nautobot instance."""

        def set_custom_field_data(value: Optional[Mapping]):
            custom_field_data = getattr(instance, "custom_field_data", None)
            if custom_field_data is None:
                raise TypeError("Missing custom_field_data")
            custom_field_data.clear()
            if value:
                custom_field_data.update(value)

        def set_empty(field, field_name: FieldName):
            if field.blank and not field.null:
                setattr(instance, field_name, "")
            else:
                setattr(instance, field_name, None)

        @atomic
        def save():
            m2m_fields = set()
            force_fields = {}

            for field_name, value in values.items():
                field_wrapper = self.fields[field_name]
                if not field_wrapper.can_import:
                    continue

                if field_wrapper.internal_type == InternalFieldType.MANY_TO_MANY_FIELD:
                    m2m_fields.add(field_name)
                elif field_wrapper.internal_type == InternalFieldType.CUSTOM_FIELD_DATA:
                    set_custom_field_data(value)
                elif value in EMPTY_VALUES:
                    set_empty(field_wrapper.field, field_name)
                elif field_wrapper.force:
                    force_fields[field_name] = value
                else:
                    setattr(instance, field_name, value)

            instance.save()

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
            save()
        # pylint: disable=broad-exception-caught
        except Exception as error:
            self.stats.save_failed += 1
            self.add_issue(
                "SaveFailed",
                nautobot_instance=instance,
                data=values,
                error=error,
            )
            return False

        try:
            instance.clean()
        # pylint: disable=broad-exception-caught
        except Exception as error:
            # `clean()` is called again by `get_importer_issues()` after importing all data
            self.add_issue(
                "CleanFailed",
                nautobot_instance=instance,
                data=values,
                error=error,
            )

        return True

    def tag_issues(self, issues: Iterable[ImporterIssue]) -> None:
        """Tag all records with any ImporterIssue."""
        if not issues:
            return

        model = self.model

        if not hasattr(model, "tags"):
            return

        for issue in issues:
            if not issue.uid:
                continue

            try:
                nautobot_instance = model.objects.get(id=issue.uid)
            except model.DoesNotExist:  # type: ignore
                continue

            tag_name = get_issue_tag(issue)
            tag, _ = Tag.objects.get_or_create(
                id=source_pk_to_uuid("extras.tag", tag_name),
                defaults={
                    "name": tag_name,
                    "description": f"Import issue: {tag_name}",
                },
            )

            logger.debug("Tagging %s %s %s", self.content_type, issue.uid, tag_name)

            if not tag.content_types.filter(id=self.content_type_id).exists():
                tag.content_types.add(self.content_type_instance)

            nautobot_instance.tags.add(tag)


class DiffSyncBaseModel(DiffSyncModel):
    """Base class for all DiffSync models."""

    _wrapper: NautobotModelWrapper

    @classmethod
    def create(cls, diffsync: DiffSync, ids: dict, attrs: dict) -> Optional["DiffSyncBaseModel"]:
        """Create this model instance, both in Nautobot and in DiffSync."""
        wrapper = cls._wrapper

        instance = None
        try:
            instance = wrapper.model(**wrapper.constructor_kwargs, **ids)
            result = super().create(diffsync, ids, attrs)
        # pylint: disable=broad-exception-caught
        except Exception as error:
            wrapper.add_issue(
                "CreateFailed",
                uid=ids.get(wrapper.pk_field.name, ""),
                nautobot_instance=instance,
                data=attrs,
                error=error,
            )
            return None

        if wrapper.save_nautobot_instance(instance, attrs):
            wrapper.stats.created += 1
            return result

        return None

    def update(self, attrs: dict) -> Optional["DiffSyncBaseModel"]:
        """Update this model instance, both in Nautobot and in DiffSync."""
        wrapper = self._wrapper
        uid = getattr(self, wrapper.pk_field.name, None)
        if not uid:
            raise NotImplementedError("Cannot update model without pk")

        try:
            super().update(attrs)
        # pylint: disable=broad-exception-caught
        except Exception as error:
            wrapper.add_issue(
                "UpdateFailed",
                uid=uid,
                diffsync_instance=self,
                data=attrs,
                error=error,
            )
            return None

        model = wrapper.model
        filter_kwargs = {wrapper.pk_field.name: uid}
        instance = model.objects.get(**filter_kwargs)
        if wrapper.save_nautobot_instance(instance, attrs):
            wrapper.stats.updated += 1
            return self

        return None
