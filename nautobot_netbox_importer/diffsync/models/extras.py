"""Extras class definitions for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-many-ancestors, too-few-public-methods
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import Field

import nautobot.extras.models as extras

from .abstract import (
    ArrayField,
    ChangeLoggedModelMixin,
    CustomFieldModelMixin,
    NautobotBaseModel,
)
from .references import (
    foreign_key_field,
    ClusterGroupRef,
    ClusterRef,
    ContentTypeRef,
    DeviceRoleRef,
    PlatformRef,
    RegionRef,
    SiteRef,
    TagRef,
    TenantGroupRef,
    TenantRef,
    UserRef,
)
from .validation import DiffSyncCustomValidationField


class ConfigContext(ChangeLoggedModelMixin, NautobotBaseModel):
    """A set of arbitrary data available to Devices and VirtualMachines."""

    _modelname = "configcontext"
    _identifiers = ("name",)
    _attributes = (
        "weight",
        "description",
        "is_active",
        "regions",
        "sites",
        "roles",
        "platforms",
        "cluster_groups",
        "clusters",
        "tenant_groups",
        "tenants",
        "tags",
        "data",
    )
    _nautobot_model = extras.ConfigContext

    name: str

    weight: int
    description: str
    is_active: bool
    regions: List[RegionRef] = []
    sites: List[SiteRef] = []
    roles: List[DeviceRoleRef] = []
    platforms: List[PlatformRef] = []
    cluster_groups: List[ClusterGroupRef] = []
    clusters: List[ClusterRef] = []
    tenant_groups: List[TenantGroupRef] = []
    tenants: List[TenantRef] = []
    tags: List[TagRef] = []
    data: dict


class CustomField(NautobotBaseModel):
    """Custom field defined on a model(s)."""

    _modelname = "customfield"
    _identifiers = ("name",)
    _attributes = (
        "content_types",
        "type",
        "label",
        "description",
        "required",
        "filter_logic",
        "default",
        "weight",
        "validation_minimum",
        "validation_maximum",
        "validation_regex",
        "choices",
    )
    _nautobot_model = extras.CustomField

    name: str

    content_types: List[ContentTypeRef] = []
    type: str
    label: str
    description: str
    required: bool
    filter_logic: str
    default: Optional[Any]  # any JSON value
    weight: int
    validation_minimum: Optional[int]
    validation_maximum: Optional[int]
    validation_regex: str
    choices: Optional[ArrayField]


class CustomLink(ChangeLoggedModelMixin, NautobotBaseModel):
    """A custom link to an external representation of a Nautobot object."""

    _modelname = "customlink"
    _identifiers = ("name",)
    _attributes = ("content_type", "text", "target_url", "weight", "group_name", "button_class", "new_window")
    _nautobot_model = extras.CustomLink

    name: str

    content_type: ContentTypeRef
    text: str
    # Field name is "url" in NetBox, "target_url" in Nautobot
    target_url: str = Field(alias="url")
    weight: int
    group_name: str
    button_class: str
    new_window: bool

    class Config:
        """Pydantic configuration of the CustomLink class."""

        # Allow both "url" and "target_url" as property setters
        allow_population_by_field_name = True


class ExportTemplate(ChangeLoggedModelMixin, NautobotBaseModel):
    """A Jinja2 template for exporting records as text."""

    _modelname = "exporttemplate"
    _identifiers = ("name",)
    _attributes = ("content_type", "description", "template_code", "mime_type", "file_extension")
    _nautobot_model = extras.ExportTemplate

    name: str

    content_type: ContentTypeRef
    description: str
    template_code: str
    mime_type: str
    file_extension: str


class JobResultContentTypeRef(ContentTypeRef):
    """Map NetBox Script and Report contenttypes to Nautobot Job contenttype."""

    @classmethod
    def validate(cls, value):
        """Map Script and Report models to Job."""
        value = super().validate(value)
        if "model" in value and value["model"] in ("script", "report"):
            value["model"] = "job"
        return cls(value)


class JobResultData(DiffSyncCustomValidationField, dict):
    """Reformat NetBox Script and Report data to the new Nautobot JobResult data format."""

    @classmethod
    def validate(cls, value):
        """Translate data as needed."""
        if isinstance(value, dict):
            if "log" in value:
                # NetBox custom Script data, transform the result data to the new format
                # Old: {"log": [{"status": "success", "message": "..."}, ...], "output": "..."}
                # New: {"run": {"log": [(time, status, object, url, message), ...], "output": "...", "total": {...}}}
                new_value = {
                    "run": {"success": 0, "info": 0, "warning": 0, "failure": 0, "log": []},
                    "total": {"success": 0, "info": 0, "warning": 0, "failure": 0},
                    "output": value.get("output", ""),
                }
                for log_entry in value.get("log", []):
                    new_value["run"]["log"].append((None, log_entry["status"], None, None, log_entry["message"]))
                    new_value["run"][log_entry["status"]] += 1
                    new_value["total"][log_entry["status"]] += 1
                value = new_value
            else:
                # Either a Nautobot record (in which case no reformatting needed) or a NetBox Report result
                # For the latter, add "output" and "total" keys to the result.
                if "total" not in value:
                    totals = {
                        "success": 0,
                        "info": 0,
                        "warning": 0,
                        "failure": 0,
                    }
                    for test_results in value.values():
                        for key in ("success", "info", "warning", "failure"):
                            totals[key] += test_results[key]
                    value["total"] = totals
                if "output" not in value:
                    value["output"] = ""

        return cls(value)


class JobResult(NautobotBaseModel):
    """Results of running a Job / Script / Report."""

    _modelname = "jobresult"
    _identifiers = ("job_id",)
    _attributes = ("name", "obj_type", "completed", "user", "status", "data")
    _nautobot_model = extras.JobResult

    job_id: UUID

    name: str
    obj_type: JobResultContentTypeRef
    completed: Optional[datetime]
    user: Optional[UserRef]
    status: str  # not a StatusRef!
    data: Optional[JobResultData]

    created: Optional[datetime]  # Not synced


class Status(ChangeLoggedModelMixin, NautobotBaseModel):
    """Representation of a status value."""

    _modelname = "status"
    _identifiers = ("slug",)
    _attributes = ("name", "color", "description")  # TODO content_types?
    _nautobot_model = extras.Status

    slug: str
    name: str
    color: str
    description: str

    content_types: List = []


class Tag(ChangeLoggedModelMixin, CustomFieldModelMixin, NautobotBaseModel):
    """A tag that can be associated with various objects."""

    _modelname = "tag"
    _identifiers = ("name",)
    _attributes = (*CustomFieldModelMixin._attributes, "slug", "color", "description")
    _nautobot_model = extras.Tag

    name: str

    slug: str
    color: str
    description: str


class TaggedItem(NautobotBaseModel):
    """Mapping between a record and a Tag."""

    _modelname = "taggeditem"
    _identifiers = ("content_type", "object_id", "tag")
    _nautobot_model = extras.TaggedItem

    content_type: ContentTypeRef
    _object_id = foreign_key_field("*content_type")
    object_id: _object_id
    tag: TagRef


class Webhook(ChangeLoggedModelMixin, NautobotBaseModel):
    """A Webhook defines a request that will be sent to a remote application."""

    _modelname = "webhook"
    _identifiers = ("name",)
    _attributes = (
        "content_types",
        "type_create",
        "type_update",
        "type_delete",
        "payload_url",
        "enabled",
        "http_method",
        "http_content_type",
        "additional_headers",
        "body_template",
        "secret",
        "ssl_verification",
        "ca_file_path",
    )
    _nautobot_model = extras.Webhook

    name: str

    content_types: List[ContentTypeRef] = []
    type_create: bool
    type_update: bool
    type_delete: bool
    payload_url: str
    enabled: bool
    http_method: str
    http_content_type: str
    additional_headers: str
    body_template: str
    secret: str
    ssl_verification: bool
    ca_file_path: Optional[str]
