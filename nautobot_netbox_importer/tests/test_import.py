"""Test cases for NetBox adapter."""
from tempfile import NamedTemporaryFile

import requests
from django.test import TestCase

from nautobot_netbox_importer.command_utils import enable_logging
from nautobot_netbox_importer.diffsync.adapter import NetBoxAdapter
from nautobot_netbox_importer.diffsync.adapter import NetBoxImporterOptions

_SKIPPED_CONTENT_TYPES = ["contenttypes.contenttype"]

_EXPECTED_SUMMARY = {}
_EXPECTED_SUMMARY["3.0"] = {
    "create": 4976,
    "delete": 0,
    "no-change": 3,
    "update": 0,
}
_EXPECTED_SUMMARY["3.1"] = {
    **_EXPECTED_SUMMARY["3.0"],
    "create": 5612,
    "no-change": 4,
}
_EXPECTED_SUMMARY["3.2"] = {
    **_EXPECTED_SUMMARY["3.1"],
    "create": 5866,
}
_EXPECTED_SUMMARY["3.3"] = {
    **_EXPECTED_SUMMARY["3.2"],
}
_EXPECTED_SUMMARY["3.4"] = {
    **_EXPECTED_SUMMARY["3.3"],
}
_EXPECTED_SUMMARY["3.5"] = {
    **_EXPECTED_SUMMARY["3.4"],
}
_EXPECTED_SUMMARY["3.6"] = {
    **_EXPECTED_SUMMARY["3.5"],
}

_EXPECTED_COUNTS = {}
_EXPECTED_COUNTS["3.0"] = {
    "circuits.circuit": 29,
    "circuits.circuittermination": 45,
    "circuits.circuittype": 4,
    "circuits.provider": 9,
    "circuits.providernetwork": 1,
    "dcim.cable": 108,
    "dcim.consoleport": 33,
    "dcim.consoleporttemplate": 11,
    "dcim.device": 63,
    "dcim.devicebay": 28,
    "dcim.devicetype": 13,
    "dcim.frontport": 912,
    "dcim.frontporttemplate": 120,
    "dcim.interface": 1113,
    "dcim.interfacetemplate": 267,
    "dcim.location": 95,
    "dcim.locationtype": 3,
    "dcim.manufacturer": 14,
    "dcim.platform": 3,
    "dcim.powerfeed": 48,
    "dcim.poweroutlet": 104,
    "dcim.poweroutlettemplate": 8,
    "dcim.powerpanel": 4,
    "dcim.powerport": 53,
    "dcim.powerporttemplate": 20,
    "dcim.rack": 42,
    "dcim.rearport": 630,
    "dcim.rearporttemplate": 73,
    "extras.customfield": 1,
    "extras.role": 16,
    "extras.status": 5,
    "ipam.prefix": 72,
    "ipam.rir": 7,
    "ipam.vlan": 63,
    "ipam.vlangroup": 7,
    "tenancy.tenant": 11,
    "tenancy.tenantgroup": 1,
    "users.user": 1,
    "virtualization.cluster": 32,
    "virtualization.clustergroup": 4,
    "virtualization.clustertype": 6,
    "virtualization.virtualmachine": 180,
    "virtualization.vminterface": 720,
}
_EXPECTED_COUNTS["3.1"] = {
    **_EXPECTED_COUNTS["3.0"],
    "auth.group": 1,
    "dcim.consoleport": 41,
    "dcim.device": 72,
    "dcim.devicebay": 14,
    "dcim.devicebaytemplate": 14,
    "dcim.devicetype": 14,
    "dcim.interface": 1554,
    "dcim.interfacetemplate": 268,
    "dcim.locationtype": 6,
    "dcim.manufacturer": 15,
    "dcim.powerport": 75,
    "dcim.powerporttemplate": 26,
    "dcim.rackreservation": 2,
    "dcim.virtualchassis": 4,
    "extras.role": 18,
    "extras.status": 6,
    "extras.tag": 26,
    "extras.taggeditem": 72,
    "ipam.ipaddress": 30,
    "ipam.prefix": 73,
    "ipam.rir": 8,
    "users.user": 6,
}
_EXPECTED_COUNTS["3.2"] = {
    **_EXPECTED_COUNTS["3.1"],
    "dcim.devicetype": 15,
    "dcim.interface": 1586,
    "dcim.interfacetemplate": 300,
    "ipam.ipaddress": 180,
    "ipam.prefix": 94,
    "ipam.routetarget": 12,
    "ipam.vrf": 6,
}
_EXPECTED_COUNTS["3.3"] = {
    **_EXPECTED_COUNTS["3.2"],
}
_EXPECTED_COUNTS["3.4"] = {
    **_EXPECTED_COUNTS["3.3"],
}
_EXPECTED_COUNTS["3.5"] = {
    **_EXPECTED_COUNTS["3.4"],
}
_EXPECTED_COUNTS["3.6"] = {
    **_EXPECTED_COUNTS["3.5"],
}

