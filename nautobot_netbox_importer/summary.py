"""Importer summary module."""

import json
import re
from pathlib import Path
from typing import Callable, Dict, Generator, Iterable, List, Mapping, NamedTuple, Optional, Pattern

from nautobot_netbox_importer.base import ContentTypeStr, FieldName, NullablePrimitives, Pathable, Uid

_TAG_EXPRESSIONS: Mapping[str, Pattern[str]] = {
    "InvalidCircuit": re.compile("A circuit termination must attach to either a location or a provider network"),
    "IncompatibleTerminationTypes": re.compile("Incompatible termination types"),
    "InvalidPlatform": re.compile("assigned platform is limited to"),
    "MissingParentLocation": re.compile(r"A Location of type .* must have a parent Location"),
}


class ImporterIssue(NamedTuple):
    """Represents an issue encountered during the import process.

    Fields:
        uid: Unique identifier for the issue
        name: Name of the affected object or field
        issue_type: Type of issue (e.g., 'validation', 'import_error')
        message: Descriptive error message
        data: Additional contextual data for debugging
        source_reference: Reference to the source data (mostly ID field) that caused the issue
    """

    uid: str
    name: str
    issue_type: str
    message: str
    data: Dict[str, str]
    source_reference: str = ""


DiffSyncSummary = Mapping[str, int]


class FieldSummary(NamedTuple):
    """Summarizes a field's mapping between source and target systems.

    Fields:
        name: Source field name in the source system
        nautobot_name: Corresponding field name in Nautobot (if any)
        nautobot_internal_type: Nautobot's internal data type for this field
        nautobot_can_import: Whether this field can be imported into Nautobot
        importer: Name of the importer function/method handling this field
        definition: Original field definition/value from source
        sources: List of sources where this field appears
        default_value: Default value used when source value is missing
        disable_reason: Reason why this field is disabled for import (if applicable)
        required: Whether this field is required in Nautobot
    """

    name: FieldName
    nautobot_name: Optional[FieldName]
    nautobot_internal_type: Optional[str]
    nautobot_can_import: Optional[bool]
    importer: Optional[str]
    definition: NullablePrimitives
    sources: List[str]
    default_value: NullablePrimitives
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
    created = 0
    updated = 0
    placeholders = 0


class SourceModelSummary(NamedTuple):
    """Summarizes a source model's mapping to Nautobot and import statistics.

    Fields:
        content_type: Source content type string identifier
        content_type_id: Numeric ID of the source content type
        extends_content_type: Parent content type that this model extends (if any)
        nautobot_content_type: Target Nautobot content type
        disable_reason: Reason why this model is disabled for import (if applicable)
        identifiers: List of fields used to uniquely identify instances
        disable_related_reference: Whether related references are disabled
        forward_references: Configuration for forward references handling
        pre_import: Pre-import processing function/method name
        post_import: Post-import processing function/method name
        fields: List of field summaries for this model
        flags: Feature flags applied to this model
        default_reference_uid: Default UID used for reference when actual reference is missing
        stats: Statistics about the source model's import process
    """

    content_type: ContentTypeStr
    content_type_id: int
    extends_content_type: Optional[ContentTypeStr]
    nautobot_content_type: ContentTypeStr
    disable_reason: str
    identifiers: Optional[List[FieldName]]
    disable_related_reference: bool
    forward_references: Optional[str]
    fields: List[FieldSummary]
    flags: str
    default_reference_uid: Optional[Uid]
    stats: SourceModelStats
    pre_import: Optional[str] = None
    post_import: Optional[str] = None


class NautobotModelSummary(NamedTuple):
    """Summarizes a Nautobot model's import results and any issues.

    Fields:
        content_type: Nautobot content type string identifier
        content_type_id: Numeric ID of the Nautobot content type (if available)
        flags: Feature flags applied to this model
        disabled: Whether this model is disabled for import
        stats: Statistics about the Nautobot model's import process
        issues: List of issues encountered during import for this model
    """

    content_type: ContentTypeStr
    content_type_id: Optional[int]
    flags: str
    disabled: bool
    stats: NautobotModelStats
    issues: List[ImporterIssue]


_FILL_UP_LENGTH = 100


def _fill_up(*values) -> str:
    """Format values into a padded string of consistent length.

    Args:
        *values: Values to join with spaces and pad

    Returns:
        A string padded with the first character of the first value to reach the defined length

    Examples:
        >>> _fill_up("* Import Summary:")
        "* Import Summary: **********************************************************************************"

        >>> _fill_up("= DiffSync Summary:")
        "= DiffSync Summary: ================================================================================"

        >>> _fill_up("-", "dcim.device")
        "- dcim.device --------------------------------------------------------------------------------------"
    """
    fill = values[0][0]
    result = " ".join(str(value) for value in values) + " " + fill
    return result + (fill * (_FILL_UP_LENGTH - len(result)))


