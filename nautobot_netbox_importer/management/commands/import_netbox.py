"""Definition of "manage.py import_netbox" Django command for use with Nautobot."""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from packaging.version import Version

from nautobot_netbox_importer.diffsync.adapters import NetBoxAdapter, NetBoxImporterOptions

_DEFAULT_NETBOX_VERSION = str(NetBoxImporterOptions._field_defaults["netbox_version"])


class Command(BaseCommand):
    """Implementation of import_netbox command."""

    help = "Import a NetBox JSON data dump into Nautobot's database"

    def add_arguments(self, parser):
        """Add parser arguments to the import_netbox management command."""
        parser.add_argument(
            "json_file",
            help="URL or path to the JSON file to import.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Do not write any data to the database.",
        )
        parser.add_argument(
            "--update-paths",
            action="store_true",
            dest="update_paths",
            help="Call management command `trace_paths` to update paths after the import.",
        )
        parser.add_argument(
            "--bypass-data-validation",
            action="store_true",
            dest="bypass_data_validation",
            help="Bypass as much of Nautobot's internal data validation logic as possible, allowing the import of "
            "data from NetBox that would be rejected as invalid if entered as-is through the GUI or REST API. "
            "USE WITH CAUTION: it is generally more desirable to *take note* of any data validation errors, "
            "*correct* the invalid data in NetBox, and *re-import* with the corrected data!",
        )
        parser.add_argument(
            "--sitegroup-parent-always-region",
            action="store_true",
            dest="sitegroup_parent_always_region",
            help="When importing `dcim.sitegroup` to `dcim.locationtype`, always set the parent of a site group, "
            "to be a `Region` location type. This is a workaround to fix validation errors "
            "`'A Location of type Location may only have a Location of the same type as its parent.'`.",
        )
        parser.add_argument(
            "--tag-issues",
            action="store_true",
            dest="tag_issues",
            help="Whether to tag Nautobot records with any importer issues.",
        )
        parser.add_argument(
            "--deduplicate-ipam",
            action="store_true",
            dest="deduplicate_ipam",
            help="Deduplicate `ipam.prefix` and `ipam.aggregate` from NetBox. `prefix` value will be unique. (default: False)",
        )
        parser.add_argument(
            "--fix-powerfeed-locations",
            action="store_true",
            dest="fix_powerfeed_locations",
            help="Fix panel location to match rack location based on powerfeed.",
        )
        parser.add_argument(
            "--create-missing-cable-terminations",
            action="store_true",
            dest="create_missing_cable_terminations",
            help="Create missing cable terminations as Nautobot requires both cable terminations to be defined to save cable instances.",
        )
        parser.add_argument(
            "--print-summary",
            action="store_true",
            dest="print_summary",
            help="Show a summary of the import.",
        )
        parser.add_argument(
            "--no-unrack-zero-uheight-devices",
            action="store_false",
            dest="unrack_zero_uheight_devices",
            default=True,
            help="Prevents cleaning the `position` field in `dcim.device` instances that fail validation if the device is in a rack.",
        )
        parser.add_argument(
            "--save-json-summary-path",
            dest="save_json_summary_path",
            help="File path to write the JSON summary to.",
        )
        parser.add_argument(
            "--save-text-summary-path",
            dest="save_text_summary_path",
            help="File path to write the text summary to.",
        )
        parser.add_argument(
            "--trace-issues",
            action="store_true",
            dest="trace_issues",
            help="Show a detailed trace of issues originated from any `Exception` found during the import.",
        )
        parser.add_argument(
            "--customizations",
            dest="customizations",
            help="Paths to a Python module containing customizations to apply during the import. (default: empty)",
        )
        parser.add_argument(
            "--netbox-version",
            dest="netbox_version",
            help=f"SemVer NetBox version string to use for the import. (default: '{_DEFAULT_NETBOX_VERSION}')",
            default=_DEFAULT_NETBOX_VERSION,
        )

    def handle(self, json_file, **kwargs):  # type: ignore
        """Handle execution of the import_netbox management command."""
        call_command("migrate")

        customizations = (kwargs.pop("customizations") or "").split(",")
        netbox_version = Version(kwargs.pop("netbox_version", _DEFAULT_NETBOX_VERSION))

        # pylint: disable=protected-access
        keys = NetBoxImporterOptions._fields
        options = NetBoxImporterOptions(
            **{key: value for key, value in kwargs.items() if key in keys},
            customizations=customizations,
            netbox_version=netbox_version,
        )

        adapter = NetBoxAdapter(json_file, options)
        adapter.import_to_nautobot()
