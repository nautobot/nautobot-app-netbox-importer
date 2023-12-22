"""NetBox to Nautobot Source Importer Definitions."""
import json
from pathlib import Path
from typing import Generator
from typing import NamedTuple
from typing import Union

from django.core.management import call_command
from django.db.transaction import atomic

from nautobot_netbox_importer.generator import RecordData
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceRecord
from nautobot_netbox_importer.generator import logger
from nautobot_netbox_importer.generator import print_fields_mapping
from nautobot_netbox_importer.generator import print_summary

from .models.base import setup_base
from .models.circuits import setup_circuits
from .models.dcim import fix_power_feed_locations
from .models.dcim import setup_dcim
from .models.ipam import setup_ipam
from .models.locations import setup_locations
from .models.virtualization import setup_virtualization


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

    def __init__(self, file_path: Union[str, Path], options: NetBoxImporterOptions, *args, **kwargs):
        """Initialize NetBox Source Adapter."""
        super().__init__(name="NetBox", get_source_data=_get_source_reader(file_path), *args, **kwargs)
        self.options = options

        setup_base(self)
        setup_locations(self, options.sitegroup_parent_always_region)
        setup_dcim(self)
        setup_circuits(self)
        setup_ipam(self)
        setup_virtualization(self)

    def load_data(self) -> None:
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
            print_summary(self)

        if self.options.field_mapping:
            print_fields_mapping(self)

    @atomic
    def _atomic_import(self) -> None:
        self.load_data()

        nautobot = self.nautobot
        nautobot.load_data()

        nautobot.sync_from(self)

        if nautobot.validation_issues and not self.options.bypass_data_validation:
            raise _ValidationIssuesDetected("Data validation issues detected, aborting the transaction.")

        if self.options.dry_run:
            raise _DryRunException("Aborting the transaction due to the dry-run mode.")


def _get_source_reader(file_path: Union[str, Path]):
    """Read NetBox source file."""

    def process_cable_termination(source_data: RecordData) -> str:
        # NetBox 3.3 split the dcim.cable model into dcim.cable and dcim.cabletermination models.
        cable_end = source_data.pop("cable_end").lower()
        source_data["id"] = source_data.pop("cable")
        source_data[f"termination_{cable_end}_type"] = source_data.pop("termination_type")
        source_data[f"termination_{cable_end}_id"] = source_data.pop("termination_id")

        return f"dcim.cabletermination_{cable_end}"

    def read() -> Generator[SourceRecord, None, None]:
        with open(file_path, "r", encoding="utf8") as file:
            data = json.load(file)

        for item in data:
            content_type = item["model"]
            netbox_pk = item.get("pk", None)
            source_data = item["fields"]

            if netbox_pk:
                source_data["id"] = netbox_pk

            if content_type == "dcim.cabletermination":
                content_type = process_cable_termination(source_data)

            yield SourceRecord(content_type, source_data)

    return read
