"""Abstract model class mixins for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-few-public-methods
import json
import uuid

from datetime import date, datetime
from typing import Any, Mapping, Optional, Tuple, Union, Iterable

from diffsync import DiffSync, DiffSyncModel
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.db import models
from django.db.utils import IntegrityError
import netaddr
from pydantic import BaseModel, validator, root_validator
from pydantic.error_wrappers import ValidationError as PydanticValidationError
import structlog

from nautobot.extras.models import ObjectChange, ChangeLoggedModel
from nautobot.utilities.utils import serialize_object
from nautobot.dcim.models import Device

from .references import (
    foreign_key_field,
    CableRef,
    ContentTypeRef,
    DeviceRef,
    DeviceTypeRef,
    StatusRef,
)
from .validation import DiffSyncCustomValidationField, netbox_pk_to_nautobot_pk


logger = structlog.get_logger()


class DjangoBaseModel(DiffSyncModel):
    """Base class for generic Django models.

    These models *have* a primary key, but in some cases (e.g., ContentType) the primary key is
    automatically generated and outside of our control.
    Hence for these models the PK is **not** automatically considered a suitable unique identifier.
    """

    _nautobot_model: models.Model
    """Django or Nautobot model class that this model maps to."""

    _fk_associations: dict = {}
    """Mapping defining translations between foreign key (FK) fields and DiffSync models.

    Automatically populated at subclass declaration time, see __init_subclass__().

    Examples:
        {"site": "site", "parent": "rackgroup"}
    """

    _importer_request_id: uuid.UUID = uuid.uuid4()
    """Consistent Request_id used across the whole import when creating ObjectChanges for ChangeLoggedModel objects."""

    pk: Union[uuid.UUID, int]

    # known fields in NetBox that should be ignored by the importer.
    # this is only for logging information, is not critical for the importer.
    _ignored_fields = {"id"}

    @property
    def ignored_fields(self):
        """Public interface for accessing class attr `_ignored_fields`."""
        return self.__class__._ignored_fields  # pylint: disable=protected-access

    @classmethod
    def __init_subclass__(cls):
        """Automatically construct cls._fk_associations."""
        super().__init_subclass__()
        cls._fk_associations = {}
        for field in cls.__fields__.values():
            if isinstance(field.type_, type) and hasattr(field.type_, "to_name"):
                cls._fk_associations[field.name] = field.type_.to_name

    @classmethod
    def nautobot_model(cls):
        """Get the Nautobot model class that this model maps to."""
        return cls._nautobot_model

    @classmethod
    def fk_associations(cls):
        """Get the mapping between foreign key (FK) fields and the corresponding DiffSync models they reference."""
        return cls._fk_associations

    @classmethod
    def _get_nautobot_record(
        cls, diffsync_model: DiffSyncModel, diffsync_value: Any, fail_quiet: bool = False
    ) -> Optional[models.Model]:
        """Given a diffsync model and identifier (natural key or primary key) look up the Nautobot record."""
        try:
            if isinstance(diffsync_value, dict):
                # Handle nested natural key references (e.g. Group -> Permission -> ContentType)
                for key, value in diffsync_value.items():
                    if isinstance(value, dict):
                        diffsync_value[key] = getattr(diffsync_model.nautobot_model(), key).get_queryset().get(**value)
                return diffsync_model.nautobot_model().objects.get(**diffsync_value)
            # Else, assume it's a primary key value
            return diffsync_model.nautobot_model().objects.get(pk=diffsync_value)
        except ObjectDoesNotExist:
            log = logger.debug if fail_quiet else logger.error
            log(
                "Expected but did not find an existing Nautobot record",
                source=cls.get_type(),
                target=diffsync_model.get_type(),
                unique_id=diffsync_value,
            )
        return None

    @classmethod
    def clean_ids_or_attrs(cls, diffsync: DiffSync, ids_or_attrs: dict) -> Tuple[dict, dict]:
        """Clean up the DiffSync "ids" or "attrs" dict to provide the keys needed to write to Nautobot.

        Specifically, for any and all foreign-key fields, which have been translated into DiffSync as
        references to natural keys (DiffSyncModel identifiers), we now need to translate them back
        into actual references to Nautobot database objects.

        Returns:
            Tuple[dict, dict]: The first is the DiffSync ids/attrs dict
                (perhaps minus a few keys if they were unresolvable references),
                the second is a dict of Nautobot model attributes corresponding to this dict.
        """
        diffsync_data = ids_or_attrs.copy()
        nautobot_data = ids_or_attrs.copy()
        foreign_key_associations = cls.fk_associations()

        for field in list(ids_or_attrs.keys()):
            # Only foreign key references need to be fixed up
            if field not in foreign_key_associations:
                continue
            # Only non-null references need to be fixed up
            diffsync_value = ids_or_attrs[field]
            if not diffsync_value:
                continue

            # What DiffSync class is this foreign key referring to?
            target_diffsync_class_name = foreign_key_associations[field]

            # GenericForeignKey references need to be dereferenced specially, because:
            # 1. The foreign key type needs to be looked up from a different field on the record
            # 2. The value for the foreign key id field needs to be a raw PK value, *not* an object reference.
            if target_diffsync_class_name.startswith("*"):
                # This field is a GenericForeignKey, whose type is based on the value of the referenced field
                target_content_type_field = target_diffsync_class_name[1:]
                target_content_type = diffsync_data[target_content_type_field]
                target_diffsync_class_name = target_content_type["model"]
                target_class = getattr(diffsync, target_diffsync_class_name)
                target_nautobot_record = cls._get_nautobot_record(target_class, diffsync_value)
                nautobot_data[field] = target_nautobot_record.pk if target_nautobot_record else None
                continue

            target_class = getattr(diffsync, target_diffsync_class_name)

            if isinstance(diffsync_value, list):
                # This is a one-to-many or many-to-many field
                nautobot_value = []
                for unique_id in list(diffsync_value):
                    # References to nonexistent content-types are "normal" and so shouldn't be logged as loud failures
                    target_nautobot_record = cls._get_nautobot_record(
                        target_class, unique_id, fail_quiet=(target_diffsync_class_name == "contenttype")
                    )
                    if target_nautobot_record:
                        nautobot_value.append(target_nautobot_record)
                    else:
                        # Something went wrong and was already logged by _get_nautobot_record
                        diffsync_value.remove(unique_id)
            elif isinstance(diffsync_value, dict) and "pk" in diffsync_value:
                # A foreign-key reference we weren't able to look up successfully.
                diffsync_value = None
                nautobot_value = None
            else:
                # This is a one-to-one or standard foreign key field
                # Due to the presence of circular reference loops in NetBox's data models,
                # we know there will be cases where we have a forward reference to a not-yet-created Nautobot object.
                # Therefore, in this case (only), we do not log loudly if the reference lookup fails.
                nautobot_value = cls._get_nautobot_record(target_class, diffsync_value, fail_quiet=True)
                if not nautobot_value:
                    diffsync_value = None

            diffsync_data[field] = diffsync_value
            nautobot_data[field] = nautobot_value

        return (diffsync_data, nautobot_data)

    @classmethod
    def clean_ids(cls, diffsync: DiffSync, ids: dict) -> Tuple[dict, dict]:
        """Translate any DiffSync "ids" fields to the corresponding Nautobot data model identifiers."""
        return cls.clean_ids_or_attrs(diffsync, ids)

    @classmethod
    def clean_attrs(cls, diffsync: DiffSync, attrs: dict) -> Tuple[dict, dict]:
        """Translate any DiffSync "attrs" fields to the corresponding Nautobot data model fields."""
        return cls.clean_ids_or_attrs(diffsync, attrs)

    @classmethod
    def create_nautobot_record(  # pylint: disable=too-many-arguments
        cls, diffsync: DiffSync, nautobot_model, ids: Mapping, attrs: Mapping, multivalue_attrs: Mapping
    ):
        """Helper method to create() - actually populate Nautobot data."""
        model_data = {**ids, **attrs, **multivalue_attrs}
        try:
            # Custom fields are a special case - because in NetBox the values defined on a particular record are
            # only loosely coupled to the CustomField definition itself, it's quite possible that these two may be
            # out of sync for various reasons. If this happens, Nautobot *will* reject the record when we call clean().
            # Rather than add a lot of complex logic here to try to "fix" out-of-sync NetBox data, we cheat and
            # only set the custom field data *after* the record has been validated and approved by Nautobot.
            custom_field_data = attrs.pop("custom_field_data", None)
            record = nautobot_model(**ids, **attrs)

            # Run model cleaning regardless of `bypass_data_validation` setting,
            # but if that flag is set, only log a warning and save the data anyway, intead of rejecting the data.
            try:
                record.clean()
            except DjangoValidationError as exc:
                if diffsync.bypass_data_validation:
                    logger.warning(
                        "Nautobot reported a data validation error - check your source data. "
                        "Since bypass_data_validation is set, will populate this into Nautobot regardless",
                        action="create",
                        exception=str(exc),
                        model=nautobot_model,
                        model_data=model_data,
                    )
                else:
                    raise

            record.save()

            # To keep track of original created date of a ChangeLoggedModel that is updated
            # when `record.save()` and to create a ChangeObject with the import change
            if issubclass(type(record), ChangeLoggedModel):
                # Not all models that are change-logged in Nautobot are also change-logged in NetBox, though!
                if "created" in model_data:
                    record.created = model_data["created"]
                    record.save()

                ObjectChange.objects.create(
                    changed_object=record,
                    object_repr=str(record),
                    action="update",
                    object_data=serialize_object(record),
                    request_id=cls._importer_request_id,
                )

            for attr, value in multivalue_attrs.items():
                getattr(record, attr).set(value)
            if custom_field_data is not None:
                record._custom_field_data = custom_field_data  # pylint: disable=protected-access
                record.save()
            return record
        except IntegrityError as exc:
            logger.error(
                "Nautobot reported a database integrity error",
                action="create",
                exception=str(exc),
                model=nautobot_model,
                model_data=model_data,
            )
        except DjangoValidationError as exc:
            logger.error(
                "Nautobot reported a data validation error - check your source data",
                action="create",
                exception=str(exc),
                model=nautobot_model,
                model_data=model_data,
            )
        except ObjectDoesNotExist as exc:  # Including RelatedObjectDoesNotExist
            logger.error(
                "Nautobot reported an error about a missing required object",
                action="create",
                exception=str(exc),
                model=nautobot_model,
                model_data=model_data,
            )

        return None

    @classmethod
    def special_clean(cls, diffsync, ids, attrs):  # pylint: disable=unused-argument
        """Subclassable method called after `clean_ids` and `clean_attrs` to do any special cleaning needed."""

    @classmethod
    def create(cls, diffsync: DiffSync, ids: Mapping, attrs: Mapping) -> Optional["NautobotBaseModel"]:
        """Create an instance of this model, both in Nautobot and in DiffSync."""
        diffsync_ids, nautobot_ids = cls.clean_ids(diffsync, ids)
        diffsync_attrs, nautobot_attrs = cls.clean_attrs(diffsync, attrs)

        cls.special_clean(diffsync, diffsync_ids, diffsync_attrs)
        cls.special_clean(diffsync, nautobot_ids, nautobot_attrs)

        # Multi-value fields (i.e. OneToMany or ManyToMany fields) need
        # to be set separately after the record is created in Nautobot
        multivalue_attrs = {}
        for attr, value in list(nautobot_attrs.items()):
            if isinstance(value, list) and attr in cls.fk_associations():
                multivalue_attrs[attr] = value
                del nautobot_attrs[attr]

        record = cls.create_nautobot_record(
            diffsync, cls.nautobot_model(), nautobot_ids, nautobot_attrs, multivalue_attrs
        )
        if record:
            if "pk" in cls._identifiers:
                diffsync_ids["pk"] = record.pk
            else:
                diffsync_attrs["pk"] = record.pk
            try:
                return super().create(diffsync, diffsync_ids, diffsync_attrs)
            except PydanticValidationError as exc:
                logger.error(
                    "Invalid data according to internal data model. "
                    "This may be an issue with your source data or may reflect a bug in this plugin.",
                    action="create",
                    exception=str(exc),
                    model=cls.get_type(),
                    model_data={**diffsync_ids, **diffsync_attrs},
                )
        return None

    @staticmethod
    def update_nautobot_record(
        diffsync: DiffSync, nautobot_model, ids: Mapping, attrs: Mapping, multivalue_attrs: Mapping
    ):
        """Helper method to update() - actually update Nautobot data."""
        model_data = {**ids, **attrs, **multivalue_attrs}
        try:
            record = nautobot_model.objects.get(**ids)
            custom_field_data = attrs.pop("custom_field_data", None)
            # Temporarily clear any existing custom field data as part of the model update,
            # so that in case the model contains "stale" data referring to no-longer-existent fields,
            # Nautobot won't reject it out of hand.
            if not custom_field_data and hasattr(record, "custom_field_data"):
                custom_field_data = record.custom_field_data
            if custom_field_data:
                record._custom_field_data = {}  # pylint: disable=protected-access
            for attr, value in attrs.items():
                setattr(record, attr, value)

            # Run model cleaning regardless of `bypass_data_validation` setting,
            # but if that flag is set, only log a warning and save the data anyway, instead of rejecting the data.
            try:
                record.clean()
            except DjangoValidationError as exc:
                if diffsync.bypass_data_validation:
                    logger.warning(
                        "Nautobot reported a data validation error - check your source data. "
                        "Since bypass_data_validation is set, will populate this into Nautobot regardless",
                        action="update",
                        exception=str(exc),
                        model=nautobot_model,
                        model_data=model_data,
                    )
                else:
                    raise

            record.save()
            for attr, value in multivalue_attrs.items():
                getattr(record, attr).set(value)
            if custom_field_data is not None:
                record._custom_field_data = custom_field_data  # pylint: disable=protected-access
                record.save()
            return record
        except IntegrityError as exc:
            logger.error(
                "Nautobot reported a database integrity error",
                action="update",
                exception=str(exc),
                model=nautobot_model,
                model_data=model_data,
            )
        except DjangoValidationError as exc:
            logger.error(
                "Nautobot reported a data validation error - check your source data",
                action="update",
                exception=str(exc),
                model=nautobot_model,
                model_data=model_data,
            )
        except ObjectDoesNotExist as exc:  # Including RelatedObjectDoesNotExist
            logger.error(
                "Nautobot reported an error about a missing required object",
                action="update",
                exception=str(exc),
                model=nautobot_model,
                model_data=model_data,
            )

        return None

    def update(self, attrs: Mapping) -> Optional["NautobotBaseModel"]:
        """Update this model instance, both in Nautobot and in DiffSync."""
        diffsync_ids, nautobot_ids = self.clean_ids(self.diffsync, self.get_identifiers())
        diffsync_attrs, nautobot_attrs = self.clean_attrs(self.diffsync, attrs)

        if not diffsync_attrs and not nautobot_attrs:
            logger.warning("No diffs remaining after cleaning up unresolved references")
            return self

        # Multi-value fields (i.e. OneToMany or ManyToMany fields) need
        # to be set individually by the set() method, so separate them out from more general attrs.
        multivalue_attrs = {}
        for attr, value in list(nautobot_attrs.items()):
            if isinstance(value, list) and attr in self.fk_associations():
                multivalue_attrs[attr] = value
                del nautobot_attrs[attr]

        record = self.update_nautobot_record(
            self.diffsync, self.nautobot_model(), nautobot_ids, nautobot_attrs, multivalue_attrs
        )
        if record:
            try:
                return super().update(diffsync_attrs)
            except PydanticValidationError as exc:
                logger.error(
                    "Invalid data according to internal data model. "
                    "This may be an issue with your source data or may reflect a bug in this plugin.",
                    action="update",
                    exception=str(exc),
                    model=self.get_type(),
                    model_data={**diffsync_ids, **diffsync_attrs},
                )

        return None

    # TODO delete() is not yet implemented


class NautobotBaseModel(DjangoBaseModel):
    """Base class for NetBox / Nautobot models.

    For this class and its subclasses, unlike DjangoBaseModel, we use the database primary key as the unique ID.
    This is in contrast with usual DiffSync best practices, which recommend the use of "natural" keys,
    but unfortunately there are a number of NetBox data models that are defined and used in such a way
    that any possible natural keys are either potentially or even intentionally non-unique.
    Since the intended use case of this implementation is for one-way synchronization only, and
    we are assuming that the standard use case is to populate an initially empty Nautobot database with
    fresh data from NetBox, we can get away with using Nautobot primary keys
    (derived from NetBox primary keys as needed, see validation.netbox_pk_to_nautobot_pk)
    as the DiffSync unique IDs for these models.
    """

    _identifiers = ("pk",)

    pk: uuid.UUID

    @validator("pk", pre=True)
    def map_netbox_pk_to_nautobot_pk(cls, value):  # pylint: disable=no-self-argument
        """Deterministically map a NetBox integer primary key to a Nautobot UUID primary key.

        One of the reasons Nautobot moved from sequential integers to UUIDs was to protect the application
        against key-enumeration attacks, so we don't use a hard-coded mapping from integer to UUID as that
        would defeat the purpose.
        """
        if not isinstance(value, uuid.UUID):
            return netbox_pk_to_nautobot_pk(cls._modelname, value)
        return value


class BaseInterfaceMixin(BaseModel):
    """An abstract model shared by dcim.Interface and virtualization.VMInterface."""

    _attributes = ("enabled", "mac_address", "mtu", "mode")

    enabled: bool
    mac_address: Optional[str]
    mtu: Optional[int]
    mode: str

    @validator("mac_address", pre=True)
    @classmethod
    def eui_to_str(cls, value):
        """Nautobot reports MAC addresses as netaddr.EUI objects; coerce them to strings."""
        if isinstance(value, netaddr.EUI):
            value = str(value)
        return value


class CableTerminationMixin(BaseModel):
    """An abstract model for objects that can terminate a Cable connection."""

    _attributes = ("cable",)

    cable: Optional[CableRef]


class ChangeLoggedModelMixin(BaseModel):
    """An abstract model which adds fields to store the creation and last-updated times for an object."""

    # last_updated is updated automatically on model create/update, so don't try to sync it between systems
    _attributes = ("created",)

    created: Optional[date]
    last_updated: Optional[datetime]

    @validator("created", pre=True)
    @classmethod
    def check_created(cls, value):
        """Pre-cleaning: in JSON dump from Django, date string is formatted differently than Pydantic expects."""
        if isinstance(value, str) and value.endswith("T00:00:00Z"):
            value = value.replace("T00:00:00Z", "")
        return value


class ConfigContextModelMixin(BaseModel):
    """An abstract model which adds local config context data."""

    # We don't presently include the local_context_data_owner since we know it doesn't exist in NetBox
    _attributes = ("local_context_data",)

    local_context_data: Optional[dict]
    local_context_data_owner_content_type: Optional[ContentTypeRef]
    _local_context_data_owner_id = foreign_key_field("*local_context_data_owner_content_type")
    local_context_data_owner_id: Optional[_local_context_data_owner_id]


class CustomFieldModelMixin(BaseModel):
    """An abstract model that adds a custom_field_data field."""

    _attributes = ("custom_field_data",)

    custom_field_data: dict = {}


class MPTTModelMixin(BaseModel):
    """An abstract model that adds fields to represent a tree structure."""

    # None of the tree fields are relevant as attributes to sync

    lft: Optional[Union[int, str]]
    rght: Optional[Union[int, str]]
    tree_id: Optional[int]
    level: Optional[int]


class StatusModelMixin(BaseModel):
    """An abstract model that has a Status field."""

    _attributes = ("status",)

    status: StatusRef


class ComponentModel(CustomFieldModelMixin, NautobotBaseModel):
    """Base class for Device components."""

    _attributes = ("device", "name", "label", "description")

    device: DeviceRef
    name: str
    label: str
    description: str

    _type_choices = None

    @root_validator
    @classmethod
    def invalid_type_to_other(cls, values):
        """
        Default invalid `type` fields to use `other` type.

        Almost all Component Models have a `type` field that uses a ChoiceSet to limit valid
        choices. This uses Pydantic's root_validator to clean up the `type` data before loading
        it into a Model instance. All invalid types will be changed to "other."

        In order for a Component Model to inherit this behavoir, the Model must define a class
        attribute named `_type_choices`. The `_type_choices` attribute should be a set of the
        valid choices for the type per Nautobot.

        If the `_type_choices` attribute is defined, then the Model should also define a `type`
        field that is required.
        """
        if cls._type_choices is None:
            return values
        component_type_value = values["type"]
        if component_type_value not in cls._type_choices:  # pylint: disable=unsupported-membership-test
            values["type"] = "other"
            component_name = values["name"]
            device_name = None
            device_pk = values["device"]
            try:
                device = Device.objects.get(pk=device_pk)
                device_name = device.name
            except Device.DoesNotExist:
                device_name = None
            logger.warning(
                f"Encountered a NetBox {cls._modelname}.type that is not valid in this version of Nautobot, will convert it",
                component_type=cls._modelname,
                component_name=component_name,
                device_name_or_pk=device_name or device_pk,
                netbox_type=component_type_value,
                nautobot_type="other",
            )
        return values


class ComponentTemplateModel(CustomFieldModelMixin, NautobotBaseModel):
    """Base class for Device component templates."""

    _attributes = ("device_type", "name", "label", "description")

    device_type: DeviceTypeRef
    name: str
    label: str
    description: str

    _type_choices: Optional[Iterable] = None

    @root_validator
    @classmethod
    def invalid_type_to_other(cls, values):
        """
        Default invalid `type` fields to use `other` type.

        Almost all Component Template Models have a `type` field that uses a ChoiceSet to limit valid
        choices. This uses Pydantic's root_validator to clean up the `type` data before loading it
        into a Model instance. All invalid types will be changed to "other."

        In order for a Component Template Model to inherit this behavoir, the Model must define a class
        attribute named `_type_choices`. The `_type_choices` attribute should be a set of the
        valid choices for the type per Nautobot.

        If the `_type_choices` attribute is defined, then the Model should also define a `type`
        field that is required.
        """
        if cls._type_choices is None:
            return values
        component_type_value = values["type"]
        if component_type_value not in cls._type_choices:  # pylint: disable=unsupported-membership-test
            values["type"] = "other"
            component_name = values["name"]
            logger.warning(
                f"Encountered a NetBox {cls._modelname}.type that is not valid in this version of Nautobot, will convert it",
                component_type=cls._modelname,
                component_name=component_name,
                netbox_type=component_type_value,
                nautobot_type="other",
            )
        return values


class OrganizationalModel(  # pylint: disable=too-many-ancestors
    ChangeLoggedModelMixin, CustomFieldModelMixin, NautobotBaseModel
):
    """Base class for organizational models in NetBox/Nautobot.

    Organizational models represent groupings, metadata, etc. rather than concrete network resources.
    """

    _attributes = (*CustomFieldModelMixin._attributes, *ChangeLoggedModelMixin._attributes)


class PrimaryModel(  # pylint: disable=too-many-ancestors
    ChangeLoggedModelMixin, CustomFieldModelMixin, NautobotBaseModel
):
    """Base class for primary models in NetBox/Nautobot.

    Primary models typically represent concrete network resources such as Device or Rack.
    """

    _attributes = (*CustomFieldModelMixin._attributes, *ChangeLoggedModelMixin._attributes)


class ArrayField(DiffSyncCustomValidationField, list):
    """Django's serialization of a PostgreSQL ArrayField is weird."""

    @classmethod
    def validate(cls, value):
        """Convert the serialized representation (a string representation of a list of strings) to a proper list."""
        if isinstance(value, str):
            value = json.loads(value)
        # For some reason the NetBox JSON export renders an ArrayField of integers as a list of strings,
        # which makes Nautobot unhappy when it tries to import them. Try to fix it up if appropriate:
        try:
            value = [int(item) for item in value]
        except ValueError:
            pass
        # Additionally, NetBox may store a list of ints in arbitrary (unsorted) order.
        # For consistent behavior, sort them:
        # TODO: this *should* be okay in all cases as I don't know of any ArrayFields
        #       in NetBox or Nautobot where maintaining order is relevant.
        value = sorted(value)
        return cls(value)
