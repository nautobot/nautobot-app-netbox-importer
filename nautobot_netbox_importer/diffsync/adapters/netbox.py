"""NetBox to Nautobot Source Importer Definitions."""

from gzip import GzipFile
from pathlib import Path
from typing import Callable
from typing import Generator
from typing import NamedTuple
from typing import Union
from urllib.parse import ParseResult
from urllib.parse import urlparse

import ijson
import requests
from django.core.management import call_command
from django.db.transaction import atomic

from nautobot_netbox_importer.base import GENERATOR_SETUP_MODULES
from nautobot_netbox_importer.base import logger
from nautobot_netbox_importer.base import register_generator_setup
from nautobot_netbox_importer.diffsync.models.dcim import fix_power_feed_locations
from nautobot_netbox_importer.diffsync.models.dcim import unrack_zero_uheight_devices
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceDataGenerator
from nautobot_netbox_importer.generator import SourceRecord
from nautobot_netbox_importer.summary import Pathable

for _name in (
    "base",
    "circuits",
    "custom_fields",
    "dcim",
    "ipam",
    "locations",
    "object_change",
    "virtualization",
):
    register_generator_setup(f"nautobot_netbox_importer.diffsync.models.{_name}")

_FileRef = Union[str, Path, ParseResult]
_HTTP_TIMEOUT = 60


class _DryRunException(Exception):
    """Exception raised when a dry-run is requested."""


class _ImporterIssuesDetected(Exception):
    """Exception raised when importer issues are detected."""


class NetBoxImporterOptions(NamedTuple):
    """NetBox importer options."""

    dry_run: bool = True
    bypass_data_validation: bool = False
    print_summary: bool = False
    update_paths: bool = False
    fix_powerfeed_locations: bool = False
    sitegroup_parent_always_region: bool = False
    unrack_zero_uheight_devices: bool = True
    save_json_summary_path: str = ""
    save_text_summary_path: str = ""


AdapterSetupFunction = Callable[[SourceAdapter], None]


class NetBoxAdapter(SourceAdapter):
    """NetBox Source Adapter."""

    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, input_ref: _FileRef, options: NetBoxImporterOptions, job=None, sync=None, *args, **kwargs):
        """Initialize NetBox Source Adapter."""
        super().__init__(name="NetBox", get_source_data=_get_reader(input_ref), *args, **kwargs)
        self.job = job
        self.sync = sync

        self.options = options

        for name in GENERATOR_SETUP_MODULES:
            setup = __import__(name, fromlist=["setup"]).setup
            setup(self)

    def load(self) -> None:
        """Load data from NetBox."""
        self.import_data()
        if self.options.fix_powerfeed_locations:
            fix_power_feed_locations(self)
        if self.options.unrack_zero_uheight_devices:
            unrack_zero_uheight_devices(self)
        self.post_import()

    def import_to_nautobot(self) -> None:
        """Import a NetBox export file into Nautobot."""
        commited = False
        try:
            self._atomic_import()
            commited = True
        except _DryRunException:
            logger.warning("Dry-run mode, no data has been imported.")
        except _ImporterIssuesDetected:
            logger.warning("Importer issues detected, no data has been imported.")

        if commited and self.options.update_paths:
            logger.info("Updating paths ...")
            call_command("trace_paths", no_input=True)
            logger.info(" ... Updating paths completed.")

        if self.options.print_summary:
            self.summary.print()

    @atomic
    def _atomic_import(self) -> None:
        self.load()

        diff = self.nautobot.sync_from(self)
        self.summarize(diff.summary())

        if self.options.save_json_summary_path:
            self.summary.dump(self.options.save_json_summary_path, output_format="json")
        if self.options.save_text_summary_path:
            self.summary.dump(self.options.save_text_summary_path, output_format="text")

        has_issues = any(True for item in self.summary.nautobot if item.issues)
        if has_issues and not self.options.bypass_data_validation:
            raise _ImporterIssuesDetected("Importer issues detected, aborting the transaction.")

        if self.options.dry_run:
            raise _DryRunException("Aborting the transaction due to the dry-run mode.")


def _read_stream(stream) -> Generator[SourceRecord, None, None]:
    for item in ijson.items(stream, "item"):
        content_type = item["model"]
        netbox_pk = item.get("pk", None)
        source_data = item["fields"]

        if netbox_pk:
            source_data["id"] = netbox_pk

        yield SourceRecord(content_type, source_data)


def _get_reader_from_path(path: Pathable) -> SourceDataGenerator:
    result = Path(path)
    if not result.is_file():
        raise FileNotFoundError(f"File {path} does not exist.")

    def reader():
        with open(result, "rb") as file:
            yield from _read_stream(file)

    return reader


def _get_reader_from_url(url: ParseResult) -> SourceDataGenerator:
    def reader():
        with requests.get(url.geturl(), stream=True, timeout=_HTTP_TIMEOUT) as response:
            response.raise_for_status()
            if response.headers.get("Content-Encoding") == "gzip":
                stream = GzipFile(fileobj=response.raw)
            else:
                stream = response.raw

            yield from _read_stream(stream)

    return reader


def _get_reader(input_ref: _FileRef) -> SourceDataGenerator:
    """Read NetBox source file from file or HTTP resource."""
    if isinstance(input_ref, str):
        url = urlparse(input_ref)

        if not url.scheme:
            return _get_reader_from_path(input_ref)

        if url.scheme == "file":
            return _get_reader_from_path(url.path)

        if url.scheme in ["http", "https"]:
            return _get_reader_from_url(url)

    if isinstance(input_ref, Path):
        return _get_reader_from_path(input_ref)

    if isinstance(input_ref, ParseResult):
        return _get_reader_from_url(input_ref)

    raise ValueError(f"Unsupported file reference: {input_ref}")
