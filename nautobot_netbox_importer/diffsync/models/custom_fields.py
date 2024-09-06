"""NetBox to Nautobot Custom Fields Models Mapping."""

import json
from typing import Any, Iterable

from nautobot_netbox_importer.base import RecordData, Uid
from nautobot_netbox_importer.generator import (
    EMPTY_VALUES,
    DiffSyncBaseModel,
    ImporterPass,
    PreImportResult,
    SourceAdapter,
    SourceField,
    fields,
)
from nautobot_netbox_importer.utils import get_field_choices


def _convert_choices(choices: Any) -> list:
    r"""Convert NetBox custom field choices to Nautobot format.

    Example:
        >>> _convert_choices("[\"[\\\"Choice 1\\\", \\\"Choice 1\\\"]\", \"[\\\"Choice 2\\\", \\\"Choice 2\\\"]\", \"[\\\"Choice 3\\\", \\\"Choice 3\\\"]\"]")
        ["Choice 1", "Choice 2", "Choice 3"]
    """
    if choices in EMPTY_VALUES:
        return []

    if isinstance(choices, str):
        choices = json.loads(choices)

    if choices in EMPTY_VALUES:
        return []

    for index, choice in enumerate(choices):
        if isinstance(choice, str):
            try:
                stringified = json.loads(choice)
                if isinstance(stringified, (list, str)):
                    choice = stringified  # noqa: PLW2901
            except json.JSONDecodeError:
                choice = [choice, choice]  # noqa: PLW2901

        if isinstance(choice, Iterable):
            if not isinstance(choice, list):
                choice = list(choice)  # noqa: PLW2901
        else:
            raise ValueError(f"Unsupported choices format: {choices}")

        if len(choice) != 2:  # noqa: PLR2004
            raise ValueError(f"Unsupported choices format: {choices}")

        choices[index] = choice[0]

    return choices


def _define_custom_field_type(field: SourceField) -> None:
    """Define the custom field `type` field importer.

    This function is called between the first and second pass of input data, when creating importers.
    """

    def type_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        """Import the `type` field from NetBox to Nautobot.

        This function is called for each input source data record of `extras.customfield` model.

        NetBox type "multiselect" must be converted to "multi-select" in Nautobot. Fall back to "text" for all unknown field types.
        """
        # Process the conversion from NetBox to Nautobot
        field_choices = getattr(field.nautobot.field, "choices", None)
        if not field_choices:
            raise ValueError(f"Invalid field_choices for {field}")

        choices = dict(get_field_choices(field_choices))
        value = field.get_source_value(source)
        if value in choices:
            field.set_nautobot_value(target, value)
        elif value in EMPTY_VALUES:
            field.set_nautobot_value(target, value)
        elif value == "multiselect":
            field.set_nautobot_value(target, "multi-select")
        else:
            field.set_nautobot_value(target, "text")

    # Register the importer and map the field from NetBox to Nautobot.
    # The Nautobot field name is the same as the NetBox field name: `type` in this case.
    field.set_importer(type_importer)


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox custom fields to Nautobot."""
    choice_sets = {}

    def create_choice_set(source: RecordData, importer_pass: ImporterPass) -> PreImportResult:
        if importer_pass == ImporterPass.DEFINE_STRUCTURE:
            choice_sets[source.get("id")] = [
                *_convert_choices(source.get("base_choices")),
                *_convert_choices(source.get("extra_choices")),
            ]

        return PreImportResult.USE_RECORD

    def define_choice_set(field: SourceField) -> None:
        def choices_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            choice_set = source.get(field.name, None)
            if choice_set in EMPTY_VALUES:
                return

            choices = choice_sets.get(choice_set, None)
            if not choices:
                raise ValueError(f"Choice set {choice_set} not found")

            create_choices(choices, getattr(target, "id"))

        field.set_importer(choices_importer, nautobot_name=None)

    def define_choices(field: SourceField) -> None:
        def choices_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
            choices = _convert_choices(source.get(field.name, None))
            if choices in EMPTY_VALUES:
                return

            if not isinstance(choices, list):
                raise ValueError(f"Choices must be a list of strings, got {type(choices)}")

            create_choices(choices, getattr(target, "id"))

        field.set_importer(choices_importer, nautobot_name=None)

    def create_choices(choices: list, custom_field_uid: Uid) -> None:
        for choice in choices:
            choices_wrapper.import_record(
                {
                    "id": choice,
                    "custom_field": custom_field_uid,
                    "value": choice,
                },
            )

    # Defined in NetBox but not in Nautobot
    adapter.configure_model(
        "extras.CustomFieldChoiceSet",
        pre_import=create_choice_set,
    )

    adapter.configure_model(
        "extras.CustomField",
        fields={
            "name": "key",
            "label": fields.default("Empty Label"),
            "type": _define_custom_field_type,
            # NetBox<3.6
            "choices": define_choices,
            # NetBox>=3.6
            "choice_set": define_choice_set,
        },
    )

    choices_wrapper = adapter.configure_model(
        "extras.CustomFieldChoice",
        fields={
            "custom_field": "custom_field",
            "value": "value",
        },
    )
