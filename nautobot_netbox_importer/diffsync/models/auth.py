"""Authentication-related models for nautobot-netbox-importer."""

from typing import List

from diffsync.enum import DiffSyncModelFlags
import django.contrib.auth.models as auth
import structlog

from .abstract import NautobotBaseModel
from .references import ContentTypeRef, PermissionRef


class Group(NautobotBaseModel):
    """Definition of a user group."""

    _modelname = "group"
    _identifiers = ("name",)
    _attributes = ("permissions",)
    _nautobot_model = auth.Group

    name: str
    permissions: List[PermissionRef] = []


class Permission(NautobotBaseModel):
    """Definition of a permissions rule."""

    _modelname = "permission"
    _identifiers = ("content_type", "codename")
    _attributes = ("name",)
    _nautobot_model = auth.Permission

    content_type: ContentTypeRef
    codename: str

    name: str

    def __init__(self, *args, **kwargs):
        """Set the IGNORE flag on permissions that refer to content-types that do not exist in Nautobot."""
        super().__init__(*args, **kwargs)
        if (
            self.content_type["app_label"]
            not in [
                "auth",
                "circuits",
                "contenttypes",
                "dcim",
                "extras",
                "ipam",
                "references",
                "taggit",
                "tenancy",
                "users",
                "virtualization",
            ]
            or self.content_type["model"] not in self.diffsync.top_level
        ):
            structlog.get_logger().debug(
                "Flagging permission for extraneous content-type as ignorable",
                diffsync=self.diffsync,
                app_label=self.content_type["app_label"],
                model=self.content_type["model"],
            )
            self.model_flags |= DiffSyncModelFlags.IGNORE
