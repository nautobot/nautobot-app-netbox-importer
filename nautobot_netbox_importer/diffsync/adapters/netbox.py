"""DiffSync adapters for NetBox data dumps."""

import structlog

from .abstract import N2NDiffSync


class NetBox210DiffSync(N2NDiffSync):
    """DiffSync adapter for working with data from NetBox 2.10.x."""

    logger = structlog.get_logger()

    def __init__(self, *args, source_data=None, **kwargs):
        """Store the provided source_data for use when load() is called later."""
        self.source_data = source_data
        super().__init__(*args, **kwargs)

    def load_record(self, diffsync_model, record):
        """Instantiate the given model class from the given record."""
        data = record["fields"].copy()

        # Fixup fields that are actually foreign-key (FK) associations by replacing
        # their FK ids with the DiffSync model unique-id fields.
        for key, target_name in diffsync_model.fk_associations().items():
            if key not in data or not data[key]:
                continue

            if target_name == "status":
                # Special case as Status is a hard-coded field in NetBox, not a model reference
                data[key] = {"slug": data[key]}
                continue

            if target_name.startswith("*"):
                # Generic foreign key, based on the target name
                target_content_type_field = target_name[1:]
                target_content_type_pk = record["fields"][target_content_type_field]
                if not isinstance(target_content_type_pk, int) and not isinstance(target_content_type_pk, str):
                    self.logger.error(f"Invalid content-type PK value {target_content_type_pk}")
                    data[key] = None
                    continue
                target_content_type_record = self.get_by_pk(self.contenttype, target_content_type_pk)
                target_name = target_content_type_record.model

            # Identify the DiffSyncModel class that this FK is pointing to
            try:
                target_class = getattr(self, target_name)
            except AttributeError:
                self.logger.warning(f"Don't yet know about class {target_name}")
                data[key] = None
                continue

            if isinstance(data[key], list):
                # One-to-many or many-to-many field!
                data[key] = [self.get_fk_identifiers(diffsync_model, target_class, pk) for pk in data[key]]
            elif isinstance(data[key], (int, str)):
                data[key] = self.get_fk_identifiers(diffsync_model, target_class, data[key])
            else:
                self.logger.error(f"Invalid PK value {data[key]}")
                data[key] = None
                continue

        data["pk"] = record["pk"]
        return self.make_model(diffsync_model, data)

    def load(self):
        """Load records from the provided source_data into DiffSync."""
        self.logger.info("Loading imported source data into DiffSync...")
        for modelname in ("contenttype", *self.top_level):
            diffsync_model = getattr(self, modelname)
            self.logger.info(f"Loading all {modelname} records...")
            content_type_label = diffsync_model.nautobot_model()._meta.label_lower
            for record in self.source_data:
                if record["model"] == content_type_label:
                    self.load_record(diffsync_model, record)

        self.logger.info("Fixing up any previously unresolved object relations...")
        self.fixup_data_relations()

        self.logger.info("Data loading from source data complete.")
        # Discard the source data to free up memory
        self.source_data = None
