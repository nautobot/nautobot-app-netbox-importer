"""Importer summary module."""

import json
from pathlib import Path
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import List
from typing import Mapping
from typing import NamedTuple
from typing import Optional
from typing import Union

from .base import ContentTypeStr
from .base import FieldName
from .base import Pathable


class ImporterIssue(NamedTuple):
    """Importer issue."""

    uid: str
    name: str
    issue_type: str
    message: str


DiffSyncSummary = Mapping[str, int]


class FieldSummary(NamedTuple):
    """Field summary."""

    name: FieldName
    nautobot_name: Optional[FieldName]
    nautobot_internal_type: Optional[str]
    nautobot_can_import: Optional[bool]
    importer: Optional[str]
    definition: Union[str, bool, int, float, None]
    sources: List[str]
    default_value: Union[str, bool, int, float, None]
    disable_reason: str
    required: bool


# pylint: disable=too-few-public-methods,too-many-instance-attributes
class SourceModelStats:
    """Source Model Statistics."""

    first_pass_skipped = 0
    first_pass_used = 0
    second_pass_skipped = 0
    second_pass_used = 0
    pre_cached = 0
    imported_from_cache = 0
    # Imported using `wrapper.import_data()` including cache and custom importers
    imported = 0
    # DiffSyncModels created
    created = 0


# pylint: disable=too-few-public-methods
class NautobotModelStats:
    """Nautobot Model Statistics."""

    # Source DiffSyncModels created but ignored by DiffSync
    source_ignored = 0
    # Source DiffSyncModels created and synced by DiffSync
    source_created = 0
    issues = 0
    # Number of Nautobot instances that failed `save()` method
    save_failed = 0


class SourceModelSummary(NamedTuple):
    """Source Model Summary."""

    content_type: ContentTypeStr
    content_type_id: int
    extends_content_type: Optional[ContentTypeStr]
    nautobot_content_type: ContentTypeStr
    disable_reason: str
    identifiers: Optional[List[FieldName]]
    disable_related_reference: bool
    forward_references: Optional[str]
    pre_import: Optional[str]
    fields: List[FieldSummary]
    flags: str
    default_reference_uid: Union[str, bool, int, float, None]
    stats: SourceModelStats


