"""Definition of "manage.py import_netbox_json" Django command for use with Nautobot."""
import argparse
from io import StringIO
import json
import pprint
import textwrap

import colorama
from diffsync import DiffSyncFlags
from packaging import version
import structlog

from django.core.management.base import BaseCommand, CommandError

from nautobot_netbox_importer.diffsync.adapters import netbox_adapters, NautobotDiffSync
from nautobot_netbox_importer.utils import ProgressBar


class LogRenderer:  # pylint: disable=too-few-public-methods
    """Class for rendering structured logs to the console in a human-readable format.

    Example:
        19:48:19 Apparent duplicate object encountered?
          duplicate_id:
            {'group': None,
            'name': 'CR02.CHI_ORDMGMT',
            'site': {'name': 'CHI01'},
            'vid': 1000}
          model: vlan
          pk_1: 3baf142d-dd90-4379-a048-3bbbcc9c799c
          pk_2: cba19791-4d59-4ddd-a5c9-d969ec3ed2ba
    """

    def __call__(
        self,
        logger: structlog.types.WrappedLogger,
        name: str,
        event_dict: structlog.types.EventDict,
    ) -> str:
        """Render the given event_dict to a string."""
        sio = StringIO()

        timestamp = event_dict.pop("timestamp", None)
        if timestamp is not None:
            sio.write(f"{colorama.Style.DIM}{timestamp}{colorama.Style.RESET_ALL} ")

        level = event_dict.pop("level", None)
        if level is not None:
            if level in ("warning", "error", "critical"):
                sio.write(f"{colorama.Fore.RED}{level:<9}{colorama.Style.RESET_ALL}")
            else:
                sio.write(f"{level:<9}")

        event = event_dict.pop("event", None)
        sio.write(f"{colorama.Style.BRIGHT}{event}{colorama.Style.RESET_ALL}")

        for key, value in event_dict.items():
            if isinstance(value, dict):
                # We could use json.dumps() here instead of pprint.pformat,
                # but I find pprint to be a bit more compact while still readable.
                value = "\n" + textwrap.indent(pprint.pformat(value), "    ")
            sio.write(
                f"\n  {colorama.Fore.CYAN}{key}{colorama.Style.RESET_ALL}: "
                f"{colorama.Fore.MAGENTA}{value}{colorama.Style.RESET_ALL}"
            )

        return sio.getvalue()


class Command(BaseCommand):
    """Implementation of import_netbox_json command."""

    help = "Import a NetBox YAML data dump into Nautobot's database"

    def add_arguments(self, parser):
        """Add parser arguments to the import_netbox_json management command."""
        parser.add_argument("json_file", type=argparse.FileType("r"))
        parser.add_argument("netbox_version", type=version.parse)

    @staticmethod
    def enable_logging(verbosity=0, color=None):
        """Set up structlog (as used by DiffSync) to log messages for this command."""
        if color is None:
            # Let colorama decide whether or not to strip out color codes
            colorama.init()
        else:
            # Force colors or non-colors, as specified
            colorama.init(strip=(not color))

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="%H:%M:%S"),
                LogRenderer(),
            ],
            context_class=dict,
            # Logging levels aren't very granular, so we adjust the log level based on *half* the verbosity level:
            # Verbosity     Logging level
            # 0             30 (WARNING)
            # 1-2           20 (INFO)
            # 3+            10 (DEBUG)
            wrapper_class=structlog.make_filtering_bound_logger(10 * (3 - ((verbosity + 1) // 2))),
            cache_logger_on_first_use=True,
        )

    def handle(self, *args, **options):
        """Handle execution of the import_netbox_json management command."""
        if options["netbox_version"] not in netbox_adapters:
            supported_versions = sorted(netbox_adapters.keys())
            min_version = supported_versions[0]
            max_version = supported_versions[-1]
            if options["netbox_version"] < min_version:
                raise CommandError(f"Minimum NetBox version supported is {min_version}")
            if options["netbox_version"] > max_version:
                raise CommandError(f"Maximum NetBox version supported is {max_version}")
            raise CommandError(f"Unrecognized NetBox version; supported versions are {', '.join(supported_versions)}")

        # Default of None means to use colorama's autodetection to determine whether or not to use color
        color = None
        if options.get("force_color"):
            color = True
        if options.get("no_color"):
            color = False

        self.enable_logging(verbosity=options["verbosity"], color=color)
        logger = structlog.get_logger()

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
        self.enable_logging(verbosity=(options["verbosity"] - 1), color=color)

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
