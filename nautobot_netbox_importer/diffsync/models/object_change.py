"""NetBox to Nautobot Object Change Model Mapping."""

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.generator import ImporterPass, PreImportRecordResult, SourceAdapter, fields


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox object change to Nautobot."""

    def skip_disabled_object_types(source: RecordData, importer_pass: ImporterPass) -> PreImportRecordResult:
        """Disabled object types are not in Nautobot and should be skipped."""
        if importer_pass != ImporterPass.IMPORT_DATA:
            return PreImportRecordResult.USE_RECORD
        object_type = source.get("changed_object_type", None)
        wrapper = adapter.get_or_create_wrapper(object_type)
        return PreImportRecordResult.SKIP_RECORD if wrapper.disable_reason else PreImportRecordResult.USE_RECORD

    adapter.configure_model(
        "extras.ObjectChange",
        pre_import_record=skip_disabled_object_types,
        disable_related_reference=True,
        fields={
            "postchange_data": "object_data",
            # TBD: This should be defined on Nautobot side
            "time": fields.force(),
        },
    )
