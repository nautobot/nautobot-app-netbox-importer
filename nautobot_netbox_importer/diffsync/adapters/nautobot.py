"""DiffSync adapter for Nautobot database."""

from uuid import UUID

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel
from django.db import models
import structlog

from .abstract import N2NDiffSync
from ..models.abstract import NautobotBaseModel


IGNORED_FIELD_CLASSES = (GenericRel, GenericForeignKey, models.ManyToManyRel, models.ManyToOneRel)
"""Field types that will appear in record._meta.get_fields() but can be generally ignored.

The `*Rel` models are reverse-lookup relations and are not "real" fields on the model.

We handle GenericForeignKeys by managing their component `content_type` and `id` fields separately.
"""


class NautobotDiffSync(N2NDiffSync):
    """DiffSync adapter integrating with the Nautobot database."""

    logger = structlog.get_logger()

    def load_model(self, diffsync_model, record):  # pylint: disable=too-many-branches
        """Instantiate the given DiffSync model class from the given Django record."""
        data = {}

        # Iterate over all model fields on the Django record
        for field in record._meta.get_fields(include_hidden=True):
            if any(isinstance(field, ignored_class) for ignored_class in IGNORED_FIELD_CLASSES):
                continue

            # Get the value of this field from Django
            try:
                value = field.value_from_object(record)
            except AttributeError as exc:
                self.logger.error(f"Unable to get value_from_object for {record} {field}: {exc}")
                continue

            if field.name not in diffsync_model.fk_associations():
                # Field is a simple data type (str, int, bool) and can be used as-is with no modifications
                data[field.name] = value
                continue

            # If we got here, the field is some sort of foreign-key reference(s).
            if not value:
                # It's a null or empty list reference though, so we don't need to do anything special with it.
                data[field.name] = value
                continue

            # What's the name of the model that this is a reference to?
            target_name = diffsync_model.fk_associations()[field.name]

            # Special case: for generic foreign keys, the target_name is actually the name of
            # another field on this record that describes the content-type of this foreign key id.
            # We flag this by starting the target_name string with a '*', as if this were C or something.
            if target_name.startswith("*"):
                target_content_type_field = target_name[1:]
                target_content_type = getattr(record, target_content_type_field)
                target_name = target_content_type.model

            try:
                # Get the DiffSync model class that we know by the given target_name
                target_class = getattr(self, target_name)
            except AttributeError:
                self.logger.error("Unknown/unrecognized class name!", name=target_name)
                data[field.name] = None
                continue

            if not issubclass(target_class, NautobotBaseModel):
                # TODO something isn't quite right, we shouldn't need all three of these branches!
                if isinstance(value, list):
                    data[field.name] = [self.get_by_pk(target_name, obj.pk).get_identifiers() for obj in value]
                elif isinstance(value, int):
                    data[field.name] = self.get_by_pk(target_name, value).get_identifiers()
                else:
                    data[field.name] = self.get_by_pk(target_name, value.pk).get_identifiers()
                continue

            if isinstance(value, list):
                # This field is a one-to-many or many-to-many field, a list of foreign key references.
                # For each foreign key, find the corresponding DiffSync record, and use its
                # natural keys (identifiers) in the data in place of the foreign key value.
                data[field.name] = [foreign_record.pk for foreign_record in value]
            elif isinstance(value, UUID):
                # Look up the DiffSync record corresponding to this foreign key,
                # and store its natural keys (identifiers) in the data in place of the foreign key value.
                data[field.name] = value
            else:
                self.logger.error(f"Invalid PK value {value}")
                data[field.name] = None

        data["pk"] = record.pk
        return self.make_model(diffsync_model, data)

    def load(self):
        """Load all available and relevant data from Nautobot in the appropriate sequence."""
        self.logger.info("Loading data from Nautobot into DiffSync...")
        for modelname in ("contenttype", "status", *self.top_level):
            diffsync_model = getattr(self, modelname)
            self.logger.info(f"Loading all {modelname} records...")
            for instance in diffsync_model.nautobot_model().objects.all():
                self.load_model(diffsync_model, instance)

        self.logger.info("Fixing up any previously unresolved object relations...")
        self.fixup_data_relations()

        self.logger.info("Data loading from Nautobot complete.")
