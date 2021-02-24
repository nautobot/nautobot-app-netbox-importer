"""Authentication-related models for nautobot-netbox-importer."""

from datetime import datetime
from typing import List, Optional

from diffsync.enum import DiffSyncModelFlags
from django.contrib.auth import get_user_model
import django.contrib.auth.models as auth
import structlog

from .abstract import NautobotBaseModel
from .references import ContentTypeRef, GroupRef, PermissionRef


_User = get_user_model()


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


class User(NautobotBaseModel):
    """A user account, for authentication and authorization purposes."""

    _modelname = "user"
    _identifiers = ("username",)
    _attributes = (
        "first_name",
        "last_name",
        "email",
        "password",
        "is_staff",
        "is_active",
        "is_superuser",
        "date_joined",
        "groups",
        "user_permissions",
    )
    _nautobot_model = _User

    username: str
    first_name: str
    last_name: str
    email: str
    password: str
    groups: List[GroupRef] = []
    user_permissions: List[PermissionRef] = []
    is_staff: bool
    is_active: bool
    is_superuser: bool
    date_joined: datetime

    last_login: Optional[datetime]