_EXPECTED_VALIDATION_ERRORS = {}
_EXPECTED_VALIDATION_ERRORS["3.0"] = {
    "dcim.powerfeed": 48,
}
_EXPECTED_VALIDATION_ERRORS["3.1"] = {
    **_EXPECTED_VALIDATION_ERRORS["3.0"],
}
_EXPECTED_VALIDATION_ERRORS["3.2"] = {
    **_EXPECTED_VALIDATION_ERRORS["3.1"],
}
_EXPECTED_VALIDATION_ERRORS["3.3"] = {
    **_EXPECTED_VALIDATION_ERRORS["3.2"],
}
_EXPECTED_VALIDATION_ERRORS["3.4"] = {
    **_EXPECTED_VALIDATION_ERRORS["3.3"],
}
_EXPECTED_VALIDATION_ERRORS["3.5"] = {
    **_EXPECTED_VALIDATION_ERRORS["3.4"],
}
_EXPECTED_VALIDATION_ERRORS["3.6"] = {
    **_EXPECTED_VALIDATION_ERRORS["3.5"],
}


class TestImport(TestCase):
    """Unittest for NetBox adapter."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        enable_logging()

    def _import(self, version: str):
        """Test import."""
        url = f"https://raw.githubusercontent.com/netbox-community/netbox-demo-data/master/netbox-demo-v{version}.json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with NamedTemporaryFile(mode="w+", delete=False) as tmp_file:
            tmp_file.write(response.text)
            tmp_filename = tmp_file.name

        with self.subTest(f"First Import NetBox v{version}"):
            source, created_models, skipped_count = self._import_file(tmp_filename, version)
            expected_summary = {
                **_EXPECTED_SUMMARY[version],
                "skip": skipped_count,
            }
            self.assertEqual(source.diff_summary, expected_summary, "Summary mismatch")
            validation_issues = {key: len(value) for key, value in source.nautobot.validation_issues.items()}
            self.assertEqual(validation_issues, _EXPECTED_VALIDATION_ERRORS[version], "Validation issues mismatch")

        with self.subTest(f"Re-Import NetBox v{version}"):
            expected_summary = {
                **expected_summary,
                "no-change": expected_summary["no-change"] + expected_summary["create"],
                "create": 0,
            }
            source, updated_models, skipped_count = self._import_file(tmp_filename, version)
            self.assertEqual(skipped_count, expected_summary["skip"], "Skipped count mismatch")
            self.assertEqual(source.diff_summary, expected_summary, "Summary mismatch")
            self.assertEqual(source.nautobot.validation_issues, {}, "No validation issues expected")
            self.assertEqual(updated_models, created_models, "Models counts mismatch")
            total = sum(created_models.values())
            self.assertEqual(total, expected_summary["no-change"], "Total mismatch")

    def _import_file(self, tmp_filename: str, version: str):
        source = NetBoxAdapter(
            tmp_filename,
            NetBoxImporterOptions(
                dry_run=False,
                bypass_data_validation=True,
                sitegroup_parent_always_region=True,
            ),
        )
        source.import_to_nautobot()

        expected_counts = _EXPECTED_COUNTS[version]
        imported_models = {}
        skipped_count = 0
        for content_type, wrapper in source.nautobot.wrappers.items():
            if wrapper.disabled:
                continue
            imported_count = wrapper.imported_count
            if imported_count == 0:
                continue
            if content_type in _SKIPPED_CONTENT_TYPES:
                skipped_count += imported_count
                continue
            imported_models[content_type] = imported_count

        self.assertEqual(imported_models, expected_counts, "Models counts mismatch")

        for content_type, wrapper in source.nautobot.wrappers.items():
            if content_type not in imported_models:
                continue
            expected_count = expected_counts[content_type]
            current_count = wrapper.model.objects.count()
            self.assertGreaterEqual(current_count, expected_count, f"Count mismatch for {content_type}")

        return source, imported_models, skipped_count


def _create_test_methods():
    """Create test method for each NetBox version."""

    def create_test_method(version):
        def test_import_version(self):
            # pylint: disable=protected-access
            self._import(version)

        return test_import_version

    for version in _EXPECTED_COUNTS:
        test_method = create_test_method(version)
        method_name = f"test_import_{version.replace('.', '_')}"
        setattr(TestImport, method_name, test_method)


_create_test_methods()
