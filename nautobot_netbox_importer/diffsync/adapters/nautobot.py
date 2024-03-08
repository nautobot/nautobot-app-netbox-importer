"""Nautobot Adapter for NetBox Importer."""
from nautobot_netbox_importer.generator import NautobotAdapter as _NautobotAdapter


class NautobotAdapter(_NautobotAdapter):
    """DiffSync adapter for Nautobot."""

    def __init__(self, *args, job=None, sync=None, **kwargs):
        """Initialize Nautobot.

        Args:
            *args (tuple): Arguments to be passed to the parent class.
            job (object, optional): Nautobot job. Defaults to None.
            sync (object, optional): Nautobot DiffSync. Defaults to None.
            **kwargs (dict): Additional arguments to be passed to the parent class.
        """
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
