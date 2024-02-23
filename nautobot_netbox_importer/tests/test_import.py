"""Test cases for NetBox adapter."""

import json
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.serializers import serialize
from django.test import TestCase
from nautobot.ipam.models import Namespace

from nautobot_netbox_importer.base import ContentTypeStr
from nautobot_netbox_importer.command_utils import enable_logging as mute_diffsync_logging
from nautobot_netbox_importer.diffsync.adapters import NetBoxAdapter
from nautobot_netbox_importer.diffsync.adapters import NetBoxImporterOptions

_DONT_COMPARE_FIELDS = ["created", "last_updated"]
_FIXTURES_PATH = Path(__file__).parent / "fixtures"
_NETBOX_DATA_URL = "https://raw.githubusercontent.com/netbox-community/netbox-demo-data"
_SAMPLE_COUNT = 3
_SKIPPED_CONTENT_TYPES = ["contenttypes.contenttype"]

_INPUTS = {
    "3.0": f"{_NETBOX_DATA_URL}/c6a9c8835836a0629bde0713f33038ec9b8d56ea/json/netbox-demo-v3.0.json",
    "3.1": f"{_NETBOX_DATA_URL}/c6a9c8835836a0629bde0713f33038ec9b8d56ea/json/netbox-demo-v3.1.json",
    "3.2": f"{_NETBOX_DATA_URL}/c6a9c8835836a0629bde0713f33038ec9b8d56ea/json/netbox-demo-v3.2.json",
    "3.3": f"{_NETBOX_DATA_URL}/c6a9c8835836a0629bde0713f33038ec9b8d56ea/json/netbox-demo-v3.3.json",
    "3.4": f"{_NETBOX_DATA_URL}/c6a9c8835836a0629bde0713f33038ec9b8d56ea/json/netbox-demo-v3.4.json",
    "3.5": f"{_NETBOX_DATA_URL}/c6a9c8835836a0629bde0713f33038ec9b8d56ea/json/netbox-demo-v3.5.json",
    "3.6": f"{_NETBOX_DATA_URL}/c6a9c8835836a0629bde0713f33038ec9b8d56ea/json/netbox-demo-v3.6.json",
}

