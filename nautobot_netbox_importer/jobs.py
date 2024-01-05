"""Jobs for NetBox SSoT integration."""
from diffsync.enum import DiffSyncFlags
from nautobot.apps.jobs import register_jobs
from nautobot.extras.jobs import BooleanVar
from nautobot.extras.jobs import Job
from nautobot.extras.jobs import StringVar
from nautobot_ssot.jobs.base import DataSource

from nautobot_netbox_importer.diffsync.adapters import NetBoxAdapter
from nautobot_netbox_importer.diffsync.adapters import NetBoxImporterOptions

# pylint: disable=invalid-name
name = "NetBox SSoT"


# pylint: disable=too-many-instance-attributes
class NetBoxDataSource(DataSource, Job):
    """NetBox SSoT Data Source."""

    debug = BooleanVar(description="Enable for more verbose debug logging", default=False)
    input_ref = StringVar(description="Input reference", default=None)

    def __init__(self):
        """Initialize NetBox Data Source."""
        super().__init__()
        # pylint: disable-next=unsupported-binary-operation
        self.diffsync_flags = self.diffsync_flags | DiffSyncFlags.CONTINUE_ON_FAILURE
        self._options = NetBoxImporterOptions()
        self._input_ref = ""

    # pylint: disable=too-few-public-methods
    class Meta:  # type: ignore
        """Meta data for NetBox."""

        name = "NetBox to Nautobot"
        data_source = "NetBox"
        data_target = "Nautobot"
        description = "Sync information from NetBox to Nautobot"

    @classmethod
    def config_information(cls):
        """Dictionary describing the configuration of this DataSource."""
        return {}

    @classmethod
    def data_mappings(cls):
        """List describing the data mappings involved in this DataSource."""
        return ()

    def load_source_adapter(self):
        """Load source adapter."""

    def load_target_adapter(self):
        """Load target adapter."""

    def run(self, *args, debug=False, dryrun=True, memory_profiling=False, input_ref="", **kwargs):
        """Run the NetBox DataSource."""
        self.debug = debug
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        self._input_ref = input_ref
        self._options = NetBoxImporterOptions(dry_run=dryrun)

        super().run(*args, **kwargs, debug=debug, dryrun=dryrun, memory_profiling=memory_profiling)

    def sync_data(self, memory_profiling):
        """Sync data from NetBox to Nautobot."""
        if not self.sync:
            raise ValueError("Sync object not initialized.")

        if memory_profiling:
            self.logger.info("Memory profiling not implemented for NetBoxDataSource.")

        adapter = NetBoxAdapter(
            input_ref=self._input_ref,
            job=self,
            sync=self.sync,
            options=self._options,
        )
        adapter.import_to_nautobot()
        self.sync.summary = adapter.diff_summary
        self.sync.save()


register_jobs(NetBoxDataSource)

jobs = [NetBoxDataSource]
