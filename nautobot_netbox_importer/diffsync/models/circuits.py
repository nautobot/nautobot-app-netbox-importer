"""NetBox to Nautobot Circuits Models Mapping."""
from nautobot_netbox_importer.generator import SourceAdapter

from .locations import define_location


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox circuits models to Nautobot."""
    adapter.configure_model(
        "circuits.circuit",
        fields={
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
