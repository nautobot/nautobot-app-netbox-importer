"""User-related DiffSync models for nautobot-netbox-importer."""

from datetime import datetime
from typing import List, Optional

import nautobot.users.models as users

from .abstract import ArrayField, NautobotBaseModel
from .references import ContentTypeRef, GroupRef, PermissionRef, UserRef


class ObjectPermission(NautobotBaseModel):
    """A mapping of view, add, change, and/or delete permissions for users and/or groups."""

    _modelname = "objectpermission"
    # This model doesn't have any defined uniqueness constraints, but name *ought* to be it
    _identifiers = ("name",)
    _attributes = ("object_types", "groups", "users", "actions", "constraints", "description", "enabled")
    _nautobot_model = users.ObjectPermission

    name: str

    object_types: List[ContentTypeRef] = []
    groups: List[GroupRef] = []
    users: List[UserRef] = []
    actions: ArrayField
    constraints: Optional[dict]
    description: str
    enabled: bool


class Token(NautobotBaseModel):
    """An API token used for user authentication."""

    _modelname = "token"
    _identifiers = ("key",)
    _attributes = ("user", "expires", "write_enabled", "description")
    _nautobot_model = users.Token

    key: str

    user: UserRef
    expires: Optional[datetime]
    write_enabled: bool
    description: str


class User(NautobotBaseModel):
    """A user account, for authentication and authorization purposes.

    Note that in NetBox this is actually two separate models - Django's built-in User class, and
    a custom UserConfig class - while in Nautobot it is a single custom User class model.
    """

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
        "config_data",
    )
    _nautobot_model = users.User

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
    config_data: dict

    last_login: Optional[datetime]
