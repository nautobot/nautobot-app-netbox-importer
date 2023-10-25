"""Plugin declaration for nautobot_netbox_importer."""
# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

__version__ = metadata.version(__name__)

from nautobot.extras.plugins import NautobotAppConfig


class NautobotNetboxImporterConfig(NautobotAppConfig):
    """Plugin configuration for the nautobot_netbox_importer plugin."""

    name = "nautobot_netbox_importer"
    verbose_name = "Nautobot NetBox Importer"
    version = __version__
    author = "Network to Code, LLC"
    description = "Data importer from NetBox 2.10.x to Nautobot.."
    base_url = "netbox-importer"
    required_settings = []
    min_version = "1.6.0"
    max_version = "1.9999"
    default_settings = {}
    caching_config = {}


config = NautobotNetboxImporterConfig  # pylint:disable=invalid-name
