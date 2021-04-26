"""Definition of "manage.py import_netbox_objectchange_json" Django command for use with Nautobot."""
import argparse
import json

from packaging import version

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import ObjectChange

from nautobot_netbox_importer.utils import ProgressBar
from nautobot_netbox_importer.command_utils import validate_netbox_version, initialize_logger
from nautobot_netbox_importer.diffsync.models.validation import netbox_pk_to_nautobot_pk


User = get_user_model()


class Command(BaseCommand):
    """Implementation of import_netbox_objectchange_json command."""

    help = "Import ObjectChange objects from NetBox YAML data dump into Nautobot's database"

    def __init__(self):
        """Init method."""
        super().__init__()
        self.logger = None
        self.netbox_contenttype_mapping = {}
        self.nautobot_contenttype_mapping = {}

    def add_arguments(self, parser):
        """Add parser arguments to the import_netbox_objectchange_json management command."""
        parser.add_argument(
            "json_file",
            type=argparse.FileType("r"),
            help=(
                "DB dumb in JSON without ObjectChange objects. "
                "Indeed, the same used in the 'import_netbox_json' command."
            ),
        )
        parser.add_argument(
            "objectchange_json_file",
            type=argparse.FileType("r"),
            help=("DB dumb in JSON wiht ONLY ObjectChange objects. "),
        )
        parser.add_argument("netbox_version", type=version.parse)
        parser.add_argument("--dryrun", type=bool, default=False)

    def process_objectchange(self, entry, options):
        """Processes one ObjectChange entry (dict) to migrate from Netbox to Nautobot."""
        try:
            app_label, modelname = self.netbox_contenttype_mapping[entry["fields"]["changed_object_type"]]
            contenttype_id = self.nautobot_contenttype_mapping[(app_label, modelname)]
            entry["fields"]["changed_object_type"] = ContentType.objects.get(id=contenttype_id)
        except KeyError:
            self.logger.warning(
                f'{self.netbox_contenttype_mapping[entry["fields"]["changed_object_type"]]} key is not mapped'
            )
            return

        if entry["fields"]["related_object_type"]:
            app_label, modelname = self.netbox_contenttype_mapping[entry["fields"]["related_object_type"]]
            contenttype_id = self.nautobot_contenttype_mapping[(app_label, modelname)]
            entry["fields"]["related_object_type"] = ContentType.objects.get(id=contenttype_id)
        else:
            del entry["fields"]["related_object_type"]

        modelname = entry["fields"]["changed_object_type"].model
        entry["fields"]["changed_object_id"] = netbox_pk_to_nautobot_pk(modelname, entry["fields"]["changed_object_id"])
        if entry["fields"]["related_object_id"]:
            modelname = entry["fields"]["related_object_type"].model
            entry["fields"]["related_object_id"] = netbox_pk_to_nautobot_pk(
                modelname, entry["fields"]["related_object_id"]
            )

        entry["fields"]["user"] = User.objects.filter(username=entry["fields"]["user_name"]).first()
        if not entry["fields"]["user"]:
            self.logger.error(f'Username {entry["fields"]["user_name"]} not present in DB.')
            return

        if not options["dryrun"]:
            obj = ObjectChange.objects.create(**entry["fields"])
            obj.time = entry["fields"]["time"]
            obj.full_clean()
            obj.save()

    def handle(self, *args, **options):
        """Handle execution of the import_netbox_json management command."""
        validate_netbox_version(options["netbox_version"])

        self.logger, _ = initialize_logger(options)

        self.logger.info("Loading NetBox JSON data into memory...", filename={options["json_file"].name})
        no_objectchange_data = json.load(options["json_file"])

        if not isinstance(no_objectchange_data, list):
            raise CommandError(f"Data should be a list of records, but instead is {type(no_objectchange_data)}!")
        self.logger.info("JSON data loaded into memory successfully.")

        self.logger.info("Creating NetBox ContentType mapping...")
        for entry in no_objectchange_data:
            if entry["model"] == "contenttypes.contenttype":
                self.netbox_contenttype_mapping[entry["pk"]] = (
                    entry["fields"]["app_label"],
                    entry["fields"]["model"],
                )
        # Freeing some memory one the object is processed
        no_objectchange_data = None

        self.logger.info("Creating Nautobot ContentType mapping...")
        for entry in ContentType.objects.all():
            self.nautobot_contenttype_mapping[(entry.app_label, entry.model)] = entry.id

        self.logger.info("Loading ObjectChange NetBox JSON data into memory...", filename={options["json_file"].name})
        objectchange_data = json.load(options["objectchange_json_file"])
        for entry in ProgressBar(objectchange_data):
            self.process_objectchange(entry, options)

        self.logger.info("Processed %s in this run.", len(objectchange_data))
