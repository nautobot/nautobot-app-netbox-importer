"""DiffSync adapter for Nautobot database."""

from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel
from django.db import models
import structlog

from .abstract import N2NDiffSync


User = get_user_model()


IGNORED_FIELD_CLASSES = (GenericRel, GenericForeignKey, models.ManyToManyRel, models.ManyToOneRel)


class NautobotDiffSync(N2NDiffSync):
    """DiffSync adapter integrating with the Nautobot database."""

    logger = structlog.get_logger()

    def load_model(self, diffsync_model, record):
        """Instantiate the given model class from the given Django record."""
        data = {}

        # Iterate over all model fields on the Django record
        for field in record._meta.get_fields(include_hidden=True):
            if any(isinstance(field, ignored_class) for ignored_class in IGNORED_FIELD_CLASSES):
                continue

            try:
                value = field.value_from_object(record)
            except AttributeError as exc:
                self.logger.error(f"Unable to get value_from_object for {record} {field}: {exc}")
                continue

            if field.name not in diffsync_model.fk_associations():
                # Simple key-value store, no transformation needed
                data[field.name] = value
            elif value:
                # Foreign-key reference of some sort
                target_name = diffsync_model.fk_associations()[field.name]
                if target_name.startswith("*"):
                    # A generic foreign key, type is based on the value of the referenced field
                    target_content_type_field = target_name[1:]
                    target_content_type = getattr(record, target_content_type_field)
                    target_name = target_content_type.model

                try:
                    target_class = getattr(self, target_name)
                except AttributeError:
                    self.logger.warning("Don't yet know about class {target_name}")
                    continue

                if isinstance(value, list):
                    # One-to-many or many-to-many field!
                    data[field.name] = [
                        self.get_fk_identifiers(diffsync_model, target_class, foreign_record.pk)
                        for foreign_record in value
                    ]
                elif isinstance(value, (UUID, int)):
                    data[field.name] = self.get_fk_identifiers(diffsync_model, target_class, value)
                else:
                    self.logger.error(f"Invalid PK value {value}")
                    data[field.name] = None
                    continue

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
