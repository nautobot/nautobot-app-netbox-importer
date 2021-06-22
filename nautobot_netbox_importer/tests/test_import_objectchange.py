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

        with open(NETBOX_DATA_FILE, "r") as file_handle_1:
            with open(NETBOX_OBJECTCHANGE_DATA_FILE, "r") as file_handle_2:
                CommandObjChange().handle(
                    json_file=file_handle_1,
                    objectchange_json_file=file_handle_2,
                    netbox_version=version.parse("2.10.4"),
                    verbosity=0,
                )

        with open(NAUTOBOT_OBJECTCHANGE_DATA_FILE, "r") as handle:
            cls.nautobot_data += yaml.safe_load(handle)


class TestImportObjectChangeMethods(TestCase):
    """Test to import Command methods for import_netbox_objectchange_json."""

    @classmethod
    def setUpTestData(cls) -> None:
        """One-time setup function called before running the test functions in this class."""
        cls.cmd = CommandObjChange()
        cls.cmd.logger = Mock()
        cls.cmd.logger.warning = Mock()
        with open(NETBOX_DATA_FILE, "r") as handle:
            Command().handle(
                json_file=handle,
                netbox_version=version.parse("2.10.4"),
                verbosity=0,
                bypass_data_validation=False,
            )

            # Create ContentType Mappings
            cls.cmd.netbox_contenttype_mapping = {}
            handle.seek(0)
            for entry in json.load(handle):
                if entry["model"] == "contenttypes.contenttype":
                    cls.cmd.netbox_contenttype_mapping[entry["pk"]] = (
                        entry["fields"]["app_label"],
                        entry["fields"]["model"],
                    )
        cls.cmdnautobot_contenttype_mapping = {}
        for entry in ContentType.objects.all():
            cls.cmd.nautobot_contenttype_mapping[(entry.app_label, entry.model)] = entry.id

        with open(NETBOX_OBJECTCHANGE_DATA_FILE, "r") as handle:
            cls.objectchange_data = json.load(handle)

    def test_map_object_type(self):
        """Validate map_object_type method."""
        ref_entry = self.objectchange_data[0]

        # Validate contenttype is valid
        entry = copy.deepcopy(ref_entry)
        for key in ("changed_object_type", "related_object_type"):
            if entry["fields"][key]:
                assert self.cmd.map_object_type(key, entry, set()) is True

        # Validate function when a nonexistent model in Nautobot is trying to be mapped from Netbox
        entry = copy.deepcopy(ref_entry)
        unexistant_contenttype = {"id": 1000, "tuple": ("unexistant", "model")}
        entry["fields"]["changed_object_type"] = unexistant_contenttype["id"]
        self.cmd.netbox_contenttype_mapping[unexistant_contenttype["id"]] = unexistant_contenttype["tuple"]
        assert self.cmd.map_object_type("changed_object_type", entry, set()) is False
        self.cmd.logger.warning.assert_called_once_with(
            f"{unexistant_contenttype['tuple']} key is not present in Nautobot"
        )

    def test_process_objectchange(self):
        """Validate process_objectchange method."""
        ref_entry = self.objectchange_data[0]

        entry = copy.deepcopy(ref_entry)
        self.cmd.process_objectchange(entry, set())
        obj = ObjectChange.objects.get(request_id=entry["fields"]["request_id"], time=entry["fields"]["time"])
        assert str(obj.request_id) == entry["fields"]["request_id"]

        # Second processing is to assess that the function is idempotent
        entry = copy.deepcopy(ref_entry)
        self.cmd.process_objectchange(entry, set())
        obj = ObjectChange.objects.get(request_id=entry["fields"]["request_id"], time=entry["fields"]["time"])
        assert str(obj.request_id) == entry["fields"]["request_id"]