# All versions specified in _EXPECTED_SUMMARY are tested as separate test cases
_EXPECTED_SUMMARY = {
    "3.0": 4979,
    "3.1": 5616,
    "3.2": 5870,
    "3.3": 5870,
    "3.4": 5870,
    "3.5": 5870,
    "3.6": 5870,
    "3.6.custom": 58,
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
_EXPECTED_COUNTS["3.6.custom"] = {
    "auth.group": 1,
    "dcim.device": 2,
    "dcim.devicetype": 2,
    "dcim.interfaceredundancygroup": 1,
    "dcim.location": 1,
    "dcim.locationtype": 2,
    "dcim.manufacturer": 1,
    "extras.customfield": 3,
    "extras.customfieldchoice": 3,
    "extras.note": 2,
    "extras.objectchange": 18,
    "extras.role": 1,
    "extras.status": 2,
    "tenancy.tenant": 11,
    "tenancy.tenantgroup": 1,
    "users.user": 6,
    "users.objectpermission": 1,
}

_EXPECTED_IMPORTER_ISSUES = {}
_EXPECTED_IMPORTER_ISSUES["3.0"] = {
    "dcim.powerfeed": 48,
}
_EXPECTED_IMPORTER_ISSUES["3.1"] = {
    **_EXPECTED_IMPORTER_ISSUES["3.0"],
}
_EXPECTED_IMPORTER_ISSUES["3.2"] = {
    **_EXPECTED_IMPORTER_ISSUES["3.1"],
}
_EXPECTED_IMPORTER_ISSUES["3.3"] = {
    **_EXPECTED_IMPORTER_ISSUES["3.2"],
}
_EXPECTED_IMPORTER_ISSUES["3.4"] = {
    **_EXPECTED_IMPORTER_ISSUES["3.3"],
}
_EXPECTED_IMPORTER_ISSUES["3.5"] = {
    **_EXPECTED_IMPORTER_ISSUES["3.4"],
}
_EXPECTED_IMPORTER_ISSUES["3.6"] = {
    **_EXPECTED_IMPORTER_ISSUES["3.5"],
}
_EXPECTED_IMPORTER_ISSUES["3.6.custom"] = {
    "dcim.device": 1,
    "dcim.location": 1,
}


# Ensure that SECRET_KEY is set to a known value, to generate the same UUIDs
@patch("django.conf.settings.SECRET_KEY", "testing_secret_key")
class TestImport(TestCase):
    """Unittest for NetBox adapter."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        Namespace.objects.get_or_create(
            pk="26756c2d-fddd-4128-9f88-dbcbddcbef45",
            name="Global",
            description="Default Global namespace. Created by Nautobot.",
        )

        mute_diffsync_logging()

    def _import(self, version: str):
        """Test import."""
        input_ref = _INPUTS.get(version, _FIXTURES_PATH / version / "input.json")

        # Import the file to fresh Nautobot instance
        source, created_models, skipped_count = self._import_file(input_ref, version)
        source.summary.dump(_FIXTURES_PATH / version / "summary.json")
        source.summary.dump(_FIXTURES_PATH / version / "summary.txt", output_format="text")
        expected_summary = {
            "create": _EXPECTED_SUMMARY[version],
            "skip": skipped_count,
            "no-change": 0,
            "delete": 0,
            "update": 0,
        }
        self.assertEqual(source.summary.diff_summary, expected_summary, "Summary mismatch")
        importer_issues = {key: len(value) for key, value in source.summary.importer_issues.items()}
        self.assertEqual(importer_issues, _EXPECTED_IMPORTER_ISSUES[version], "importer issues mismatch")

        # Re-import the same file to verify that nothing has changed
        expected_summary["no-change"] = expected_summary["create"]
        expected_summary["create"] = 0
        source, updated_models, skipped_count = self._import_file(input_ref, version)
        self.assertEqual(skipped_count, expected_summary["skip"], "Skipped count mismatch")
        self.assertEqual(source.summary.diff_summary, expected_summary, "Summary mismatch")
        self.assertEqual(source.summary.validation_issues, {}, "No validation issues expected")
        self.assertEqual(updated_models, created_models, "Models counts mismatch")
        total = sum(created_models.values())
        self.assertEqual(total, expected_summary["no-change"], "Total mismatch")

        # Verify data
        dir_path = _FIXTURES_PATH / version / "samples"
        if not (dir_path).is_dir():
            dir_path.mkdir(parents=True)
        for content_type in created_models:
            with self.subTest(f"Verify data {version} {content_type}"):
                self._verify_model(source, version, content_type)

    def _import_file(self, input_ref, version: str):
        source = NetBoxAdapter(
            input_ref,
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

    def _verify_model(self, source: NetBoxAdapter, version: str, content_type: ContentTypeStr):
        """Verify data."""
        path = _FIXTURES_PATH / version / "samples" / f"{content_type}.json"
        if not path.is_file():
            _generate_fixtures(source, content_type, path)
            self.fail("Fixture file was generated, please re-run the test")

        samples = json.loads(path.read_text())
        model = source.nautobot.wrappers[content_type].model
        for sample in samples:
            self.assertEqual(content_type, sample["model"], f"Content type mismatch for {content_type} {sample}")

            uid = sample["pk"]
            instance = model.objects.get(pk=uid)
            formatted = json.loads(serialize("json", [instance], ensure_ascii=False))[0]

            self.assertEqual(formatted["pk"], uid, f"PK mismatch for {content_type} {instance}")
            formatted_fields = formatted["fields"]

            for key, value in sample["fields"].items():
                if key.startswith("_") or key in _DONT_COMPARE_FIELDS:
                    continue
                if key == "content_types":
                    self.assertEqual(
                        sorted(formatted_fields[key]),
                        sorted(value),
                        f"Data mismatch for {content_type} {uid} {key}",
                    )
                else:
                    self.assertEqual(formatted_fields[key], value, f"Data mismatch for {content_type} {uid} {key}")


def _generate_fixtures(source: NetBoxAdapter, content_type: ContentTypeStr, output_path: Path):
    """Generate fixture file containing `_SAMPLE_COUNT` random instaces for the specified content type.

    Should be used only with the lowest supported Nautobot version.
    """
    wrapper = source.nautobot.wrappers[content_type]
    random_instances = wrapper.model.objects.order_by("?")[:_SAMPLE_COUNT]
    call_command(
        "dumpdata",
        content_type,
        indent=2,
        pks=",".join(str(instance.pk) for instance in random_instances),
        output=output_path,
    )


def _create_test_cases():
    """Create test method for each NetBox version."""

    def create_test_method(version):
        def test_import_version(self):
            # pylint: disable=protected-access
            self._import(version)

        return test_import_version

    directories = set(directory.name for directory in Path(_FIXTURES_PATH).glob("*") if directory.is_dir())

    for version in set(_INPUTS) | set(_EXPECTED_SUMMARY) | directories:
        test_method = create_test_method(version)
        method_name = f"test_import_{version.replace('.', '_')}"
        setattr(TestImport, method_name, test_method)


_create_test_cases()
