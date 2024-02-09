"""Importer summary module."""

import json
from pathlib import Path
from typing import Callable
from typing import Generator
from typing import List
from typing import Mapping
from typing import MutableMapping
from typing import NamedTuple
from typing import Optional
from typing import OrderedDict
from typing import Union

from .base import ContentTypeStr
from .base import FieldName
from .base import Pathable


class ValidationIssue(NamedTuple):
    """Validation issue."""

    uid: str
    name: str
    error: str


ValidationIssues = MutableMapping[ContentTypeStr, List[ValidationIssue]]
DiffSummary = Mapping[str, int]


class FieldSummary(NamedTuple):
    """Field summary."""

    name: FieldName
    nautobot_name: Optional[FieldName]
    nautobot_internal_type: Optional[str]
    nautobot_can_import: Optional[bool]
    importer: Optional[str]
    definition: Union[str, bool, int, float, None]
    from_data: Optional[bool]
    is_custom: Optional[bool]
    default_value: Union[str, bool, int, float, None]
    disable_reason: str


class ModelSummary(NamedTuple):
    """Model summary."""

    content_type: ContentTypeStr
    content_type_id: int
    extends_content_type: Optional[ContentTypeStr]
    nautobot_content_type: ContentTypeStr
    nautobot_content_type_id: Optional[int]
    disable_reason: str
    identifiers: Optional[List[FieldName]]
    disable_related_reference: bool
    forward_references: Optional[str]
    pre_import: Optional[str]
    fields: List[FieldSummary]
    flags: str
    nautobot_flags: str
    default_reference_uid: Union[str, bool, int, float, None]
    imported_count: int


_FILL_UP_LENGTH = 100


def _fill_up(*values) -> str:
    fill = values[0][0]
    result = " ".join(str(value) for value in values) + " " + fill
    return result + (fill * (_FILL_UP_LENGTH - len(result)))


def serialize_to_summary(value):
    """Serialize value to summary."""
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Callable):
        return value.__name__
    return str(value)


