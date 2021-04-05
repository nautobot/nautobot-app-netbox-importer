"""Tenancy model class definitions for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-many-ancestors
from typing import Optional

import nautobot.tenancy.models as tenancy

from .abstract import MPTTModelMixin, OrganizationalModel, PrimaryModel
from .references import TenantGroupRef


class TenantGroup(MPTTModelMixin, OrganizationalModel):
    """An arbitrary collection of Tenants."""

    _modelname = "tenantgroup"
    _attributes = (*OrganizationalModel._attributes, "name", "slug", "parent", "description")
    # Not all Tenants belong to a TenantGroup, so we don't treat them as children
    _nautobot_model = tenancy.TenantGroup

    name: str
    slug: str
    parent: Optional[TenantGroupRef]
    description: str


class Tenant(PrimaryModel):
    """A Tenant represents an organization served by the application owner."""

    _modelname = "tenant"
    _attributes = (*PrimaryModel._attributes, "name", "slug", "group", "description", "comments")
    _nautobot_model = tenancy.Tenant

    name: str
    slug: str
    group: Optional[TenantGroupRef]
    description: str
    comments: str
