"""NetBox to Nautobot Circuits Models Mapping."""

from nautobot_netbox_importer.base import PLACEHOLDER_UID
from nautobot_netbox_importer.diffsync.models.locations import define_location
from nautobot_netbox_importer.generator import SourceAdapter, fields


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox circuits models to Nautobot."""

    def fill_circuit_termination_placeholder(record, suffix):
        circuit_instance = circuit.import_placeholder(suffix)
        uid = circuit_instance.id  # type: ignore
        return record.update({"circuit": uid})

    def fill_circuit_placeholder(record, _):
        return record.update(
            {
                "provider": PLACEHOLDER_UID,
                "type": PLACEHOLDER_UID,
            }
        )

    circuit_type = adapter.configure_model("circuits.circuittype")
    circuit_type.cache_record(
        {
            "id": PLACEHOLDER_UID,
        }
    )
    circuit_provider = adapter.configure_model("circuits.provider")
    circuit_provider.cache_record(
        {
            "id": PLACEHOLDER_UID,
        }
    )
    circuit = adapter.configure_model(
        "circuits.circuit",
        fields={
            "provider": "",
            "cid": fields.auto_increment(),
            "type": "circuit_type",
            "termination_a": "circuit_termination_a",
            "termination_z": "circuit_termination_z",
        },
        fill_placeholder=fill_circuit_placeholder,
    )
    adapter.configure_model(
        "circuits.circuittermination",
        fields={
            "circuit": "",
            "location": define_location,
        },
        fill_placeholder=fill_circuit_termination_placeholder,
    )
