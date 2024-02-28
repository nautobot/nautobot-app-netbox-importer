"""NetBox to Nautobot Custom Fields Models Mapping."""

import json
from typing import Any
from typing import Iterable

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.base import Uid
from nautobot_netbox_importer.generator import EMPTY_VALUES
from nautobot_netbox_importer.generator import DiffSyncBaseModel
from nautobot_netbox_importer.generator import ImporterPass
from nautobot_netbox_importer.generator import PreImportResult
from nautobot_netbox_importer.generator import SourceAdapter
from nautobot_netbox_importer.generator import SourceField
from nautobot_netbox_importer.generator import fields


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
                    choice = stringified
            except json.JSONDecodeError:
                choice = [choice, choice]

        if isinstance(choice, Iterable):
            if not isinstance(choice, list):
                choice = list(choice)
        else:
            raise ValueError(f"Unsupported choices format: {choices}")

        if len(choice) != 2:
            raise ValueError(f"Unsupported choices format: {choices}")

        choices[index] = choice[0]

    return choices


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
            "type": fields.fallback(value="text"),
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
