"""Test cases for NetBox adapter.

Tests are using stored fixtures to verify that the import process is working as expected.

It's also possible to generate and overwrite the fixtures by setting the `BUILD_FIXTURES` environment variable
to `True`, or by using the `invoke unittest --build-fixtures` option when running the tests.
"""

import json
from os import getenv
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.serializers import serialize
from django.test import TestCase
from nautobot.core.settings_funcs import is_truthy
from nautobot.ipam.models import Namespace

from nautobot_netbox_importer.command_utils import enable_logging as mute_diffsync_logging
from nautobot_netbox_importer.diffsync.adapters import NetBoxAdapter
from nautobot_netbox_importer.diffsync.adapters import NetBoxImporterOptions
from nautobot_netbox_importer.generator.nautobot import NautobotModelWrapper
from nautobot_netbox_importer.summary import ImportSummary

_BUILD_FIXTURES = is_truthy(getenv("BUILD_FIXTURES", "False"))
_DONT_COMPARE_FIELDS = ["created", "last_updated"]
_FIXTURES_PATH = Path(__file__).parent / "fixtures"
_NETBOX_DATA_REPOSITORY = "https://raw.githubusercontent.com/netbox-community/netbox-demo-data"
_NETBOX_DATA_URL = _NETBOX_DATA_REPOSITORY + "/c6a9c8835836a0629bde0713f33038ec9b8d56ea/json"
_SAMPLE_COUNT = 3

