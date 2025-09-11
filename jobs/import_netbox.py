from nautobot.apps.jobs import Job, BooleanVar, FileVar, register_jobs, StringVar
from packaging.version import Version

from nautobot_netbox_importer.diffsync.adapters import NetBoxAdapter, NetBoxImporterOptions

_DEFAULT_NETBOX_VERSION = str(NetBoxImporterOptions._field_defaults["netbox_version"])


class NetBoxImporter(Job):
    """Import data from a NetBox JSON export file into Nautobot."""

    json_file = FileVar(
        description="Upload a NetBox JSON export file.",
        label="NetBox JSON File",
        required=True,
    )

    dry_run = BooleanVar(
        description="Do not write any data to the database.",
        label="Dry Run",
        required=False,
    )

    update_paths = BooleanVar(
        description="Call management command `trace_paths` to update paths after the import.",
        label="Update Paths",
        required=False,
    )

    bypass_data_validation = BooleanVar(
        description=(
            "Bypass as much of Nautobot's internal data validation logic as possible, allowing the import of "
            "data from NetBox that would be rejected as invalid if entered as-is through the GUI or REST API. "
            "USE WITH CAUTION: it is generally more desirable to *take note* of any data validation errors, "
            "*correct* the invalid data in NetBox, and *re-import* with the corrected data!"
        ),
        label="Bypass Data Validation",
        required=False,
    )
    sitegroup_parent_always_region = BooleanVar(
        description=(
            "When importing `dcim.sitegroup` to `dcim.locationtype`, always set the parent of a site group, "
            "to be a `Region` location type. This is a workaround to fix validation errors "
            "`'A Location of type Location may only have a Location of the same type as its parent.'`."
        ),
        label="SiteGroup Parent Always Region",
        required=False,
    )

    tag_issues = BooleanVar(
        description="Whether to tag Nautobot records with any importer issues.",
        label="Tag Issues",
        required=False,
    )

    deduplicate_ipam = BooleanVar(
        description="Deduplicate `ipam.prefix` and `ipam.aggregate` from NetBox. `prefix` value will be unique.",
        label="Deduplicate IPAM",
        required=False,
    )

    fix_powerfeed_locations = BooleanVar(
        description="Fix panel location to match rack location based on powerfeed.",
        label="Fix PowerFeed Locations",
        required=False,
    )

    create_missing_cable_terminations = BooleanVar(
        description="Create missing cable terminations based on existing cables.",
        label="Create Missing Cable Terminations",
        required=False,
    )

    print_summary = BooleanVar(
        description="Show a summary of the import.",
        label="Print Summary",
        required=False,
    )

    unrack_zero_uheight_devices = BooleanVar(
        description="Prevents cleaning the `position` field in `dcim.device` instances that fail validation if the device is in a rack.",
        label="Unrack Zero U-Height Devices",
        required=False,
    )

    save_json_summary = BooleanVar(
        description="Generate a JSON summary file of the import.",
        label="Save JSON Summary",
        required=False,
    )

    save_text_summary = BooleanVar(
        description="Generate a text summary file of the import.",
        label="Save Text Summary",
        required=False,
    )

    netbox_version = StringVar(
        description="The version of NetBox that the JSON export file was generated from. This is used to handle any differences in the data model between versions.",
        label="NetBox Version",
        required=False,
        default=_DEFAULT_NETBOX_VERSION
    )

    def run(self, json_file, *args, **kwargs):
        # customizations = (args.pop("customizations") or "").split(",")
        netbox_version = Version(args.pop("netbox_version", _DEFAULT_NETBOX_VERSION))
        keys = NetBoxImporterOptions._fields
        options = NetBoxImporterOptions(
            **{key: value for key, value in kwargs.items() if key in keys},
            netbox_version=netbox_version,
        )

        adapter = NetBoxAdapter(json_file, options)
        adapter.import_to_nautobot()


register_jobs(NetBoxImporter)