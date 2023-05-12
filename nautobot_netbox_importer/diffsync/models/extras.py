"""Extras class definitions for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-many-ancestors, too-few-public-methods
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import Field, validator
from diffsync.exceptions import ObjectNotFound
import structlog

import nautobot.extras.models as extras

from .abstract import (
    ChangeLoggedModelMixin,
    CustomFieldModelMixin,
    NautobotBaseModel,
)
from .references import (
    foreign_key_field,
    ClusterGroupRef,
    ClusterRef,
    ContentTypeRef,
    CustomFieldRef,
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


logger = structlog.get_logger()


class ConfigContext(ChangeLoggedModelMixin, NautobotBaseModel):
    """A set of arbitrary data available to Devices and VirtualMachines."""

    _modelname = "configcontext"
    _attributes = (
        *ChangeLoggedModelMixin._attributes,
        "name",
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
    _attributes = (
        "name",
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

    # Because marking a custom field as "required" doesn't automatically assign a value to pre-existing records,
    # we never want, when adding custom fields from NetBox, to flag fields as required=True.
    # Instead we store it in "actual_required" and fix it up only afterwards.
    actual_required: Optional[bool]

    _ignored_fields = {"choices"} | NautobotBaseModel._ignored_fields

    @classmethod
    def special_clean(cls, diffsync, ids, attrs):
        """Special-case handling for the "default" attribute."""
        if attrs.get("default") and attrs["type"] in ("select", "multiselect"):
            # There's a bit of a chicken-and-egg problem here in that we have to create a CustomField
            # before we can create any CustomFieldChoice records that reference it, but the "default"
            # attribute on the CustomField is only valid if it references an existing CustomFieldChoice.
            # So what we have to do is skip over the "default" field if it references a nonexistent CustomFieldChoice.
            default = attrs.get("default")
            try:
                diffsync.get("customfieldchoice", {"field": {"name": attrs["name"]}, "value": default})
            except ObjectNotFound:
                logger.debug(
                    "CustomFieldChoice not yet present to set as 'default' for CustomField, will fixup later",
                    field=attrs["name"],
                    default=default,
                )
                del attrs["default"]


class CustomFieldChoice(NautobotBaseModel):
    """One of the valid options for a CustomField of type "select" or "multiselect"."""

    _modelname = "customfieldchoice"
    # Since these only exist in Nautobot and not in NetBox, we can't match them between the two systems by PK.
    _identifiers = ("field", "value")
    _attributes = ("weight",)
    _nautobot_model = extras.CustomFieldChoice

    field: CustomFieldRef
    value: str
    weight: int = 100


class CustomLink(ChangeLoggedModelMixin, NautobotBaseModel):
    """A custom link to an external representation of a Nautobot object."""

    _modelname = "customlink"
    _attributes = (
        "name",
        "content_type",
        "text",
        "target_url",
        "weight",
        "group_name",
        "button_class",
        "new_window",
        *ChangeLoggedModelMixin._attributes,
    )
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
    _attributes = (
        "name",
        "content_type",
        "description",
        "template_code",
        "mime_type",
        "file_extension",
        *ChangeLoggedModelMixin._attributes,
    )
    _nautobot_model = extras.ExportTemplate

    name: str

    content_type: ContentTypeRef
    description: str
    template_code: str
    mime_type: str
    file_extension: str


class ImageAttachment(NautobotBaseModel):
    """An uploaded image which is associated with an object."""

    _modelname = "imageattachment"
    _attributes = ("content_type", "object_id", "image", "image_height", "image_width", "name", "created")
    _nautobot_model = extras.ImageAttachment

    content_type: ContentTypeRef
    _object_id = foreign_key_field("*content_type")
    object_id: _object_id
    image: str
    image_height: int
    image_width: int
    name: str
    created: datetime

    @validator("image", pre=True)
    def imagefieldfile_to_str(cls, value):  # pylint: disable=no-self-argument,no-self-use
        """Convert ImageFieldFile objects to strings."""
        if hasattr(value, "name"):
            value = value.name
        return value


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
                    if log_entry["status"] in new_value["run"]:
                        new_value["run"][log_entry["status"]] += 1
                    if log_entry["status"] in new_value["total"]:
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
    _attributes = ("job_id", "name", "obj_type", "completed", "user", "status", "data")
    _nautobot_model = extras.JobResult

    job_id: UUID

    name: str
    obj_type: ContentTypeRef
    completed: Optional[datetime]
    user: Optional[UserRef]
    status: str  # not a StatusRef!
    data: Optional[JobResultData]

    created: Optional[datetime]  # Not synced


class Note(ChangeLoggedModelMixin, NautobotBaseModel):
    """
    Representation of NetBox JournalEntry to Nautobot Note.

    NetBox fields ignored: kind
    Nautobot fields not supported by NetBox: user_name, slug
    """

    _modelname = "note"
    _attributes = (
        *ChangeLoggedModelMixin._attributes,
        "assigned_object_type",
        "assigned_object_id",
        "user",
        "note",
    )
    _nautobot_model = extras.Note

    assigned_object_type: ContentTypeRef
    _assigned_object_id = foreign_key_field("*assigned_object_type")
    assigned_object_id: _assigned_object_id
    # NetBox uses `created_by` where Nautobot uses `user`
    user: UserRef = Field(alias="created_by")
    # NetBox uses `comments` where Nautobot uses `note`
    note: str = Field(alias="comments")

    class Config:
        """Pydantic configuration of the Note class."""

        # Allow both "url" and "target_url" as property setters
        allow_population_by_field_name = True


class Status(ChangeLoggedModelMixin, NautobotBaseModel):
    """Representation of a status value."""

    _modelname = "status"
    _attributes = ("slug", "name", "color", "description", *ChangeLoggedModelMixin._attributes)  # TODO content_types?
    _nautobot_model = extras.Status

    slug: str
    name: str
    color: str
    description: str

    content_types: List = []


class Tag(ChangeLoggedModelMixin, CustomFieldModelMixin, NautobotBaseModel):
    """A tag that can be associated with various objects."""

    _modelname = "tag"
    _attributes = (
        *CustomFieldModelMixin._attributes,
        "name",
        "slug",
        "color",
        "description",
        *ChangeLoggedModelMixin._attributes,
    )
    _nautobot_model = extras.Tag

    name: str

    slug: str
    color: str
    description: str


class TaggedItem(NautobotBaseModel):
    """Mapping between a record and a Tag."""

    _modelname = "taggeditem"
    _attributes = ("content_type", "object_id", "tag")
    _nautobot_model = extras.TaggedItem

    content_type: ContentTypeRef
    _object_id = foreign_key_field("*content_type")
    object_id: _object_id
    tag: TagRef


class Webhook(ChangeLoggedModelMixin, NautobotBaseModel):
    """A Webhook defines a request that will be sent to a remote application."""

    _modelname = "webhook"
    _attributes = (
        "name",
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
        *ChangeLoggedModelMixin._attributes,
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
