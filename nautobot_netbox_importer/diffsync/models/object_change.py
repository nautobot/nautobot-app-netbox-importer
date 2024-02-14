"""NetBox to Nautobot Object Change Model Mapping."""

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import fields


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox object change to Nautobot."""

    def skip_disabled_object_types(source: RecordData, stage: int) -> bool:
        """Disabled object types are not in Nautobot and should be skipped."""
        if stage != 2:
            return True
        object_type = source.get("changed_object_type", None)
        wrapper = adapter.get_or_create_wrapper(object_type)
        return not wrapper.disable_reason

    adapter.configure_model(
        "extras.ObjectChange",
        pre_import=skip_disabled_object_types,
        disable_related_reference=True,
        fields={
            "postchange_data": "object_data",
            # TBD: This should be defined on Nautobot side
            "time": fields.force(),
        },
    )
