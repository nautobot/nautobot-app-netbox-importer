"""Definition of "manage.py import_netbox_json" Django command for use with Nautobot."""
import argparse
import json

from django.core.management.base import BaseCommand
from packaging import version

from nautobot_netbox_importer.diffsync.netbox import sync_to_nautobot


class Command(BaseCommand):
    """Implementation of import_netbox_json command."""

    help = "Import a NetBox YAML data dump into Nautobot's database"

    def add_arguments(self, parser):
        """Add parser arguments to the import_netbox_json management command."""
        parser.add_argument("json_file", type=argparse.FileType("r"))
        parser.add_argument("netbox_version", type=version.parse)
        parser.add_argument(
            "--bypass-data-validation",
            action="store_true",
            help="Bypass as much of Nautobot's internal data validation logic as possible, allowing the import of "
            "data from NetBox that would be rejected as invalid if entered as-is through the GUI or REST API. "
            "USE WITH CAUTION: it is generally more desirable to *take note* of any data validation errors, "
            "*correct* the invalid data in NetBox, and *re-import* with the corrected data! ",
        )

    def handle(self, *_args, **options):
        """Handle execution of the import_netbox_json management command."""
        sync_to_nautobot(json.load(options["json_file"]))
