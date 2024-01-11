"""Summary of the import."""
from .base import DiffSummary
from .source import SourceAdapter
from .source import SourceField

_FILL_UP_LENGTH = 80


def _print(*strings: str):
    fill = strings[0][0]
    result = " ".join(strings)
    result = result + (fill * (_FILL_UP_LENGTH - len(result)))
    print(result)


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
        elif field.importer:
            yield "Custom Importer"
        elif field.disable_reason:
            yield "Disabled with reason:"
            yield field.disable_reason
        else:
            yield "Disabled"

    for content_type, wrapper in source.wrappers.items():
        if wrapper.imported_count == 0:
            continue

        _print(f". {content_type} => {wrapper.nautobot.content_type} ")
        for field in wrapper.fields.values():
            print(" ".join(get_field(field)))


def _print_back_mapping(source: SourceAdapter) -> None:
    back_mapping = getattr(source, "_content_types_back_mapping")
    for nautobot_content_type, content_type in back_mapping.items():
        if nautobot_content_type == content_type:
            continue
        if content_type:
            print(f"{nautobot_content_type} => {content_type}")
        else:
            print(f"{nautobot_content_type} => Ambiguous")


def _print_content_types_deviations(source: SourceAdapter) -> None:
    for content_type, wrapper in source.wrappers.items():
        if wrapper.disable_reason:
            print(f"{content_type} => {wrapper.nautobot.content_type} | Disabled with reason: {wrapper.disable_reason}")
        elif wrapper.extends_wrapper:
            print(f"{content_type} EXTENDS {wrapper.extends_wrapper.content_type} => {wrapper.nautobot.content_type}")
        elif content_type != wrapper.nautobot.content_type:
            print(f"{content_type} => {wrapper.nautobot.content_type}")


def _print_validation_issues(source: SourceAdapter) -> None:
    total = 0
    for content_type, issues in source.nautobot.validation_issues.items():
        total += len(issues)
        _print(f". {content_type}: {len(issues)} ")
        for error in issues:
            print(f"{error}")
    _print(".")
    print("Total validation issues:", total)


def print_summary(source: SourceAdapter, diff_summary: DiffSummary, field_mappings=True) -> None:
    """Print a summary of the import."""
    _print("= Import Summary: ")

    _print("- DiffSync Summary: ")
    for key, value in diff_summary.items():
        print(f"{key}: {value}")

    _print("- Nautobot Models Summary: ")
    for wrapper in source.get_imported_nautobot_wrappers():
        print(f"{wrapper.content_type}: {wrapper.imported_count}")

    _print("- Validation issues: ")
    if source.nautobot.validation_issues:
        _print_validation_issues(source)
    else:
        print("  No validation issues found.")

    _print("- Content Types Mapping Deviations: ")
    print("  Mapping deviations from source content type to Nautobot content type")
    _print_content_types_deviations(source)

    _print("- Content Types Back Mapping: ")
    print("  Back mapping deviations from Nautobot content type to the source content type")
    _print_back_mapping(source)

    if field_mappings:
        _print("- Fields Mapping: ")
        _print_fields_mapping(source)

    _print("=")
