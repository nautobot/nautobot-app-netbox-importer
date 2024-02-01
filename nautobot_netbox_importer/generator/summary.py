"""Summary of the import."""
from typing import Callable

from django.contrib.contenttypes.models import ContentType

from .base import DiffSummary
from .source import SourceAdapter
from .source import SourceField
from .source import SourceModelWrapper

_FILL_UP_LENGTH = 80


def _print(*values):
    fill = values[0][0]
    result = " ".join(str(value) for value in values)
    result = result + (fill * (_FILL_UP_LENGTH - len(result)))
    print(result)


def _print_fields_mapping(source: SourceAdapter) -> None:
    """Print fields mapping."""
    wrapper_to_id = {value: key for key, value in source.content_type_ids_mapping.items()}

    def get_header(wrapper: SourceModelWrapper):
        yield "."
        yield wrapper.content_type
        yield "CT PK:"
        try:
            yield wrapper_to_id[wrapper]
        except KeyError:
            yield "Not Found"
        yield "=>"
        yield wrapper.nautobot.content_type
        yield "CT PK:"
        try:
            yield wrapper.nautobot.content_type_instance.pk
        except ContentType.DoesNotExist:  # type: ignore
            yield "(Not Found)"

    def get_field(field: SourceField):
        yield field.name
        if field.from_data:
            yield "(DATA)"
        if field.is_custom:
            yield "(CUSTOM)"

        yield "=>"

        if field.disable_reason:
            yield "Disabled with reason:"
            yield field.disable_reason
            return

        if field.importer:
            yield field.importer.__name__
        elif field.name == "id":
            yield "uid_from_data"
        else:
            yield "NO IMPORTER"

        yield "=>"

        nautobot_field = getattr(field, "_nautobot")
        if nautobot_field:
            yield nautobot_field.name
            yield f"({nautobot_field.internal_type.value})"
        elif field.importer and not field.disable_reason:
            yield "Custom Target"
        else:
            yield "NO TARGET"

    for wrapper in source.wrappers.values():
        if wrapper.imported_count == 0:
            continue

        _print(*get_header(wrapper))
        for field in wrapper.fields.values():
            print(*get_field(field))


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


def _serialize(value):
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Callable):
        return value.__name__
    return str(value)


def _get_field_mapping(field: SourceField) -> dict:
    nautobot = getattr(field, "_nautobot")

    return {
        "name": field.name,
        "nautobot.name": nautobot and nautobot.name,
        "nautobot.internal_type": nautobot and nautobot.internal_type.value,
        "nautobot.can_import": nautobot and nautobot.can_import,
        "importer": field.importer and field.importer.__name__,
        "definition": _serialize(field.definition),
        "from_data": field.from_data,
        "is_custom": field.is_custom,
        "default_value": _serialize(field.default_value),
        "disable_reason": field.disable_reason,
    }


def _get_wrapper_mapping(wrapper: SourceModelWrapper, content_type_id) -> dict:
    nautobot = wrapper.nautobot
    nautobot_content_type = nautobot.content_type_instance if getattr(nautobot, "_model", None) else None

    return {
        "content_type": wrapper.content_type,
        "content_type_id": content_type_id,
        "extends_content_type": wrapper.extends_wrapper and wrapper.extends_wrapper.content_type,
        "nautobot.content_type": nautobot.content_type,
        "nautobot.content_type_id": nautobot_content_type and nautobot_content_type.pk,
        "disable_reason": wrapper.disable_reason,
        "identifiers": wrapper.identifiers,
        "disable_related_reference": wrapper.disable_related_reference,
        "forward_references": wrapper.forward_references and wrapper.forward_references.__name__,
        "pre_import": wrapper.pre_import and wrapper.pre_import.__name__,
        "fields": [_get_field_mapping(field) for field in wrapper.fields.values()],
        "flags": _serialize(wrapper.flags),
        "nautobot.flags": _serialize(nautobot.flags),
        "default_reference_uid": _serialize(wrapper.default_reference_uid),
        "imported_count": wrapper.imported_count,
    }


def get_mapping(source: SourceAdapter) -> list:
    """Get a JSON serializable mapping of the importer."""
    wrapper_to_id = {value: key for key, value in source.content_type_ids_mapping.items()}

    def get_wrappers():
        content_types = sorted(list(source.wrappers))
        for content_type in content_types:
            wrapper = source.wrappers.get(content_type, None)
            if wrapper:
                yield wrapper

    return [_get_wrapper_mapping(wrapper, wrapper_to_id.get(wrapper, None)) for wrapper in get_wrappers()]
