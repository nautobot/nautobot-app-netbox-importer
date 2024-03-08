"""NetBox to Nautobot Virtualization Models Mapping."""
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import fields

from .locations import define_location


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox virtualization models to Nautobot."""
    adapter.configure_model(
        "virtualization.cluster",
        fields={
            "type": "cluster_type",
            "group": "cluster_group",
            "location": define_location,
        },
    )
    adapter.configure_model(
        "virtualization.virtualmachine",
        fields={
            "role": fields.role(adapter, "dcim.devicerole"),
        },
    )
    adapter.configure_model(
        "virtualization.vminterface",
        fields={
            "parent": "parent_interface",
        },
    )