_INPUTS = {
    "3.0": f"{_NETBOX_DATA_URL}/netbox-demo-v3.0.json",
    "3.1": f"{_NETBOX_DATA_URL}/netbox-demo-v3.1.json",
    "3.2": f"{_NETBOX_DATA_URL}/netbox-demo-v3.2.json",
    "3.3": f"{_NETBOX_DATA_URL}/netbox-demo-v3.3.json",
    "3.4": f"{_NETBOX_DATA_URL}/netbox-demo-v3.4.json",
    "3.5": f"{_NETBOX_DATA_URL}/netbox-demo-v3.5.json",
    "3.6": f"{_NETBOX_DATA_URL}/netbox-demo-v3.6.json",
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
        # pylint: disable=invalid-name
        self.maxDiff = None

    def test_3_0(self):
        """Test import for NetBox 3.0."""
        self._import("3.0")

    def test_3_1(self):
        """Test import for NetBox 3.1."""
        self._import("3.1")

    def test_3_2(self):
        """Test import for NetBox 3.2."""
        self._import("3.2")

    def test_3_3(self):
        """Test import for NetBox 3.3."""
        self._import("3.3")

    def test_3_4(self):
        """Test import for NetBox 3.4."""
        self._import("3.4")

    def test_3_5(self):
        """Test import for NetBox 3.5."""
        self._import("3.5")

    def test_3_6(self):
        """Test import for NetBox 3.6."""
        self._import("3.6")

    def test_3_6_custom(self):
        """Test import for NetBox 3.6 with customized data."""
        self._import("3.6.custom")

    def test_3_7(self):
        """Test import for NetBox 3.7."""
        self._import("3.7")

    def _import(self, version: str):
        """Test import."""
        fixtures_path = _FIXTURES_PATH / version
        input_ref = _INPUTS.get(version, fixtures_path / "input.json")

        expected_summary = ImportSummary()
        try:
            expected_summary.load(fixtures_path / "summary.json")
        # pylint: disable=broad-exception-caught
        except Exception:
            if not _BUILD_FIXTURES:
                raise
            # Allow to generate summary
            expected_summary = None

        # Import the file to fresh Nautobot instance
        source = self._import_file(input_ref)

        # Build summary in text format in all cases to allow comparison
        source.summary.dump(fixtures_path / "summary.txt", output_format="text")
        if _BUILD_FIXTURES:
            source.summary.dump(fixtures_path / "summary.json")
        if not expected_summary:
            expected_summary = source.summary

        expected_diffsync_summary = {
            "create": 0,
            "skip": 0,
            "no-change": 0,
            "delete": 0,
            "update": 0,
        }

        self.assertEqual(len(expected_summary.source), len(source.summary.source), "Source model counts mismatch")

        for expected_item in expected_summary.source:
            source_item = next(
                item for item in source.summary.source if item.content_type == expected_item.content_type
            )
            self.assertEqual(
                expected_item.stats.__dict__,
                source_item.stats.__dict__,
                f"Source model stats mismatch for {expected_item.content_type}",
            )

        self.assertEqual(len(expected_summary.nautobot), len(source.summary.nautobot), "Nautobot model counts mismatch")

        save_failed_sum = 0
        for expected_item in expected_summary.nautobot:
            nautobot_item = next(
                item for item in source.summary.nautobot if item.content_type == expected_item.content_type
            )
            self.assertEqual(
                expected_item.stats.__dict__,
                nautobot_item.stats.__dict__,
                f"Nautobot model stats mismatch for {expected_item.content_type}",
            )
            expected_diffsync_summary["create"] += expected_item.stats.source_created
            expected_diffsync_summary["skip"] += expected_item.stats.source_ignored
            save_failed_sum += nautobot_item.stats.save_failed

        self.assertEqual(expected_summary.diffsync, source.summary.diffsync, "DiffSync summary mismatch")
        self.assertEqual(expected_diffsync_summary, source.summary.diffsync, "Expected DiffSync summary mismatch")

        # Re-import the same file to verify that nothing has changed
        second_source = self._import_file(input_ref)
        expected_diffsync_summary["no-change"] = expected_diffsync_summary["create"] - save_failed_sum
        expected_diffsync_summary["create"] = save_failed_sum
        self.assertEqual(
            expected_diffsync_summary, second_source.summary.diffsync, "Expected DiffSync 2 summary mismatch"
        )

        # Verify data
        samples_path = fixtures_path / "samples"
        if not (samples_path).is_dir():
            samples_path.mkdir(parents=True)

        for wrapper in source.nautobot.wrappers.values():
            if wrapper.stats.source_created > 0:
                with self.subTest(f"Verify data {version} {wrapper.content_type}"):
                    self._verify_model(samples_path, wrapper)

        if expected_summary is source.summary:
            self.fail("Expected summary was generated, please re-run the test")

    def _import_file(self, input_ref):
        source = NetBoxAdapter(
            input_ref,
            NetBoxImporterOptions(
                dry_run=False,
                bypass_data_validation=True,
                sitegroup_parent_always_region=True,
            ),
        )
        source.import_to_nautobot()

        return source

    def _verify_model(self, samples_path: Path, wrapper: NautobotModelWrapper):
        """Verify data."""
        self.assertLessEqual(
            wrapper.stats.source_created - wrapper.stats.save_failed,
            wrapper.model.objects.count(),
            f"Nautobot instances count mismatch for {wrapper.content_type}",
        )

        path = samples_path / f"{wrapper.content_type}.json"
        if not path.is_file():
            if _BUILD_FIXTURES:
                _generate_fixtures(wrapper, path)
                self.fail(f"Fixture file was generated, please re-run the test {path}")
            else:
                self.fail(f"Fixture file is missing: {path}")

        samples = json.loads(path.read_text())
        model = wrapper.model
        for sample in samples:
            self.assertEqual(
                sample["model"], wrapper.content_type, f"Content type mismatch for {wrapper.content_type} {sample}"
            )

            uid = sample["pk"]
            instance = model.objects.get(pk=uid)
            formatted = json.loads(serialize("json", [instance], ensure_ascii=False))[0]

            self.assertEqual(uid, formatted["pk"], f"PK mismatch for {wrapper.content_type} {instance}")
            formatted_fields = formatted["fields"]

            for key, value in sample["fields"].items():
                if key.startswith("_") or key in _DONT_COMPARE_FIELDS:
                    continue
                if key == "content_types":
                    self.assertEqual(
                        sorted(value),
                        sorted(formatted_fields[key]),
                        f"Data mismatch for {wrapper.content_type} {uid} {key}",
                    )
                else:
                    self.assertEqual(
                        value, formatted_fields[key], f"Data mismatch for {wrapper.content_type} {uid} {key}"
                    )


def _generate_fixtures(wrapper: NautobotModelWrapper, output_path: Path):
    """Generate fixture file containing `_SAMPLE_COUNT` random instaces for the specified content type.

    Should be used only with the lowest supported Nautobot version.
    """
    random_instances = wrapper.model.objects.order_by("?")[:_SAMPLE_COUNT]
    call_command(
        "dumpdata",
        wrapper.content_type,
        indent=2,
        pks=",".join(str(instance.pk) for instance in random_instances),
        output=output_path,
    )
