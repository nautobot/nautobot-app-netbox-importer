"""Test the importing functionality of nautobot-netbox-importer."""

import os

from django.core.management import call_command
import yaml
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
