"""Definition of "manage.py import_netbox_json" Django command for use with Nautobot."""
import argparse
import json

from diffsync import DiffSyncFlags
from packaging import version

from django.core.management.base import BaseCommand, CommandError

from nautobot_netbox_importer.diffsync.adapters import netbox_adapters, NautobotDiffSync
from nautobot_netbox_importer.utils import ProgressBar
from nautobot_netbox_importer.command_utils import validate_netbox_version, enable_logging, initialize_logger


class Command(BaseCommand):
    """Implementation of import_netbox_json command."""

    help = "Import a NetBox YAML data dump into Nautobot's database"

    def add_arguments(self, parser):
        """Add parser arguments to the import_netbox_json management command."""
        parser.add_argument("json_file", type=argparse.FileType("r"))
        parser.add_argument("netbox_version", type=version.parse)

    def handle(self, *args, **options):
        """Handle execution of the import_netbox_json management command."""
        validate_netbox_version(options["netbox_version"])

        logger, color = initialize_logger(options)

        logger.info("Loading NetBox JSON data into memory...", filename={options["json_file"].name})
        data = json.load(options["json_file"])

        if not isinstance(data, list):
            raise CommandError(f"Data should be a list of records, but instead is {type(data)}!")
        logger.info("JSON data loaded into memory successfully.")

        source = netbox_adapters[options["netbox_version"]](source_data=data, verbosity=options["verbosity"])
        source.load()

        target = NautobotDiffSync(verbosity=options["verbosity"])
        target.load()

        # Lower the verbosity of newly created structlog loggers by one (half-) step
        # This is so that DiffSync's internal logging defaults to slightly less verbose than
        # our own (plugin) logging.
        enable_logging(verbosity=(options["verbosity"] - 1), color=color)

        logger.info("Beginning data synchronization...")
        # Due to the fact that model inter-references do not form an acyclic graph,
        # there is no ordering of models that we can follow that allows for the creation
        # of all possible references in a single linear pass.
        # The first pass should always suffice to create all required models;
        # a second pass ensures that (now that we have all models) we set all model references.
        with ProgressBar(verbosity=options["verbosity"]) as p_bar:
            target.sync_from(source, flags=DiffSyncFlags.SKIP_UNMATCHED_DST, callback=p_bar.diffsync_callback)
        summary_1 = target.sync_summary()
        logger.info("First-pass synchronization complete, beginning second pass")
        with ProgressBar(verbosity=options["verbosity"]) as p_bar:
            target.sync_from(source, flags=DiffSyncFlags.SKIP_UNMATCHED_DST, callback=p_bar.diffsync_callback)
        summary_2 = target.sync_summary()
        logger.info("Synchronization complete!", first_pass=summary_1, second_pass=summary_2)
