"""Summary of the import."""
from nautobot_netbox_importer.diffsync.source import SourceAdapter
from nautobot_netbox_importer.diffsync.nautobot import NautobotAdapter


def print_fields_mapping(source: SourceAdapter) -> None:
    """Print fields mapping."""

    def get_mapping(field):
        if field.nautobot_name:
            return field.nautobot_name

        if not field.importer:
            return "SKIPPED"

        return "CUSTOM IMPORTER"

    print("= Field Mapping ================================")
    for content_type, wrapper in source.wrappers.items():
        if wrapper.imported_count == 0:
            continue

        print(f"- {content_type} --------------------------------")
        for field in wrapper.fields.values():
            print(f"  {field.name} => {get_mapping(field)}")

    print("================================================")


def print_summary(source: SourceAdapter, nautobot: NautobotAdapter) -> None:
    """Print a summary of the import."""
    print("= Import Summary ===============================")

    print("- Nautobot Models Imports: ---------------------")
    for wrapper in source.get_imported_nautobot_wrappers():
        print(f"  {wrapper.content_type}: {wrapper.imported_count}")

    if nautobot.validation_errors:
        print("- Validation errors: ---------------------------")
        total = 0
        for model_type, errors in nautobot.validation_errors.items():
            total += len(errors)
            print(f"  {model_type}: {len(errors)}")
            for error in errors:
                print(f"    {error}")
        print("Total validation errors:", total)
    else:
        print("- No validation errors ------------------------")

    print("- Content Types Mapping ------------------------")
    print("Mapping deviations from source content type to Nautobot content type")
    for content_type, wrapper in source.wrappers.items():
        if wrapper.imported_count == 0 or content_type == wrapper.nautobot.content_type:
            continue
        print(f"  {content_type} -> {wrapper.nautobot.content_type}")

    print("- Content Types Back Mapping -------------------")
    print("Back mapping deviations from Nautobot content type to source content type")
    for content_type, back_mapping in source.content_types_back_mapping.items():
        wrapper = source.nautobot.wrappers[content_type]
        if wrapper.imported_count == 0 or content_type == back_mapping:
            continue
        if back_mapping:
            print(f"  {content_type} -> {back_mapping}")
        else:
            print(f"  {content_type} -> Unambiguous")

    print("================================================")
