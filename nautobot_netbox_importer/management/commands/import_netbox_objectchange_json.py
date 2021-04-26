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

    def add_arguments(self, parser):
        """Add parser arguments to the import_netbox_objectchange_json management command."""
        parser.add_argument("json_file", type=argparse.FileType("r"))
        parser.add_argument("objectchange_json_file", type=argparse.FileType("r"))
        parser.add_argument("netbox_version", type=version.parse)
        parser.add_argument("--dryrun", type=bool, default=False)

    def handle(self, *args, **options):
        """Handle execution of the import_netbox_json management command."""

        def process_objectchange(entry):
            """Processes on objectchange entry to migrate from Netbox to Nautobot."""
            try:
                entry["fields"]["changed_object_type"] = ContentType.objects.filter(
                    id=nautobot_contenttype_mapping[netbox_contenttype_mapping[entry["fields"]["changed_object_type"]]]
                ).first()
            except KeyError:
                logger.warning(
                    f'{netbox_contenttype_mapping[entry["fields"]["changed_object_type"]]} key is not mapped'
                )
                return

            if entry["fields"]["related_object_type"]:
                entry["fields"]["related_object_type"] = ContentType.objects.filter(
                    id=nautobot_contenttype_mapping[netbox_contenttype_mapping[entry["fields"]["related_object_type"]]]
                ).first()
            else:
                del entry["fields"]["related_object_type"]

            modelname = entry["fields"]["changed_object_type"].model
            entry["fields"]["changed_object_id"] = netbox_pk_to_nautobot_pk(
                modelname, entry["fields"]["changed_object_id"]
            )
            if entry["fields"]["related_object_id"]:
                modelname = entry["fields"]["related_object_type"].model
                entry["fields"]["related_object_id"] = netbox_pk_to_nautobot_pk(
                    modelname, entry["fields"]["related_object_id"]
                )

            entry["fields"]["user"] = User.objects.filter(username=entry["fields"]["user_name"]).first()
            if not entry["fields"]["user"]:
                logger.error(f'Username {entry["fields"]["user_name"]} not present in DB.')
                return

            if not options["dryrun"]:
                obj = ObjectChange.objects.create(**entry["fields"])
                obj.time = entry["fields"]["time"]
                obj.save()

        validate_netbox_version(options["netbox_version"])

        logger, _ = initialize_logger(options)

        logger.info("Loading NetBox JSON data into memory...", filename={options["json_file"].name})
        no_objectchange_data = json.load(options["json_file"])

        if not isinstance(no_objectchange_data, list):
            raise CommandError(f"Data should be a list of records, but instead is {type(no_objectchange_data)}!")
        logger.info("JSON data loaded into memory successfully.")

        logger.info("Creating NetBox ContentType mapping...")
        netbox_contenttype_mapping = {}
        for entry in no_objectchange_data:
            if entry["model"] == "contenttypes.contenttype":
                netbox_contenttype_mapping[entry["pk"]] = (
                    entry["fields"]["app_label"],
                    entry["fields"]["model"],
                )

        logger.info("Creating Nautobot ContentType mapping...")
        nautobot_contenttype_mapping = {}
        for entry in ContentType.objects.all():
            nautobot_contenttype_mapping[(entry.app_label, entry.model)] = entry.id

        logger.info("Loading ObjectChange NetBox JSON data into memory...", filename={options["json_file"].name})
        objectchange_data = json.load(options["objectchange_json_file"])
        for entry in ProgressBar(objectchange_data):
            process_objectchange(entry)

        logger.info("Processed %s in this run.", len(objectchange_data))
