"""Test the importing functionality of nautobot-netbox-importer."""

import os
import json
import yaml
import copy
from unittest.mock import Mock
from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType
from nautobot_netbox_importer.management.commands.import_netbox_objectchange_json import Command
from .test_import import TestImport


NETBOX_DATA_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "netbox_dump.json")
NETBOX_OBJECTCHANGE_DATA_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "netbox_objectchange_dump.json")
NAUTOBOT_DATA_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "nautobot_objectchange_expectations.yaml")


class TestImportObjectChange(TestImport):
    """Test the importing functionality of nautobot-netbox-importer, for ObjectChange objects.

    It is mostly reusing same tests as TestImport, but with an extra command during TestData Setup.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        """One-time setup function called before running the test functions in this class."""
        # First we import the data without ObjectChanges
        call_command("import_netbox_json", NETBOX_DATA_FILE, "2.10.4", verbosity=0)
        call_command(
            "import_netbox_objectchange_json", NETBOX_DATA_FILE, NETBOX_OBJECTCHANGE_DATA_FILE, "2.10.4", verbosity=0
        )

        # TODO check stdout/stderr for errors and such
        with open(NAUTOBOT_DATA_FILE, "r") as handle:
            cls.nautobot_data = yaml.safe_load(handle)

        # Create ContentType Mappings
        with open(NETBOX_DATA_FILE, "r") as handle:
            cls.netbox_contenttype_mapping = {}
            for entry in json.load(handle):
                if entry["model"] == "contenttypes.contenttype":
                    cls.netbox_contenttype_mapping[entry["pk"]] = (
                        entry["fields"]["app_label"],
                        entry["fields"]["model"],
                    )
        cls.nautobot_contenttype_mapping = {}
        for entry in ContentType.objects.all():
            cls.nautobot_contenttype_mapping[(entry.app_label, entry.model)] = entry.id

        with open(NETBOX_OBJECTCHANGE_DATA_FILE, "r") as handle:
            cls.objectchange_data = yaml.safe_load(handle)

    def test_map_object_type(self):
        """validate map_object_type method."""

        cmd = Command()
        cmd.netbox_contenttype_mapping = self.netbox_contenttype_mapping
        cmd.nautobot_contenttype_mapping = self.nautobot_contenttype_mapping

        ref_entry = self.objectchange_data[0]

        # Validate contenttype is valid
        entry = copy.deepcopy(ref_entry)
        for key in ("changed_object_type", "related_object_type"):
            if entry["fields"][key]:
                assert cmd.map_object_type(key, entry, set()) is True

        # Validate function when an unexistatnt model in Nautobot is trying to be mapped from Netbox
        entry = copy.deepcopy(ref_entry)
        UNEXISTANT_CONTENT_TYPE = {"id": 1000, "tuple": ("unexistant", "model")}
        entry["fields"]["changed_object_type"] = UNEXISTANT_CONTENT_TYPE["id"]
        cmd.netbox_contenttype_mapping[UNEXISTANT_CONTENT_TYPE["id"]] = UNEXISTANT_CONTENT_TYPE["tuple"]
        cmd.logger = Mock()
        cmd.logger.warning = Mock()
        assert cmd.map_object_type("changed_object_type", entry, set()) is False
        cmd.logger.warning.assert_called_once_with(f"{UNEXISTANT_CONTENT_TYPE['tuple']} key is not present in Nautobot")
