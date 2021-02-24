"""Definition of "manage.py import_netbox_json" Django command for use with Nautobot."""
import argparse
import json
import logging

from diffsync import DiffSyncFlags
from packaging import version
import structlog

from django.core.management.base import BaseCommand, CommandError

from nautobot_netbox_importer.diffsync.adapters import netbox_adapters, NautobotDiffSync


class Command(BaseCommand):
    """Implementation of import_netbox_json command."""

    help = "Import a NetBox YAML data dump into Nautobot's database"

    def add_arguments(self, parser):
        """Add parser arguments to the import_netbox_json management command."""
        parser.add_argument("json_file", type=argparse.FileType("r"))
        parser.add_argument("netbox_version", type=version.parse)

    @staticmethod
    def enable_logging(verbosity=0):
        """Set up structlog (as used by DiffSync) to log messages for this command."""
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        formatter = structlog.stdlib.ProcessorFormatter(processor=structlog.dev.ConsoleRenderer())
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        diffsync_logger = logging.getLogger("diffsync")
        root_logger.addHandler(handler)
        if verbosity == 0:
            root_logger.setLevel(logging.WARNING)
            diffsync_logger.setLevel(logging.WARNING)
        elif verbosity == 1:  # usual default value
            root_logger.setLevel(logging.INFO)
            diffsync_logger.setLevel(logging.WARNING)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
            diffsync_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
            diffsync_logger.setLevel(logging.INFO)
        else:
            root_logger.setLevel(logging.DEBUG)
            diffsync_logger.setLevel(logging.DEBUG)

    def handle(self, *args, **options):
        """Handle execution of the import_netbox_json management command."""
        if options["netbox_version"] < version.Version("2.10.3"):
            raise CommandError("Minimum NetBox version supported is 2.10.3")
        if options["netbox_version"] > version.Version("2.10.4"):
            raise CommandError("Maximum NetBox version supported is 2.10.4")

        self.enable_logging(verbosity=options["verbosity"])
        logger = structlog.get_logger()

        logger.info("Loading NetBox JSON data into memory...", filename={options["json_file"].name})
        data = json.load(options["json_file"])

        if not isinstance(data, list):
            raise CommandError(f"Data should be a list of records, but instead is {type(data)}!")
        logger.info("JSON data loaded into memory successfully.")

        source = netbox_adapters[options["netbox_version"]](source_data=data)
        source.load()

        target = NautobotDiffSync()
        target.load()

        # Due to the fact that model inter-references do not form an acyclic graph,
        # there is no ordering of models that we can follow that allows for the creation
        # of all possible references in a single linear pass.
        # The first pass should always suffice to create all required models;
        # a second pass ensures that (now that we have all models) we set all model references.
        target.sync_from(source, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)
        summary_1 = target.sync_summary()
        logger.info("First-pass synchronization complete, beginning second pass")
        target.sync_from(source, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)
        summary_2 = target.sync_summary()
        logger.info("Synchronization complete!", first_pass=summary_1, second_pass=summary_2)
