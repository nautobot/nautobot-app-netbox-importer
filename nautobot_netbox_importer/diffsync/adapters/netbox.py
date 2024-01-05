"""NetBox to Nautobot Source Importer Definitions."""
from gzip import GzipFile
from pathlib import Path
from typing import Generator
from typing import NamedTuple
from typing import Union
from urllib.parse import ParseResult
from urllib.parse import urlparse

import ijson
import requests
from django.core.management import call_command
from django.db.transaction import atomic

from nautobot_netbox_importer.generator import DiffSummary
from nautobot_netbox_importer.generator import RecordData
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceRecord
from nautobot_netbox_importer.generator import logger
from nautobot_netbox_importer.generator import print_summary

from nautobot_netbox_importer.diffsync.models.base import setup_base
from nautobot_netbox_importer.diffsync.models.circuits import setup_circuits
from nautobot_netbox_importer.diffsync.models.dcim import fix_power_feed_locations
from nautobot_netbox_importer.diffsync.models.dcim import setup_dcim
from nautobot_netbox_importer.diffsync.models.ipam import setup_ipam
from nautobot_netbox_importer.diffsync.models.locations import setup_locations
from nautobot_netbox_importer.diffsync.models.virtualization import setup_virtualization

_FileRef = Union[str, Path, ParseResult]

_HTTP_TIMEOUT = 60


class _DryRunException(Exception):
    """Exception raised when a dry-run is requested."""


class _ValidationIssuesDetected(Exception):
    """Exception raised when validation issues are detected."""


class NetBoxImporterOptions(NamedTuple):
    """NetBox importer options."""

    dry_run: bool = True
    bypass_data_validation: bool = False
    summary: bool = False
    field_mapping: bool = False
    update_paths: bool = False
    fix_powerfeed_locations: bool = False
    sitegroup_parent_always_region: bool = False


class NetBoxAdapter(SourceAdapter):
    """NetBox Source Adapter."""

    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, input_ref: _FileRef, options: NetBoxImporterOptions, job=None, sync=None, *args, **kwargs):
        """Initialize NetBox Source Adapter."""
        super().__init__(name="NetBox", get_source_data=_get_reader(input_ref), *args, **kwargs)
        self.job = job
        self.sync = sync

        self.options = options
        self.diff_summary: DiffSummary = {}

        setup_base(self)
        setup_locations(self, options.sitegroup_parent_always_region)
        setup_dcim(self)
        setup_circuits(self)
        setup_ipam(self)
        setup_virtualization(self)

    def load(self) -> None:
        """Load data from NetBox."""
        self.import_data()
        if self.options.fix_powerfeed_locations:
            fix_power_feed_locations(self)
        self.post_import()

    def import_to_nautobot(self) -> None:
        """Import a NetBox export file into Nautobot."""
        commited = False
        try:
            self._atomic_import()
            commited = True
        except _DryRunException:
            logger.warning("Dry-run mode, no data has been imported.")
        except _ValidationIssuesDetected:
            logger.warning("Data validation issues detected, no data has been imported.")

        if commited and self.options.update_paths:
            logger.info("Updating paths ...")
            call_command("trace_paths", no_input=True)
            logger.info(" ... Updating paths completed.")

        if self.options.summary:
            print_summary(self, self.diff_summary, self.options.field_mapping)

    @atomic
    def _atomic_import(self) -> None:
        self.load()

        diff = self.nautobot.sync_from(self)
        self.diff_summary = diff.summary()

        if self.nautobot.validation_issues and not self.options.bypass_data_validation:
            raise _ValidationIssuesDetected("Data validation issues detected, aborting the transaction.")

        if self.options.dry_run:
            raise _DryRunException("Aborting the transaction due to the dry-run mode.")


def _get_reader(input_ref: _FileRef):
    """Read NetBox source file from file or HTTP resource."""

    def process_cable_termination(source_data: RecordData) -> str:
        # NetBox 3.3 split the dcim.cable model into dcim.cable and dcim.cabletermination models.
        cable_end = source_data.pop("cable_end").lower()
        source_data["id"] = source_data.pop("cable")
        source_data[f"termination_{cable_end}_type"] = source_data.pop("termination_type")
        source_data[f"termination_{cable_end}_id"] = source_data.pop("termination_id")

        return f"dcim.cabletermination_{cable_end}"

    def read_item(item: dict) -> SourceRecord:
        content_type = item["model"]
        netbox_pk = item.get("pk", None)
        source_data = item["fields"]

        if netbox_pk:
            source_data["id"] = netbox_pk

        if content_type == "dcim.cabletermination":
            content_type = process_cable_termination(source_data)

        return SourceRecord(content_type, source_data)

    def read_path() -> Generator[SourceRecord, None, None]:
        with open(path, "rb") as file:
            for item in ijson.items(file, "item"):
                yield read_item(item)

    def read_url() -> Generator[SourceRecord, None, None]:
        with requests.get(url.geturl(), stream=True, timeout=_HTTP_TIMEOUT) as response:
            response.raise_for_status()
            if response.headers.get("Content-Encoding") == "gzip":
                stream = GzipFile(fileobj=response.raw)
            else:
                stream = response.raw

            for item in ijson.items(stream, "item"):
                yield read_item(item)

    def verify_file(file_path) -> Path:
        result = Path(file_path)
        if not result.is_file():
            raise FileNotFoundError(f"File {input_ref} does not exist.")
        return result

    if isinstance(input_ref, str):
        url = urlparse(input_ref)

        if not url.scheme:
            path = verify_file(input_ref)
            return read_path

        if url.scheme == "file":
            path = verify_file(url.path)
            return read_path

        if url.scheme in ["http", "https"]:
            return read_url

    if isinstance(input_ref, Path):
        path = verify_file(input_ref)
        return read_path

    if isinstance(input_ref, ParseResult):
        url = input_ref
        return read_url

    raise ValueError(f"Unsupported file reference: {input_ref}")
