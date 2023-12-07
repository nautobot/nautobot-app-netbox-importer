"""Test cases for NetBox adapter."""
from tempfile import NamedTemporaryFile

import requests
from django.test import TestCase
from nautobot.core.utils.lookup import get_model_from_name

from nautobot_netbox_importer.command_utils import enable_logging
from nautobot_netbox_importer.diffsync.netbox import sync_to_nautobot

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
    "dcim.manufacturer": 15,
    "dcim.powerport": 75,
    "dcim.powerporttemplate": 26,
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
    "ipam.prefix": 94,
    "ipam.ipaddress": 180,
}

_EXPECTED_COUNTS["3.3"] = {
    **_EXPECTED_COUNTS["3.2"],
}

_EXPECTED_COUNTS["3.4"] = {
    **_EXPECTED_COUNTS["3.3"],
}


class TestSync(TestCase):
    """Unittest for NetBox adapter."""

    def test_sync_3_0(self):
        self._sync("3.0")

    def test_sync_3_1(self):
        self._sync("3.1")

    def test_sync_3_2(self):
        self._sync("3.2")

    def test_sync_3_3(self):
        self._sync("3.3")

    def test_sync_3_4(self):
        self._sync("3.4")

    def _sync(self, version: str):
        """Test sync."""
        enable_logging()

        url = f"https://raw.githubusercontent.com/netbox-community/netbox-demo-data/master/netbox-demo-v{version}.json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with NamedTemporaryFile(mode="w+", delete=False) as tmp_file:
            tmp_file.write(response.text)
            tmp_filename = tmp_file.name

        netbox = sync_to_nautobot(tmp_filename, dry_run=False)

        for content_type, expected_count in _EXPECTED_COUNTS[version].items():
            model = get_model_from_name(content_type)
            imported_count = netbox.get_or_create_wrapper(content_type).nautobot.count
            if imported_count != expected_count:
                print(f"Import count mismatch for {content_type}")
            self.assertEqual(imported_count, expected_count, f"Import count mismatch for {content_type}")
            current_count = model.objects.count()
            self.assertGreaterEqual(current_count, expected_count, f"Count mismatch for {content_type}")
