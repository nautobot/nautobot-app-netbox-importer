"""Test the importing functionality of nautobot-netbox-importer."""
import os
import json
import copy
from unittest.mock import Mock
from packaging import version

import yaml
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from nautobot.extras.models import ObjectChange
from nautobot_netbox_importer.management.commands.import_netbox_json import Command
from nautobot_netbox_importer.management.commands.import_netbox_objectchange_json import Command as CommandObjChange
from .test_import import TestImport


NETBOX_DATA_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "netbox_dump.json")
NETBOX_OBJECTCHANGE_DATA_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "netbox_objectchange_dump.json")
NAUTOBOT_DATA_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "nautobot_expectations.yaml")
NAUTOBOT_OBJECTCHANGE_DATA_FILE = os.path.join(
    os.path.dirname(__file__), "fixtures", "nautobot_objectchange_expectations.yaml"
)


class TestImportObjectChange(TestImport):
    """Test the importing functionality of nautobot-netbox-importer, for ObjectChange objects.

    It is mostly reusing same tests as TestImport, but with an extra command during TestData Setup.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        """One-time setup function called before running the test functions in this class."""
        super().setUpTestData()

        with open(NETBOX_DATA_FILE, "r", encoding="utf-8") as file_handle_1:
            with open(NETBOX_OBJECTCHANGE_DATA_FILE, "r", encoding="utf-8") as file_handle_2:
                CommandObjChange().handle(
                    json_file=file_handle_1,
                    objectchange_json_file=file_handle_2,
                    netbox_version=version.parse("2.10.4"),
                    verbosity=0,
                )

        with open(NAUTOBOT_OBJECTCHANGE_DATA_FILE, "r", encoding="utf-8") as handle:
            cls.nautobot_data += yaml.safe_load(handle)


class TestImportObjectChangeMethods(TestCase):
    """Test to import Command methods for import_netbox_objectchange_json."""

    def setUp(self) -> None:
        """Pre-test setup function.

        Note that this was originally a setUpTestData() classmethod, but when moving to a newer version of Django,
        we found that then accessing `self.cmd` would result in Django throwing an infinite RecursionError.
        Probably a Django bug, but changing to setUp() appears to avoid the issue at the cost of slightly slower tests.
        """
        self.cmd = CommandObjChange()
        self.cmd.logger = Mock()
        self.cmd.logger.warning = Mock()

        # Import base test data into Nautobot
        with open(NETBOX_DATA_FILE, "r", encoding="utf-8") as handle:
            Command().handle(
                json_file=handle,
                netbox_version=version.parse("2.10.4"),
                verbosity=0,
                bypass_data_validation=False,
            )

            # Create ContentType Mappings
            self.cmd.netbox_contenttype_mapping = {}
            handle.seek(0)
            for entry in json.load(handle):
                if entry["model"] == "contenttypes.contenttype":
                    self.cmd.netbox_contenttype_mapping[entry["pk"]] = (
                        entry["fields"]["app_label"],
                        entry["fields"]["model"],
                    )
        self.cmd.nautobot_contenttype_mapping = {}
        for entry in ContentType.objects.all():
            self.cmd.nautobot_contenttype_mapping[(entry.app_label, entry.model)] = entry.id

        # Load the objectchange data into memory in preparation for the test
        with open(NETBOX_OBJECTCHANGE_DATA_FILE, "r", encoding="utf-8") as handle:
            self.objectchange_data = json.load(handle)

    def test_map_object_type(self):
        """Validate map_object_type method."""
        ref_entry = self.objectchange_data[0]

        # Validate contenttype is valid
        entry = copy.deepcopy(ref_entry)
        for key in ("changed_object_type", "related_object_type"):
            if entry["fields"][key]:
                self.assertTrue(self.cmd.map_object_type(key, entry, set()))

        # Validate function when a nonexistent model in Nautobot is trying to be mapped from Netbox
        entry = copy.deepcopy(ref_entry)
        unexistant_contenttype = {"id": 1000, "tuple": ("unexistant", "model")}
        entry["fields"]["changed_object_type"] = unexistant_contenttype["id"]
        self.cmd.netbox_contenttype_mapping[unexistant_contenttype["id"]] = unexistant_contenttype["tuple"]
        self.assertFalse(self.cmd.map_object_type("changed_object_type", entry, set()))
        self.cmd.logger.warning.assert_called_once_with(
            f"{unexistant_contenttype['tuple']} key is not present in Nautobot"
        )

    def test_process_objectchange(self):
        """Validate process_objectchange method."""
        ref_entry = self.objectchange_data[0]

        entry = copy.deepcopy(ref_entry)
        self.cmd.process_objectchange(entry, set())
        obj = ObjectChange.objects.get(request_id=entry["fields"]["request_id"], time=entry["fields"]["time"])
        self.assertEqual(str(obj.request_id), entry["fields"]["request_id"])

        # Second processing is to assess that the function is idempotent
        entry = copy.deepcopy(ref_entry)
        self.cmd.process_objectchange(entry, set())
        obj = ObjectChange.objects.get(request_id=entry["fields"]["request_id"], time=entry["fields"]["time"])
        self.assertEqual(str(obj.request_id), entry["fields"]["request_id"])
