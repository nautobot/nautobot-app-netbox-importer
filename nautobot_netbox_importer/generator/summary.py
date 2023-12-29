"""Summary of the import."""
from .base import DiffSummary
from .source import SourceAdapter
from .source import SourceField


def _print_fields_mapping(source: SourceAdapter) -> None:
    """Print fields mapping."""

    def get_field(field: SourceField):
        yield field.name
        if field.from_data:
            yield "(DATA)"
        if field.is_custom:
            yield "(CUSTOM)"

        yield "=>"

        nautobot_field = getattr(field, "_nautobot")
        if nautobot_field:
            yield nautobot_field.name
            yield f"({nautobot_field.internal_type.value})"
        elif not field.importer:
            yield "SKIPPED"
        else:
            yield "CUSTOM IMPORTER"

    for content_type, wrapper in source.wrappers.items():
        if wrapper.imported_count == 0:
            continue

        print(f". {content_type} ................................")
        for field in wrapper.fields.values():
            print(" ".join(get_field(field)))


def _print_back_mapping(source: SourceAdapter) -> None:
    back_mapping = getattr(source, "_content_types_back_mapping")
    for nautobot_content_type, content_type in back_mapping.items():
        if nautobot_content_type == content_type:
            continue
        if content_type:
            print(f"  {nautobot_content_type} -> {content_type}")
        else:
            print(f"  {nautobot_content_type} -> Unambiguous")


def _print_content_types_deviations(source: SourceAdapter) -> None:
    back_mapping = getattr(source, "_content_types_back_mapping")
    for content_type, wrapper in source.wrappers.items():
        if wrapper.disable_reason:
            print(
                f"  {content_type} -> {wrapper.nautobot.content_type}; Disabled with reason: {wrapper.disable_reason}"
            )
        elif back_mapping.get(wrapper.nautobot.content_type, "") is None:
            print(f"  {content_type} -> {wrapper.nautobot.content_type}")


def _print_validation_issues(source: SourceAdapter) -> None:
    total = 0
    for model_type, issues in source.nautobot.validation_issues.items():
        total += len(issues)
        print(f"  {model_type}: {len(issues)}")
        for error in issues:
            print(f"    {error}")
    print("Total validation issues:", total)


def print_summary(source: SourceAdapter, diff_summary: DiffSummary, field_mappings=True) -> None:
    """Print a summary of the import."""
    print("= Import Summary ===============================")

    print("- Diff Summary: ---------------------")
    for key, value in diff_summary.items():
        print(f"  {key}: {value}")

    print("- Nautobot Models Imports: ---------------------")
    for wrapper in source.get_imported_nautobot_wrappers():
        print(f"  {wrapper.content_type}: {wrapper.imported_count}")

    if source.nautobot.validation_issues:
        print("- Validation issues: ---------------------------")
        _print_validation_issues(source)
    else:
        print("- No validation issues -------------------------")

    print("- Content Types Deviations ---------------------")
    print("Mapping deviations from source content type to Nautobot content type")
    _print_content_types_deviations(source)

    print("- Content Types Back Mapping -------------------")
    print("Back mapping deviations from Nautobot content type to source content type")
    _print_back_mapping(source)

    if field_mappings:
        print("- Fields Mapping -------------------------------")
        _print_fields_mapping(source)

    print("================================================")
