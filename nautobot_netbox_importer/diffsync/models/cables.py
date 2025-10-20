# COMPATIBLE_TERMINATION_TYPES = {
#     "circuittermination": ["interface", "frontport", "rearport", "circuittermination"],
#     "consoleport": ["consoleserverport", "frontport", "rearport"],
#     "consoleserverport": ["consoleport", "frontport", "rearport"],
#     "interface": ["interface", "circuittermination", "frontport", "rearport"],
#     "frontport": [
#         "consoleport",
#         "consoleserverport",
#         "interface",
#         "frontport",
#         "rearport",
#         "circuittermination",
#     ],
#     "powerfeed": ["powerport"],
#     "poweroutlet": ["powerport"],
#     "powerport": ["poweroutlet", "powerfeed"],
#     "rearport": [
#         "consoleport",
#         "consoleserverport",
#         "interface",
#         "frontport",
#         "rearport",
#         "circuittermination",
#     ],
# }
"""DCIM data related functions."""

from diffsync import DiffSyncModel
from nautobot.dcim.constants import COMPATIBLE_TERMINATION_TYPES

from nautobot_netbox_importer.base import PLACEHOLDER_UID, ContentTypeStr, RecordData, Uid
from nautobot_netbox_importer.generator import (
    EMPTY_VALUES,
    DiffSyncBaseModel,
    PreImportRecordResult,
    SourceAdapter,
    SourceField,
    SourceModelWrapper,
)

_FALLBACK_TERMINATION_TYPE = "circuittermination"
_CIRCUIT_MODELS = {"circuittermination"}
_IGNORE_CABLE_LABELS = (
    "connected",
    "testing",
    "planned",
    "decommissioned",
    "disconnected",
    "failed",
    "unknown",
)


def _pre_import_cable_termination(source: RecordData, _) -> PreImportRecordResult:
    cable_end = source.pop("cable_end").lower()
    source["id"] = source.pop("cable")
    source[f"termination_{cable_end}_type"] = source.pop("termination_type")
    source[f"termination_{cable_end}_id"] = source.pop("termination_id")

    return PreImportRecordResult.USE_RECORD


def _define_cable_label(field: SourceField) -> None:
    """Define the cable label field importer.

    Importer uses cable.id if label is empty or contains any of the ignored labels.
    """

    def cable_label_importer(source: RecordData, target: DiffSyncBaseModel) -> None:
        value = field.get_source_value(source)

        if value:
            value = str(value).strip()

        if value in EMPTY_VALUES or value.lower() in _IGNORE_CABLE_LABELS:
            value = str(source["id"])

        field.set_nautobot_value(target, value)

    field.set_importer(cable_label_importer)


def _get_first_compatible_termination_type(stripped_type: str) -> ContentTypeStr:
    """Determine the first compatible termination type for a given termination.

    This function identifies the first compatible termination type based on the
    given termination string, falling back to '_FALLBACK_TERMINATION_TYPE' if
    no compatibility is found.

    Args:
        stripped_type (str): The termination type with 'dcim.' prefix removed

    Returns:
        str: The compatible termination type with 'dcim.' prefix

    Examples:
        >>> _get_first_compatible_termination_type("interface")
        'dcim.interface'

        >>> _get_first_compatible_termination_type("poweroutlet")
        'dcim.powerport'

        >>> _get_first_compatible_termination_type("unknown")
        'circuits.circuittermination'
    """

    def get_type(model_name: str) -> ContentTypeStr:
        return f"circuits.{model_name}" if model_name in _CIRCUIT_MODELS else f"dcim.{model_name}"

    if stripped_type not in COMPATIBLE_TERMINATION_TYPES:
        return get_type(_FALLBACK_TERMINATION_TYPE)

    types = COMPATIBLE_TERMINATION_TYPES[stripped_type]
    if _FALLBACK_TERMINATION_TYPE in types:
        return get_type(_FALLBACK_TERMINATION_TYPE)

    return get_type(types[0])