class ImportSummary:
    """Import summary."""

    def __init__(self):
        """Initialize the import summary."""
        self.models: List[ModelSummary] = []
        self.diff_summary: DiffSummary = {}
        self.validation_issues: ValidationIssues = OrderedDict()

    def add(self, model_summary: ModelSummary):
        """Add a model summary to the import summary."""
        self.models.append(model_summary)

    def set_validation_issues(self, validation_issues: ValidationIssues):
        """Set the validation issues."""
        for content_type in sorted(validation_issues):
            self.validation_issues[content_type] = sorted(validation_issues[content_type], key=lambda issue: issue.uid)

    def load(self, path: Pathable):
        """Load the summary from a file."""
        content = json.loads(Path(path).read_text(encoding="utf-8"))
        self.diff_summary = content["diff_summary"]
        self.set_validation_issues(content["validation_issues"])
        for model in content["models"].values():
            self.add(
                ModelSummary(
                    **{key.replace(".", "_"): value for key, value in model.items() if key not in ["fields"]},
                    fields=[
                        FieldSummary(**{key.replace(".", "_"): value for key, value in field.items()})
                        for field in model["fields"].values()
                    ],
                )
            )

    def dump(self, path: Pathable, output_format="json", indent=4):
        """Dump the summary to a file."""
        if output_format == "json":
            Path(path).write_text(
                json.dumps(
                    {
                        "diff_summary": self.diff_summary,
                        "models": {
                            model_summary.content_type: {
                                **{key: value for key, value in model_summary._asdict().items() if key != "fields"},
                                "fields": {field.name: field._asdict() for field in model_summary.fields},
                            }
                            for model_summary in self.models
                        },
                        "validation_issues": {key: list(value) for key, value in self.validation_issues.items()},
                    },
                    indent=indent,
                ),
                encoding="utf-8",
            )
        elif output_format == "text":
            with open(path, "w", encoding="utf-8") as file:
                for line in self.get_summary(detailed=True):
                    file.write(line + "\n")
        else:
            raise ValueError(f"Unsupported format {output_format}")

    def print(self, detailed=False):
        """Print a summary of the import."""
        for line in self.get_summary(detailed):
            print(line)

    def get_summary(self, detailed: bool) -> Generator[str, None, None]:
        """Get a summary of the import."""
        yield _fill_up("= Import Summary:")

        yield _fill_up("- DiffSync Summary:")
        for key, value in self.diff_summary.items():
            yield f"{key}: {value}"

        yield _fill_up("- Nautobot Models Summary:")
        for model_summary in self.models:
            if model_summary.imported_count > 0:
                yield f"{model_summary.content_type}: {model_summary.imported_count}"

        yield _fill_up("- Validation issues:")
        if self.validation_issues:
            yield from self.get_validation_issues()
        else:
            yield "  No validation issues found."

        yield _fill_up("- Content Types Mapping Deviations:")
        yield "  Mapping deviations from source content type to Nautobot content type"
        yield from self.get_content_types_deviations()

        yield _fill_up("- Content Types Back Mapping:")
        yield "  Back mapping deviations from Nautobot content type to the source content type"
        yield from self.get_back_mapping()

        if detailed:
            yield _fill_up("- Detailed Fields Mapping:")
            yield from self.get_detailed_mapping()

        yield _fill_up("= End of Import Summary.")

    def get_content_types_deviations(self) -> Generator[str, None, None]:
        """Get formatted content types deviations."""
        for model_summary in self.models:
            if model_summary.disable_reason:
                yield f"{model_summary.content_type} => {model_summary.nautobot_content_type} | Disabled with reason: {model_summary.disable_reason}"
            elif model_summary.extends_content_type:
                yield f"{model_summary.content_type} EXTENDS {model_summary.extends_content_type} => {model_summary.nautobot_content_type}"
            elif model_summary.content_type != model_summary.nautobot_content_type:
                yield f"{model_summary.content_type} => {model_summary.nautobot_content_type}"

    def get_back_mapping(self) -> Generator[str, None, None]:
        """Get formatted back mapping."""
        back_mapping = {}

        for model_summary in self.models:
            if model_summary.nautobot_content_type != model_summary.content_type:
                if model_summary.nautobot_content_type in back_mapping:
                    if back_mapping[model_summary.nautobot_content_type] != model_summary.content_type:
                        back_mapping[model_summary.nautobot_content_type] = None
                else:
                    back_mapping[model_summary.nautobot_content_type] = model_summary.content_type

        for nautobot_content_type, content_type in back_mapping.items():
            if content_type:
                yield f"{nautobot_content_type} => {content_type}"
            else:
                yield f"{nautobot_content_type} => Ambiguous"

    def get_validation_issues(self) -> Generator[str, None, None]:
        """Get formatted validation issues."""
        total = 0

        for content_type, issues in self.validation_issues.items():
            total += len(issues)
            yield _fill_up(f". {content_type}: {len(issues)} ")
            for issue in issues:
                yield f"{issue.uid} {issue.name} | {issue.error}"
        yield _fill_up(".")

        yield f"Total validation issues: {total}"

    def get_detailed_mapping(self) -> Generator[str, None, None]:
        """Get formatted detailed mappings."""

        def get_field(field: FieldSummary):
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
                yield field.importer
            elif field.name == "id":
                yield "uid_from_data"
            else:
                yield "NO IMPORTER"

            yield "=>"

            if field.importer or field.nautobot_name == "id":
                if field.nautobot_name:
                    yield field.nautobot_name
                    yield f"({field.nautobot_internal_type})"
                else:
                    yield "Custom Target"
            else:
                yield "NO TARGET"

        for model_summary in self.models:
            yield _fill_up(
                "*",
                model_summary.content_type,
                "=>",
                model_summary.nautobot_content_type,
            )

            if model_summary.disable_reason:
                yield f"    Disable reason: {model_summary.disable_reason}"
            else:
                for field in model_summary.fields:
                    yield " ".join(get_field(field))
