"""Utility functions and classes for nautobot_netbox_importer."""
from io import StringIO
import pprint
import textwrap

import colorama

import structlog


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
                rendered_dict = pprint.pformat(value)
                if len(rendered_dict.splitlines()) > 50:
                    rendered_dict = "\n".join(rendered_dict.splitlines()[:50]) + "\n...}"
                value = "\n" + textwrap.indent(rendered_dict, "    ")
            sio.write(
                f"\n  {colorama.Fore.CYAN}{key}{colorama.Style.RESET_ALL}: "
                f"{colorama.Fore.MAGENTA}{value}{colorama.Style.RESET_ALL}"
            )

        return sio.getvalue()


def enable_logging(verbosity=0, color=None):
    """Set up structlog (as used by DiffSync) to log messages for this command."""
    if color is None:
        # Let colorama decide whether or not to strip out color codes
        colorama.init()
    else:
        # Force colors or non-colors, as specified
        colorama.init(strip=not color)

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


def initialize_logger(options):
    """Initialize logger instance."""
    # Default of None means to use colorama's autodetection to determine whether or not to use color
    color = None
    if options.get("force_color"):
        color = True
    if options.get("no_color"):
        color = False

    enable_logging(verbosity=options["verbosity"], color=color)
    return structlog.get_logger(), color
