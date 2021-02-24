"""User-related DiffSync models for nautobot-netbox-importer."""

from datetime import datetime
from typing import List, Mapping, Optional

import nautobot.users.models as users

from .abstract import ArrayField, NautobotBaseModel
from .references import ContentTypeRef, GroupRef, UserRef


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


class UserConfig(NautobotBaseModel):
    """Storage of user preferences in JSON."""

    _modelname = "userconfig"
    _identifiers = ("user",)
    _attributes = ("data",)
    _nautobot_model = users.UserConfig

    user: UserRef
    data: dict

    @staticmethod
    def create_nautobot_record(nautobot_model, ids: Mapping, attrs: Mapping, multivalue_attrs: Mapping):
        """Create or update an existing UserConfig Nautobot record as required.

        When a User object is created in Nautobot, an associated UserConfig is automatically created as well.
        Therefore, when we go to "create" a UserConfig after first creating a User, it actually will already exist.
        """
        return NautobotBaseModel.update_nautobot_record(nautobot_model, ids, attrs, multivalue_attrs)