def _get_termination(uid: Uid, type_: ContentTypeStr, other_type: ContentTypeStr) -> tuple[Uid, ContentTypeStr]:
    """Determine the appropriate termination for a cable side.

    This function evaluates cable termination data and returns correct termination information
    based on compatibility rules.

    Args:
        uid (Uid): UID of the current termination
        type_ (ContentTypeStr): Type of the current termination
        other_type (ContentTypeStr): Type of the opposite termination

    Returns:
        tuple[str, str]: A tuple containing (termination_id, termination_type)

    Examples:
        >>> _get_termination("123", "dcim.interface", "dcim.frontport")
        ('123', 'dcim.interface')

        >>> _get_termination("", "dcim.interface", "dcim.poweroutlet")
        ('placeholder', 'circuit.circuittermination')

        >>> _get_termination("123", "", "dcim.frontport")
        ('123', 'dcim.interface')

        >>> _get_termination("123", "dcim.interface", "")
        ('123', 'dcim.interface')

        >>> _get_termination("", "", "")
        ('placeholder', 'circuit.circuittermination')

        >>> _get_termination("456", "dcim.powerport", "dcim.poweroutlet")
        ('456', 'dcim.powerport')
    """
    type_stripped = type_.split(".")[1] if type_ else ""
    other_stripped = other_type.split(".")[1] if other_type else ""
    first_compatible = _get_first_compatible_termination_type(other_stripped)

    if not type_:
        uid = PLACEHOLDER_UID
        type_ = first_compatible

    if not uid:
        uid = PLACEHOLDER_UID

    if not other_type:
        return uid, type_

    if type_stripped in COMPATIBLE_TERMINATION_TYPES and other_stripped in COMPATIBLE_TERMINATION_TYPES.get(
        type_stripped, []
    ):
        return uid, type_

    return PLACEHOLDER_UID, first_compatible


def _update_cable_termination(wrapper: SourceModelWrapper, cable: DiffSyncModel, side: str) -> None:
    """Update cable termination information for a specific side.

    This function retrieves termination data for the specified side of a cable, determines
    the appropriate termination using _get_termination(), and updates the cable if needed.

    Args:
        wrapper (SourceModelWrapper): Model wrapper containing field definitions
        cable (DiffSyncModel): The cable model to update
        side (str): Which side of the cable to update ('a' or 'b')
    """
    adapter = wrapper.adapter

    old_uid = getattr(cable, f"termination_{side}_id", "")
    old_type_id = getattr(cable, f"termination_{side}_type_id", 0)
    old_type = adapter.nautobot.get_content_type_str(old_type_id) if old_type_id else ""
    other_type = getattr(cable, f"termination_{'b' if side == 'a' else 'a'}_type", "")

    new_uid, new_type = _get_termination(old_uid, old_type, other_type)

    if new_uid == old_uid and new_type == old_type:
        return

    source_field = wrapper.fields[f"termination_{side}_type"]
    source_field.set_nautobot_value(cable, adapter.get_nautobot_content_type_uid(new_type))

    if new_uid == PLACEHOLDER_UID:
        type_wrapper = adapter.get_or_create_wrapper(new_type)
        new_instance = type_wrapper.import_placeholder(
            f"_dcim.cable_{getattr(cable, wrapper.nautobot.pk_field.name)}_side_{side}",
            {
                "cable": cable.id,  # type: ignore
            },
        )
        new_uid = new_instance.id  # type: ignore
        cable_id = type_wrapper.get_pk_from_uid(new_uid)
        wrapper.add_reference(type_wrapper, cable_id)

        source_field = wrapper.fields[f"termination_{side}_id"]
        source_field.set_nautobot_value(cable, cable_id)

    source_field.add_issue(
        "UpdatedCableTermination",
        f"Cable termination {side.upper()} updated from {old_uid}, {old_type} to {new_uid}, {new_type}",
        cable,
    )


def create_missing_cable_terminations(adapter: SourceAdapter) -> None:
    """Fix cables by ensuring proper terminations.

    This function processes all cables from the source adapter and validates/fixes
    termination information for both sides of each cable.

    Args:
        adapter (SourceAdapter): The source adapter containing cable data
    """
    adapter.logger.info("Creating missing cable terminations ...")
    wrapper = adapter.get_or_create_wrapper("dcim.cable")

    for cable in adapter.get_all(wrapper.nautobot.diffsync_class):
        if getattr(cable, "termination_a_id", None) and getattr(cable, "termination_b_id", None):
            continue

        adapter.logger.debug(f"Processing missing cable terminations {getattr(cable, 'id')} ...")

        _update_cable_termination(wrapper, cable, "a")
        _update_cable_termination(wrapper, cable, "b")


def setup(adapter: SourceAdapter) -> None:
    """Map NetBox Cable related models to Nautobot."""
    adapter.disable_model("dcim.cablepath", "Recreated in Nautobot on signal when circuit termination is created")

    adapter.configure_model(
        "dcim.cable",
        fields={
            "label": _define_cable_label,
            "termination_a_type": "",
            "termination_a_id": "",
            "termination_b_type": "",
            "termination_b_id": "",
        },
    )

    adapter.configure_model(
        "dcim.cabletermination",
        extend_content_type="dcim.cable",
        pre_import_record=_pre_import_cable_termination,
    )
