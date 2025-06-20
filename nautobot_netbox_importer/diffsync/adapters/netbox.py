"""NetBox to Nautobot Source Importer Definitions."""

from gzip import GzipFile
from pathlib import Path
from typing import Callable, Generator, NamedTuple, Sequence, Union
from urllib.parse import ParseResult, urlparse

import ijson
import requests
from django.core.management import call_command
from django.db.transaction import atomic
from packaging.version import Version

from nautobot_netbox_importer.base import GENERATOR_SETUP_MODULES, logger, register_generator_setup
from nautobot_netbox_importer.diffsync.models.cables import create_missing_cable_terminations
from nautobot_netbox_importer.diffsync.models.dcim import fix_power_feed_locations, unrack_zero_uheight_devices
from nautobot_netbox_importer.generator import SourceAdapter, SourceDataGenerator, SourceRecord
from nautobot_netbox_importer.summary import Pathable

for _name in (
    "base",
    "cables",
    "circuits",
    "content_types",
    "custom_fields",
    "dcim",
    "ipam",
    "locations",
    "object_change",
    "tags",
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
    deduplicate_ipam: bool = False
    fix_powerfeed_locations: bool = False
    sitegroup_parent_always_region: bool = False
    create_missing_cable_terminations: bool = False
    tag_issues: bool = False
    unrack_zero_uheight_devices: bool = True
    save_json_summary_path: str = ""
    save_text_summary_path: str = ""
    trace_issues: bool = False
    customizations: Sequence[str] = []
    netbox_version: Version = Version("3.7")


AdapterSetupFunction = Callable[[SourceAdapter], None]


class NetBoxAdapter(SourceAdapter):
    """NetBox Source Adapter."""

    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, input_ref: _FileRef, options: NetBoxImporterOptions, job=None, sync=None, *args, **kwargs):
        """Initialize NetBox Source Adapter."""
        super().__init__(
            name="NetBox",
            *args,
            get_source_data=_get_reader(input_ref),
            trace_issues=options.trace_issues,
            **kwargs,
        )
        self.job = job
        self.sync = sync

        self.options = options

        for name in options.customizations:
            if name:
                register_generator_setup(name)

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

        if self.options.create_missing_cable_terminations:
            create_missing_cable_terminations(self)

        self.post_load()

    def import_to_nautobot(self) -> None:
        """Import a NetBox export file into Nautobot."""
        exception = None
        commited = False
        try:
            self._atomic_import()  # type: ignore
            commited = True
        except (_DryRunException, _ImporterIssuesDetected) as error:
            exception = error
            logger.info("Data were not saved: %s", error)

        if self.options.save_json_summary_path:
            self.summary.dump(self.options.save_json_summary_path, output_format="json")
        if self.options.save_text_summary_path:
            self.summary.dump(self.options.save_text_summary_path, output_format="text")

        if commited:
            if self.options.update_paths:
                logger.info("Updating paths ...")
                call_command("trace_paths", no_input=True)
                logger.info(" ... Updating paths completed.")

            if self.options.tag_issues:
                self.nautobot.tag_issues(self.summary)  # type: ignore

        if self.options.print_summary:
            self.summary.print()

        if commited:
            logger.info("Import completed successfully.")
        else:
            logger.error("Data were not saved %s", exception)

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
            raise _ImporterIssuesDetected("Aborting the transaction: importer issues detected.")

        if self.options.dry_run:
            raise _DryRunException("Aborting the transaction: dry-run mode.")


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
