"""App declaration for nautobot_netbox_importer."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class NautobotNetboxImporterConfig(NautobotAppConfig):
    """App configuration for the nautobot_netbox_importer app."""

    name = "nautobot_netbox_importer"
    verbose_name = "Nautobot NetBox Importer"
    version = __version__
    author = "Network to Code, LLC"
    description = "Data importer from NetBox 3.x to Nautobot 2.x."
    base_url = "netbox-importer"
    required_settings = []
    default_settings = {}
    docs_view_name = "plugins:nautobot_netbox_importer:docs"
    searchable_models = []


config = NautobotNetboxImporterConfig  # pylint:disable=invalid-name