class NautobotModelSummary(NamedTuple):
    """Nautobot Model Summary."""

    content_type: ContentTypeStr
    content_type_id: Optional[int]
    flags: str
    disabled: bool
    stats: NautobotModelStats
    issues: List[ImporterIssue]


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
        self.source: List[SourceModelSummary] = []
        self.nautobot: List[NautobotModelSummary] = []
        self.diffsync: DiffSyncSummary = {}

    @property
    def data_sources(self) -> Generator[SourceModelSummary, None, None]:
        """Get source originating from data."""
        for summary in self.source:
            if any(field for field in summary.fields if "DATA" in field.sources):
                yield summary

    @property
    def data_nautobot_models(self) -> Generator[NautobotModelSummary, None, None]:
        """Get Nautobot models originating from data."""
        content_types = set(item.content_type for item in self.data_sources)

        for item in self.nautobot:
            if item.content_type in content_types:
                yield item

    def load(self, path: Pathable):
        """Load the summary from a file."""
        content = json.loads(Path(path).read_text(encoding="utf-8"))

        self.diffsync = content["diffsync"]

        for model in content["source"].values():
            stats = SourceModelStats()
            for key, value in model.pop("stats", {}).items():
                setattr(stats, key, value)
            fields = model.pop("fields", [])
            self.source.append(
                SourceModelSummary(
                    **model,
                    fields=[FieldSummary(**field) for field in fields.values()],
                    stats=stats,
                )
            )

        for model in content["nautobot"].values():
            stats = NautobotModelStats()
            for key, value in model.pop("stats", {}).items():
                setattr(stats, key, value)
            issues = model.pop("issues", {})
            self.nautobot.append(
                NautobotModelSummary(
                    **model,
                    stats=stats,
                    issues=[ImporterIssue(**issue) for issue in issues],
                )
            )

    def dump(self, path: Pathable, output_format="json", indent=4):
        """Dump the summary to a file."""
        if output_format == "json":
            Path(path).write_text(
                json.dumps(
                    {
                        "diffsync": self.diffsync,
                        "source": {
                            summary.content_type: {
                                **summary._asdict(),
                                "fields": {field.name: field._asdict() for field in summary.fields},
                                "stats": summary.stats.__dict__,
                            }
                            for summary in self.source
                        },
                        "nautobot": {
                            summary.content_type: {
                                **summary._asdict(),
                                "issues": [issue._asdict() for issue in summary.issues],
                                "stats": summary.stats.__dict__,
                            }
                            for summary in self.nautobot
                        },
                    },
                    indent=indent,
                ),
                encoding="utf-8",
            )
        elif output_format == "text":
            with open(path, "w", encoding="utf-8") as file:
                for line in self.get_summary():
                    file.write(line + "\n")
        else:
            raise ValueError(f"Unsupported format {output_format}")

    def print(self):
        """Print a summary of the import."""
        for line in self.get_summary():
            print(line)

    def get_summary(self) -> Generator[str, None, None]:
        """Get a summary of the import."""
        yield _fill_up("* Import Summary:")

        yield _fill_up("= DiffSync Summary:")
        for key, value in self.diffsync.items():
            yield f"{key}: {value}"

        yield from self.get_stats("Source", self.source)
        yield from self.get_stats("Nautobot", self.nautobot)
        yield from self.get_content_types_deviations()
        yield from self.get_back_mapping()
        yield from self.get_issues()
        yield from self.get_fields_mapping()

        yield _fill_up("* End of Import Summary")

    def get_stats(self, caption: str, objects: Iterable[object]) -> Generator[str, None, None]:
        """Get formatted stats."""
        yield _fill_up("=", caption, "Stats:")
        for summary in objects:
            stats = getattr(summary, "stats", {}).__dict__
            if stats:
                yield _fill_up("-", getattr(summary, "content_type"))
                for key, value in stats.items():
                    yield f"{key}: {value}"

    def get_content_types_deviations(self) -> Generator[str, None, None]:
        """Get formatted content types deviations."""
        yield _fill_up("= Content Types Mapping Deviations:")
        yield "  Mapping deviations from source content type to Nautobot content type"

        for summary in self.data_sources:
            if summary.disable_reason:
                yield f"{summary.content_type} => {summary.nautobot_content_type} | Disabled with reason: {summary.disable_reason}"
            elif summary.extends_content_type:
                yield f"{summary.content_type} EXTENDS {summary.extends_content_type} => {summary.nautobot_content_type}"
            elif summary.content_type != summary.nautobot_content_type:
                yield f"{summary.content_type} => {summary.nautobot_content_type}"

    def get_back_mapping(self) -> Generator[str, None, None]:
        """Get formatted back mapping."""
        yield _fill_up("= Content Types Back Mapping:")
        yield "  Back mapping deviations from Nautobot content type to the source content type"

        back_mapping = {}

        for summary in self.data_sources:
            if summary.nautobot_content_type != summary.content_type:
                if summary.nautobot_content_type in back_mapping:
                    if back_mapping[summary.nautobot_content_type] != summary.content_type:
                        back_mapping[summary.nautobot_content_type] = None
                else:
                    back_mapping[summary.nautobot_content_type] = summary.content_type

        for nautobot_content_type, content_type in back_mapping.items():
            if content_type:
                yield f"{nautobot_content_type} => {content_type}"
            else:
                yield f"{nautobot_content_type} => Ambiguous"

    def get_issues(self) -> Generator[str, None, None]:
        """Get formatted issues."""
        yield _fill_up("= Importer issues:")
        for summary in self.nautobot:
            if summary.issues:
                yield _fill_up("-", summary.content_type)
                for issue in summary.issues:
                    yield f"{issue.uid} | {issue.issue_type} | {json.dumps(issue.name)} | {json.dumps(issue.message)}"

    def get_fields_mapping(self) -> Generator[str, None, None]:
        """Get formatted field mappings."""
        yield _fill_up("= Field Mappings:")

        def get_field(field: FieldSummary):
            yield field.name
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

            if field.nautobot_name:
                yield field.nautobot_name
                yield f"({field.nautobot_internal_type})"
            else:
                yield "CUSTOM TARGET"

        for summary in self.data_sources:
            yield _fill_up(
                "-",
                summary.content_type,
                "=>",
                summary.nautobot_content_type,
            )

            if summary.disable_reason:
                yield f"    Disable reason: {summary.disable_reason}"
            else:
                for field in summary.fields:
                    if "DATA" in field.sources:
                        yield " ".join(get_field(field))
