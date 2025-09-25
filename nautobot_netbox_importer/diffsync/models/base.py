"""NetBox to Nautobot Base Models Mapping."""

from packaging.version import Version

from nautobot_netbox_importer.diffsync.adapters.netbox import NetBoxAdapter
from nautobot_netbox_importer.diffsync.models.locations import define_locations
from nautobot_netbox_importer.generator import fields


def setup(adapter: NetBoxAdapter) -> None:
    """Map NetBox base models to Nautobot."""
    netbox_version = adapter.options.netbox_version

    adapter.disable_model("admin.logentry", "Not directly used in Nautobot.")
    adapter.disable_model("auth.permission", "Handled via a Nautobot model and may not be a 1 to 1.")
    adapter.disable_model("extras.imageattachment", "Images are not imported yet.")
    adapter.disable_model("sessions.session", "Nautobot has own sessions, sessions should never cross apps.")
    adapter.disable_model("users.userconfig", "May not have a 1 to 1 translation to Nautobot.")

    adapter.configure_model(
        "extras.Status",
        identifiers=["name"],
        default_reference={
            "name": "Unknown",
        },
    )
    adapter.configure_model("extras.role")
    adapter.configure_model(
        "extras.ConfigContext",
        fields={
            "locations": define_locations,
            "roles": fields.relation("dcim.DeviceRole"),
        },
    )
    adapter.configure_model(
        # pylint: disable=hard-coded-auth-user
        "auth.User" if netbox_version < Version("4") else "users.User",
        nautobot_content_type="users.User",
        identifiers=["username"],
        fields={
            "last_login": fields.disable("Should not be attempted to migrate"),
            "password": fields.disable("Should not be attempted to migrate"),
            "user_permissions": fields.disable("Permissions import is not implemented yet"),
            "object_permissions": fields.disable("Permissions import is not implemented yet"),
            "groups": (
                ""
                if netbox_version < Version("4")
                else fields.disable("Groups import is not implemented for NetBox 4+")
            ),
        },
    )
    adapter.configure_model(
        "auth.Group",
        identifiers=["name"],
        fields={
            "permissions": fields.disable("Permissions import is not implemented yet"),
        },
    )
    adapter.configure_model(
        "tenancy.Tenant",
        fields={
            "group": "tenant_group",
        },
    )
    adapter.configure_model(
        "extras.JournalEntry",
        nautobot_content_type="extras.Note",
    )
