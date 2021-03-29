"""DiffSync adapters for NetBox data dumps."""

from uuid import UUID

import structlog
from tqdm import tqdm

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
                # Null reference, no processing required.
                continue

            if target_name == "status":
                # Special case as Status is a hard-coded field in NetBox, not a model reference
                # Construct an appropriately-formatted mock natural key and use that instead
                # TODO: we could also do this with a custom validator on the StatusRef model; might be better?
                data[key] = {"slug": data[key]}
                continue

            # In the case of generic foreign keys, we have to actually check a different field
            # on the DiffSync model to determine the model type that this foreign key is referring to.
            # By convention, we label such fields with a '*', as if this were a C pointer.
            if target_name.startswith("*"):
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
                self.logger.warning("Unknown/unrecognized class name!", name=target_name)
                data[key] = None
                continue

            if isinstance(data[key], list):
                # This field is a one-to-many or many-to-many field, a list of foreign key references.
                # For each foreign key, find the corresponding DiffSync record, and use its
                # natural keys (identifiers) in the data in place of the foreign key value.
                data[key] = [self.get_fk_identifiers(diffsync_model, target_class, pk) for pk in data[key]]
            elif isinstance(data[key], (UUID, int)):
                # Look up the DiffSync record corresponding to this foreign key,
                # and store its natural keys (identifiers) in the data in place of the foreign key value.
                data[key] = self.get_fk_identifiers(diffsync_model, target_class, data[key])
            else:
                self.logger.error(f"Invalid PK value {data[key]}")
                data[key] = None

        data["pk"] = record["pk"]
        return self.make_model(diffsync_model, data)

    def load(self):
        """Load records from the provided source_data into DiffSync."""
        self.logger.info("Loading imported NetBox source data into DiffSync...")
        for modelname in ("contenttype", *self.top_level):
            diffsync_model = getattr(self, modelname)
            self.logger.info("Loading NetBox records...", model=modelname)
            content_type_label = diffsync_model.nautobot_model()._meta.label_lower
            records = [record for record in self.source_data if record["model"] == content_type_label]
            for record in tqdm(records, disable=(self.verbosity < 1)):
                self.load_record(diffsync_model, record)

        self.logger.info("Fixing up any previously unresolved object relations...")
        self.fixup_data_relations()

        self.logger.info("Data loading from NetBox source data complete.")
        # Discard the source data to free up memory
        self.source_data = None
