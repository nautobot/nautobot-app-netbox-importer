"""Plugin declaration for nautobot-netbox-importer."""

try:
    from importlib import metadata
except ImportError:
    # Python version < 3.8
    import importlib_metadata as metadata

from nautobot.extras.plugins import PluginConfig

__version__ = metadata.version(__name__)


class NautobotNetboxImporterConfig(PluginConfig):
    """Plugin configuration for the nautobot-netbox-importer plugin."""

    name = "nautobot_netbox_importer"
    verbose_name = "Nautobot NetBox Importer"
    version = __version__
    author = "Network to Code, LLC"
    author_email = "opensource@networktocode.com"
    description = "Data importer from NetBox 2.10.x to Nautobot."
    base_url = "netbox-importer"
    required_settings = []
    min_version = "1.0.0b3"
    max_version = "1.9999"
    default_settings = {}
    caching_config = {}


config = NautobotNetboxImporterConfig  # pylint:disable=invalid-name
