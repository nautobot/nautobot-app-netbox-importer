"""NetBox to Nautobot Object Change Model Mapping."""

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.generator import ImporterPass
from nautobot_netbox_importer.generator import PreImportResult
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import fields


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox object change to Nautobot."""

    def skip_disabled_object_types(source: RecordData, importer_pass: ImporterPass) -> PreImportResult:
        """Disabled object types are not in Nautobot and should be skipped."""
        if importer_pass != ImporterPass.IMPORT_DATA:
            return PreImportResult.USE_RECORD
        object_type = source.get("changed_object_type", None)
        wrapper = adapter.get_or_create_wrapper(object_type)
        return PreImportResult.SKIP_RECORD if wrapper.disable_reason else PreImportResult.USE_RECORD

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
