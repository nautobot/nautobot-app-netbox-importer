"""Test the importing functionality of nautobot-netbox-importer."""

import os

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from packaging import version
import yaml

from nautobot_netbox_importer.management.commands.import_netbox_json import Command


NETBOX_DATA_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "netbox_dump.json")
NAUTOBOT_DATA_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "nautobot_expectations.yaml")


class TestImport(TestCase):
    """Test the importing functionality of nautobot-netbox-importer."""

    @classmethod
    def setUpClass(cls) -> None:
        """One-time setup function called before running the test functions in this class."""
        super().setUpClass()
        with open(NETBOX_DATA_FILE, "r") as handle:
            Command().handle(json_file=handle, netbox_version=version.Version("2.10.4"), verbosity=0)
        with open(NAUTOBOT_DATA_FILE, "r") as handle:
            cls.nautobot_data = yaml.safe_load(handle)

    def fixup_refs(self, model_class, refs):
        """Convert any FK references in the given ids dict to actual model references."""
        for key, value in list(refs.items()):
            if isinstance(value, dict) and "ids" in value:
                field = getattr(model_class, key)
                related_model = field.field.related_model
                try:
                    related_record = related_model.objects.get(**self.fixup_refs(related_model, value["ids"]))
                except ObjectDoesNotExist:
                    self.fail(f"Record {related_model} {value['ids']} missing in Nautobot")
                refs[key] = related_record
            if isinstance(value, list):
                new_value = []
                for list_value in value:
                    if isinstance(list_value, dict) and "ids" in list_value:
                        field = getattr(model_class, key)
                        related_model = field.field.related_model
                        try:
                            related_record = related_model.objects.get(
                                **self.fixup_refs(related_model, list_value["ids"])
                            )
                        except ObjectDoesNotExist:
                            self.fail(f"Record {related_model} {list_value['ids']} missing in Nautobot")
                        list_value = related_record
                    new_value.append(list_value)
                refs[key] = new_value

        return refs

    def test_imported_data_correctness(self):
        """Iterate over all imported data and check its correctness."""
        for data in self.nautobot_data:
            # No doubt there is a more efficient way to do this...
            content_type_string = data["model"]
            app_label, model = content_type_string.split(".")
            if "ids" not in data:
                self.fail(f"Bad data: missing 'ids' for record {data}")
            # TODO: unfortunately unittest doesn't report the number of passed subtests
            with self.subTest(content_type=content_type_string, ids=data["ids"]):
                content_type = ContentType.objects.get(app_label=app_label, model=model)
                model_class = content_type.model_class()
                try:
                    record = model_class.objects.get(**self.fixup_refs(model_class, data["ids"]))
                except ObjectDoesNotExist:
                    self.fail(f"Record {model_class} {data['ids']} missing in Nautobot")
                for key, expected_value in self.fixup_refs(model_class, data.get("fields", {})).items():
                    actual_value = getattr(record, key)
                    if isinstance(expected_value, str):
                        actual_value = str(actual_value)
                    # Fix up one-to-many and many-to-many relations
                    if isinstance(expected_value, list) and not isinstance(actual_value, list):
                        actual_value = list(actual_value.get_queryset())

                    self.assertEqual(expected_value, actual_value, f"key '{key}'' on {model} '{record}' is incorrect")

    def test_resync_without_changes_correctness(self):
        """Resync (with no changes to the source data) and verify that data is still correct."""
        with open(NETBOX_DATA_FILE, "r") as handle:
            Command().handle(json_file=handle, netbox_version=version.Version("2.10.4"), verbosity=0)
        # TODO check logs for errors and such
        self.test_imported_data_correctness()
