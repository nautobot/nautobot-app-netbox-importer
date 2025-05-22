"""NetBox to Nautobot Circuits Models Mapping."""

from nautobot_netbox_importer.diffsync.models.locations import define_location
from nautobot_netbox_importer.generator import SourceAdapter, fields


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox circuits models to Nautobot."""
    adapter.configure_model(
        "circuits.circuit",
        fields={
            "cid": fields.auto_increment(),
            "type": "circuit_type",
            "termination_a": "circuit_termination_a",
            "termination_z": "circuit_termination_z",
        },
    )
    adapter.configure_model(
        "circuits.circuittermination",
        fields={
            "location": define_location,
        },
    )
