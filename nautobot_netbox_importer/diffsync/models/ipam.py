"""NetBox to Nautobot IPAM Models Mapping."""

import netaddr
from nautobot.ipam.models import get_default_namespace

from nautobot_netbox_importer.base import RecordData
from nautobot_netbox_importer.diffsync.models.locations import define_location
from nautobot_netbox_importer.generator import (
    DiffSyncBaseModel,
    ImporterPass,
    InvalidChoiceValueIssue,
    PreImportRecordResult,
    SourceAdapter,
    SourceField,
    SourceModelWrapper,
    fields,
)


def _fhrp_protocol_fallback(field: SourceField, source: RecordData, target: DiffSyncBaseModel, _) -> None:
    """Fallback for FHRPGroup protocol."""
    value = field.get_source_value(source)
    if value.startswith("vrrp"):
        target_value = "vrrp"
    else:
        return

    field.set_nautobot_value(target, target_value)
    raise InvalidChoiceValueIssue(field, value, target_value)


def _assign_ipaddress(source: RecordData, ipaddresstointerface: SourceModelWrapper) -> None:
    assigned_object_type = source.get("assigned_object_type")
    assigned_object_id = source.get("assigned_object_id")
    if not assigned_object_type or not assigned_object_id:
        return

    if isinstance(assigned_object_type, list):
        assigned_object_type = ".".join(assigned_object_type)

    if assigned_object_type != "dcim.interface":
        return

    ipaddress_id = source["id"]
    ipaddresstointerface.import_record(
        {
            "id": ipaddress_id,
            "ip_address": ipaddress_id,
            "interface": assigned_object_id,
        }
    )


def _add_missing_prefix(source: RecordData, prefix_wrapper: SourceModelWrapper) -> None:
    address = source.get("address", "")
    ip_network = netaddr.IPNetwork(address)
    prefix_cidr = str(ip_network.cidr)
    prefix_pk = prefix_wrapper.find_pk_from_uid(prefix_cidr)
    if prefix_pk:
        return

    instance = prefix_wrapper.import_record(
        {
            "id": prefix_cidr,
            "prefix": prefix_cidr,
            "status": "tbd",
        }
    )
    prefix_wrapper.nautobot.add_issue("CreatedMissingPrefix", diffsync_instance=instance)


def _deduplicate_prefix(
    prefix: SourceModelWrapper,
    wrapper: SourceModelWrapper,
    source: RecordData,
    importer_pass: ImporterPass,
) -> PreImportRecordResult:
    """Pre-cache prefix prefixes UUIDs to deduplicate them."""
    if importer_pass == ImporterPass.DEFINE_STRUCTURE:
        cidr = source["prefix"]
        was_cached = prefix.is_pk_cached(cidr)
        uuid = prefix.get_pk_from_uid(cidr)
        if was_cached:
            prefix.nautobot.add_issue(
                "DuplicatePrefix",
                f"Duplicate prefix `{cidr}` found, merging `{wrapper.content_type}:{source['id']}`",
                uid=uuid,
                data=source,
            )

        wrapper.cache_record_uids(source, uuid)

    return PreImportRecordResult.USE_RECORD


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox IPAM models to Nautobot."""
    options = getattr(adapter, "options", {})
    deduplicate_ipam = getattr(options, "deduplicate_ipam", False)

    def pre_import_ipaddress(source: RecordData, importer_pass: ImporterPass) -> PreImportRecordResult:
        if importer_pass == ImporterPass.DEFINE_STRUCTURE:
            host = source["address"].split("/")[0]
            ipaddress.cache_record_uids(source, ipaddress.get_pk_from_uid(host))

        return PreImportRecordResult.USE_RECORD

    def post_import_ipaddress(source: RecordData, _) -> None:
        _assign_ipaddress(source, ipaddresstointerface)
        _add_missing_prefix(source, prefix)

    ipaddress = adapter.configure_model(
        "ipam.ipaddress",
        pre_import_record=pre_import_ipaddress if deduplicate_ipam else None,
        post_import_record=post_import_ipaddress,
        fields={
            "role": fields.role(adapter, "ipam.role"),
        },
    )
    ipaddress.nautobot.set_instance_defaults(namespace=get_default_namespace())

    def pre_import_prefix(source: RecordData, importer_pass: ImporterPass) -> PreImportRecordResult:
        return _deduplicate_prefix(prefix, prefix, source, importer_pass)

    prefix = adapter.configure_model(
        "ipam.prefix",
        pre_import_record=pre_import_prefix,
        fields={
            "location": define_location,
            "role": fields.role(adapter, "ipam.role"),
        },
    )

    def pre_import_aggregate(source: RecordData, importer_pass: ImporterPass) -> PreImportRecordResult:
        return _deduplicate_prefix(prefix, aggregate, source, importer_pass)

    aggregate = adapter.configure_model(
        "ipam.aggregate",
        pre_import_record=pre_import_aggregate if deduplicate_ipam else None,
        nautobot_content_type="ipam.prefix",
    )
    adapter.configure_model(
        "ipam.vlan",
        fields={
            "group": "vlan_group",
            "location": define_location,
            "role": fields.role(adapter, "ipam.role"),
        },
    )
    adapter.configure_model(
        "ipam.FHRPGroup",
        nautobot_content_type="dcim.InterfaceRedundancyGroup",
        fields={
            "protocol": fields.fallback(callback=_fhrp_protocol_fallback),
        },
    )
    ipaddresstointerface = adapter.configure_model(
        "ipam.ipaddresstointerface",
        fields={
            "ip_address": "ip_address",
            "interface": "interface",
        },
    )
