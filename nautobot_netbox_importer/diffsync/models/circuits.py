"""Circuits class definitions for nautobot-netbox-importer.

Note that in most cases the same model classes are used for both NetBox imports and Nautobot exports.
Because this plugin is meant *only* for NetBox-to-Nautobot migration, the create/update/delete methods on these classes
are for populating data into Nautobot only, never the reverse.
"""
# pylint: disable=too-many-ancestors
from datetime import date
from typing import Optional

from pydantic import validator

import nautobot.circuits.models as circuits

from .abstract import (
    CableTerminationMixin,
    NautobotBaseModel,
    OrganizationalModel,
    PrimaryModel,
    StatusModelMixin,
)
from .references import CircuitRef, CircuitTypeRef, ProviderRef, SiteRef, TenantRef


class Provider(PrimaryModel):
    """Each Circuit belongs to a Provider."""

    _modelname = "provider"
    _identifiers = ("name",)
    _attributes = (
        *PrimaryModel._attributes,
        "slug",
        "asn",
        "account",
        "portal_url",
        "noc_contact",
        "admin_contact",
        "comments",
    )
    _nautobot_model = circuits.Provider

    name: str
    slug: str
    asn: Optional[int]
    account: str
    portal_url: str
    noc_contact: str
    admin_contact: str
    comments: str


class CircuitType(OrganizationalModel):
    """Circuits can be organized by their functional role."""

    _modelname = "circuittype"
    _identifiers = ("name",)
    _attributes = (*OrganizationalModel._attributes, "slug", "description")
    _nautobot_model = circuits.CircuitType

    name: str
    slug: str
    description: str


class Circuit(StatusModelMixin, PrimaryModel):
    """A communications circuit connects two points."""

    _modelname = "circuit"
    _identifiers = ("provider", "cid")
    _attributes = (
        *PrimaryModel._attributes,
        *StatusModelMixin._attributes,
        "status",
        "type",
        "tenant",
        "install_date",
        "commit_rate",
        "description",
        "comments",
    )
    _nautobot_model = circuits.Circuit

    provider: ProviderRef
    cid: str
    type: CircuitTypeRef
    tenant: Optional[TenantRef]
    install_date: Optional[date]
    commit_rate: Optional[int]
    description: str
    comments: str

    @validator("install_date", pre=True)
    def check_install_date(cls, value):  # pylint: disable=no-self-argument,no-self-use
        """Pre-cleaning: in JSON dump from Django, date string is formatted differently than Pydantic expects."""
        if isinstance(value, str) and value.endswith("T00:00:00Z"):
            value = value.replace("T00:00:00Z", "")
        return value


class CircuitTermination(CableTerminationMixin, NautobotBaseModel):
    """An endpoint of a Circuit."""

    _modelname = "circuittermination"
    _identifiers = ("circuit", "term_side")
    _attributes = (
        *CableTerminationMixin._attributes,
        "site",
        "port_speed",
        "upstream_speed",
        "xconnect_id",
        "pp_info",
        "description",
    )
    _nautobot_model = circuits.CircuitTermination

    circuit: CircuitRef
    term_side: str
    site: SiteRef
    port_speed: Optional[int]
    upstream_speed: Optional[int]
    xconnect_id: str
    pp_info: str
    description: str
