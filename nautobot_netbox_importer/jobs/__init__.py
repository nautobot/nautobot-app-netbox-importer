from nautobot.apps.jobs import register_jobs
from nautobot_netbox_importer.jobs.import_netbox import NetBoxImporter

register_jobs(NetBoxImporter)