def serialize_to_summary(value) -> NullablePrimitives:
    """Serialize a value to a summary-compatible format.

    Args:
        value (NullablePrimitives): The value to serialize

    Returns:
        NullablePrimitives: A summary-compatible representation of the value
        - Returns None for None values
        - Returns primitive types (str, bool, int, float) as-is
        - Returns function/method name for callables
        - Returns string representation for other types

    Examples:
        >>> serialize_to_summary(None)
        None
        >>> serialize_to_summary("string")
        "string"
        >>> serialize_to_summary(42)
        42
    """
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Callable):
        return value.__name__
    return str(value)


class ImportSummary:
    """Container class for import operation summary data.

    Stores, processes and formats information about source models,
    target Nautobot models, and DiffSync operations during an import process.
    """

    def __init__(self):
        """Initialize the import summary with empty collections."""
        self.source: List[SourceModelSummary] = []
        self.nautobot: List[NautobotModelSummary] = []
        self.diffsync: DiffSyncSummary = {}

    @property
    def data_sources(self) -> Generator[SourceModelSummary, None, None]:
        """Get source models originating from data.

        Yields:
            SourceModelSummary: Objects that originates from source data.
        """
        for summary in self.source:
            if any(field for field in summary.fields if "DATA" in field.sources):
                yield summary

    @property
    def data_nautobot_models(self) -> Generator[NautobotModelSummary, None, None]:
        """Get Nautobot models that correspond to data sources.

        Yields:
            NautobotModelSummary: Objects that have corresponding entries in data_sources.
        """
        content_types = set(item.content_type for item in self.data_sources)

        for item in self.nautobot:
            if item.content_type in content_types:
                yield item

    def load(self, path: Pathable):
        """Load import summary from a JSON file.

        Loads the serialized summary information from a JSON file
        into the current instance.

        Args:
            path (Pathable): Path-like object pointing to a JSON summary file

        Examples:
            >>> summary = ImportSummary()
            >>> summary.load("import_results.json")
        """
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

    def dump(self, path: Pathable, output_format: str = "json", indent: int = 4):
        """Save the import summary to a file.

        Args:
            path (Pathable): Path-like object where to save the summary
            output_format (str): Format to save in ('json' or 'text')
            indent (int): Number of spaces for JSON indentation (if output_format is 'json')

        Raises:
            ValueError: If an unsupported output format is specified

        Examples:
            >>> summary.dump("/tmp/import_results.json")
            >>> summary.dump("/tmp/import_results.txt", output_format="text")
        """
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
        """Print a formatted summary of the import to stdout."""
        for line in self.get_summary():
            print(line)

    def get_summary(self) -> Generator[str, None, None]:
        """Generate a formatted text representation of the import summary.

        Yields:
            str: Formatted lines with the import summary
        """
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
        """Generate formatted statistics for a collection of objects.

        Args:
            caption (str): Caption for the statistics section
            objects (Iterable[object]): Collection of objects to summarize

        Yields:
            str: Formatted lines of statistics information
        """
        yield _fill_up("=", caption, "Stats:")
        for summary in objects:
            stats = getattr(summary, "stats", {}).__dict__
            if stats:
                yield _fill_up("-", getattr(summary, "content_type"))
                for key, value in stats.items():
                    yield f"{key}: {value}"

    def get_content_types_deviations(self) -> Generator[str, None, None]:
        """Generate formatted information about content type mapping deviations.

        Shows how source content types map to Nautobot content types,
        highlighting extensions and non-standard mappings.

        Yields:
            str: Formatted lines describing content type mapping deviations
        """
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
        """Generate formatted information about reverse content type mapping.

        Shows how Nautobot content types map back to source content types,
        identifying ambiguous mappings where multiple source types map to the same Nautobot type.

        Yields:
            str: Formatted lines describing back mapping from Nautobot to source content types
        """
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
        """Generate formatted information about issues encountered during import.

        Groups issues by Nautobot content type and formats them for readability.

        Yields:
            str: Formatted lines describing import issues
        """
        yield _fill_up("= Importer issues:")
        for summary in self.nautobot:
            if summary.issues:
                yield _fill_up("-", summary.content_type)
                for issue in summary.issues:
                    yield f"{issue.uid} | {issue.source_reference} | {issue.issue_type} | {json.dumps(issue.name)} | {json.dumps(issue.message)}"

    def get_fields_mapping(self) -> Generator[str, None, None]:
        """Generate formatted information about field mappings between source and Nautobot.

        Shows how fields from source models map to fields in Nautobot models,
        including import methods and data types.

        Yields:
            str: Formatted lines describing field mappings
        """
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


def get_issue_tag(issue: ImporterIssue) -> str:
    """Get a tag for an issue."""
    if issue.issue_type == "ValidationError":
        for key, expression in _TAG_EXPRESSIONS.items():
            if re.search(expression, issue.message):
                return key

    return issue.issue_type
