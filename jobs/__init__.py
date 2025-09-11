from nautobot.apps.jobs import register_jobs
from .import_netbox import NetBoxImporter

register_jobs(NetBoxImporter)