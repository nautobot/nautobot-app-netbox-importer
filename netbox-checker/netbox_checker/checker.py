"""NetBox check script to validate data before importing to Nautobot."""

import sys
from os import getenv

from django.apps import apps
from django.urls import reverse

_SETTINGS = {
    "max_outputs": 0,
    "base_url": "",
}


def _print_issues(message: str, queryset):
    """Print issues to the console."""
    for obj in queryset:
        _SETTINGS["max_outputs"] -= 1
        if _SETTINGS["max_outputs"] < 0:
            sys.exit(0)

        print(f"{message} {obj.id} {obj}")

        app_label = obj._meta.app_label
        model_name = obj._meta.model_name
        url = reverse(f"{app_label}:{model_name}", kwargs={"pk": obj.id})
        print(f"{_SETTINGS['base_url']}{url}")

        print(100 * "-")


def _find_missing_cables(side: str):
    """Check for cables missing termination side `A` or `B`."""
    Cable = apps.get_model("dcim", "Cable")
    CableTermination = apps.get_model("dcim", "CableTermination")

    cables_missing = Cable.objects.exclude(id__in=CableTermination.objects.filter(cable_end="A").values("cable_id"))

    if cables_missing.count():
        _print_issues(f"Missing cable termination on side {side}:", cables_missing)


def check_netbox(
    max_outputs=int(getenv("NETBOX_CHECKER_MAX_OUTPUTS") or 10),
    base_url=getenv("NETBOX_CHECKER_BASE_URL", "http://localhost:8000"),
):
    """Main function."""
    _SETTINGS["max_outputs"] = max_outputs
    _SETTINGS["base_url"] = base_url

    _find_missing_cables("A")
    _find_missing_cables("B")
