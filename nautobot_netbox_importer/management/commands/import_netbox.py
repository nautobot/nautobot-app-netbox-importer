"""Definition of "manage.py import_netbox" Django command for use with Nautobot."""
import argparse

from django.core.management.base import BaseCommand

from nautobot_netbox_importer.diffsync.netbox import sync_to_nautobot


class Command(BaseCommand):
    """Implementation of import_netbox command."""

    help = "Import a NetBox YAML data dump into Nautobot's database"

    def add_arguments(self, parser):
        """Add parser arguments to the import_netbox management command."""
        parser.add_argument(
            "json_file",
            type=argparse.FileType("r"),
            help="Path to the JSON file to import.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Do not write any data to the database.",
        )
        parser.add_argument(
            "--summary",
            action="store_true",
            dest="summary",
            help="Show a summary of the import.",
        )
        parser.add_argument(
            "--field-mapping",
            action="store_true",
            dest="field_mapping",
            help="Show a mapping of NetBox fields to Nautobot fields.",
        )
        parser.add_argument(
            "--update-paths",
            action="store_true",
            dest="update_paths",
            help="Call management command to update paths after the import.",
        )
        parser.add_argument(
            "--bypass-data-validation",
            action="store_true",
            help="Bypass as much of Nautobot's internal data validation logic as possible, allowing the import of "
            "data from NetBox that would be rejected as invalid if entered as-is through the GUI or REST API. "
            "USE WITH CAUTION: it is generally more desirable to *take note* of any data validation errors, "
            "*correct* the invalid data in NetBox, and *re-import* with the corrected data!",
        )

    def handle(self, json_file, **options):
        """Handle execution of the import_netbox management command."""
        sync_to_nautobot(json_file.name, **options)
