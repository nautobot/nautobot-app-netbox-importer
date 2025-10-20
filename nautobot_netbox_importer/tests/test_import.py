"""Test cases for the NetBox adapter.

Tests use stored fixtures to verify that the import process works as expected.

Check the [fixtures README](./fixtures/README.md) for more details.
"""

import json
import warnings
from contextlib import contextmanager
from os import getenv
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command
from django.core.serializers import serialize
from django.test import TestCase
from nautobot import __version__ as nautobot_version
from nautobot.core.settings_funcs import is_truthy
from packaging.version import Version

from nautobot_netbox_importer.command_utils import enable_logging as mute_diffsync_logging
from nautobot_netbox_importer.diffsync.adapters import NetBoxAdapter, NetBoxImporterOptions
from nautobot_netbox_importer.generator.nautobot import NautobotModelWrapper
from nautobot_netbox_importer.summary import ImportSummary

_BUILD_FIXTURES = is_truthy(getenv("BUILD_FIXTURES", "False"))
_DONT_COMPARE_FIELDS = ["created", "last_updated"]
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
    """Unittest for NetBox adapter.

    Test cases are dynamically created based on the fixtures available for the current Nautobot version.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        apps.get_model("extras", "Role").objects.all().delete()
        apps.get_model("extras", "Status").objects.all().delete()

        apps.get_model("ipam", "Namespace").objects.get_or_create(
            pk="26756c2d-fddd-4128-9f88-dbcbddcbef45",
            name="Global",
            description="Default Global namespace. Created by Nautobot.",
        )

        mute_diffsync_logging()
        # pylint: disable=invalid-name
        self.maxDiff = None

    def _import(self, fixtures_name: str, fixtures_path: Path):
        """Test import.

        This method is called by each dynamically-created test case.

        Runs import twice, first time to import data and the second time to verify that nothing has changed.
        """
        expected_summary = ImportSummary()
        with warn_if_building_fixtures():
            expected_summary.load(fixtures_path / "summary.json")

        # Import the file to fresh Nautobot instance
        input_ref = _INPUTS.get(fixtures_name, fixtures_path / "input.json")
        version = _version_from_fixtures_name(fixtures_name)
        source = self._import_file(input_ref, version)

        # Build summary in text format in all cases to allow comparison
        source.summary.dump(fixtures_path / "summary.txt", output_format="text")

        if _BUILD_FIXTURES:
            source.summary.dump(fixtures_path / "summary.json")
            warnings.warn("Expected summary was generated, please re-run the test")

        with warn_if_building_fixtures():
            self.assertEqual(len(expected_summary.source), len(source.summary.source), "Source model counts mismatch")

        if _BUILD_FIXTURES:
            expected_summary = source.summary

        for expected_item in expected_summary.source:
            source_item = next(
                item for item in source.summary.source if item.content_type == expected_item.content_type
            )
            self.assertEqual(
                expected_item.stats.__dict__,
                source_item.stats.__dict__,
                f"Source model stats mismatch for {expected_item.content_type}",
            )

        self.assertEqual(
            len(expected_summary.nautobot),
            len(source.summary.nautobot),
            "Nautobot model counts mismatch",
        )

        expected_diffsync_summary = {
            "create": 0,
            "skip": 0,
            "no-change": 0,
            "delete": 0,
            "update": 0,
        }
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

        self.assertEqual(
            expected_summary.diffsync,
            source.summary.diffsync,
            "DiffSync summary mismatch",
        )
        self.assertEqual(
            expected_diffsync_summary,
            source.summary.diffsync,
            "Expected DiffSync summary mismatch",
        )

        # Verify data
        samples_path = fixtures_path / "samples"
        if not (samples_path).is_dir():
            samples_path.mkdir(parents=True)

        for wrapper in source.nautobot.wrappers.values():
            if wrapper.stats.source_created > 0:
                with self.subTest(f"Verify data {fixtures_name} {wrapper.content_type}"):
                    self._verify_model(samples_path, wrapper)

        # Re-import the same file to verify that nothing has changed
        second_source = self._import_file(input_ref, version)

        # In some cases, e.g. placeholders or cached records, it's not possible to verify "no-change"
        expected_diffsync_summary["no-change"] = second_source.summary.diffsync["no-change"]
        expected_diffsync_summary["create"] = save_failed_sum
        self.assertEqual(
            expected_diffsync_summary,
            second_source.summary.diffsync,
            "Expected DiffSync 2 summary mismatch",
        )

    def _import_file(self, input_ref, version: Version):
        source = NetBoxAdapter(
            input_ref,
            NetBoxImporterOptions(
                dry_run=False,
                netbox_version=version,
                bypass_data_validation=True,
                create_missing_cable_terminations=True,
                deduplicate_ipam=True,
                sitegroup_parent_always_region=True,
            ),
        )
        source.import_to_nautobot()

        return source

    def _verify_model_samples(self, wrapper: NautobotModelWrapper, path: Path):
        if not path.is_file():
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
                        value,
                        formatted_fields.get(key, ""),
                        f"Data mismatch for {wrapper.content_type} {uid} {key}",
                    )

    def _verify_model(self, samples_path: Path, wrapper: NautobotModelWrapper):
        """Verify data."""
        path = samples_path / f"{wrapper.content_type}.json"

        self.assertLessEqual(
            wrapper.stats.source_created - wrapper.stats.save_failed,
            wrapper.model.objects.count(),
            f"Nautobot instances count mismatch for {wrapper.content_type}",
        )

        try:
            self._verify_model_samples(wrapper, path)
        # pylint: disable=broad-exception-caught
        except Exception:
            if _BUILD_FIXTURES:
                _generate_model_samples(wrapper, path)
            else:
                raise


@contextmanager
def warn_if_building_fixtures():
    """Context manager to catch exceptions when building fixtures and issue a warning instead."""
    if _BUILD_FIXTURES:
        try:
            yield
        # pylint: disable=broad-exception-caught
        except Exception as error:
            warnings.warn(f"{error}")
    else:
        yield


def _generate_model_samples(wrapper: NautobotModelWrapper, path: Path):
    """Generate fixture file containing `_SAMPLE_COUNT` random instaces for the specified content type."""
    warnings.warn(f"Generating fixture for {wrapper.content_type} at {path}")

    # Find existing instances to keep them
    pks = []
    try:
        model = wrapper.model
        samples = json.loads(path.read_text())
        for sample in samples:
            uid = sample["pk"]
            if model.objects.filter(pk=uid).exists():
                pks.append(uid)
    # pylint: disable=broad-exception-caught
    except Exception:
        pass

    if len(pks) < _SAMPLE_COUNT:
        random_instances = wrapper.model.objects
        if pks:
            random_instances = random_instances.exclude(pk__in=pks)
        random_instances = random_instances.order_by("?")[: _SAMPLE_COUNT - len(pks)]
        for instance in random_instances:
            pks.append(instance.pk)
    else:
        pks = pks[:_SAMPLE_COUNT]

    call_command(
        "dumpdata",
        wrapper.content_type,
        indent=2,
        pks=",".join(f"{item}" for item in pks),
        output=path,
    )


def _version_from_fixtures_name(fixtures_name: str) -> Version:
    """Extract NetBox version from the fixtures name."""

    split = fixtures_name.split(".")
    return Version(f"{split[0]}.{split[1]}") if len(split) >= 2 else Version("3.0")


def _create_test_cases():
    """Dynamically create test cases, based on the current Nautobot version and defined fixtures.

    Example of test created: `TestImport.test_3_7_custom`
    """
    nautobot_version_str = ".".join(nautobot_version.split(".")[:2])
    fixtures_path = Path(__file__).parent / "fixtures" / f"nautobot-v{nautobot_version_str}"
    if not fixtures_path.is_dir() or not (fixtures_path / "dump.sql").is_file():
        raise ValueError(f"Fixtures for Nautobot {nautobot_version_str} are missing")

    def add_case(fixtures_name: str):
        def test_method(self):
            # pylint: disable=protected-access
            self._import(fixtures_name, fixtures_path / fixtures_name)

        setattr(TestImport, f"test_{fixtures_name.replace('.', '_')}", test_method)

    for fixture_dir in fixtures_path.iterdir():
        if fixture_dir.is_dir():
            add_case(fixture_dir.name)


_create_test_cases()
