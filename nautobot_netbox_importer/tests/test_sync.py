"""Test cases for NetBox adapter."""
from tempfile import NamedTemporaryFile

import requests
from django.test import TestCase
from nautobot.core.utils.lookup import get_model_from_name

from nautobot_netbox_importer.command_utils import enable_logging
from nautobot_netbox_importer.diffsync.netbox import sync_to_nautobot

# How to parametrize this using _EXPECTED_COUNTS.keys()?

_EXPECTED_COUNTS = {
    "3.0": {
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
    },
    "3.1": {
        "auth.group": 1,
        "circuits.circuit": 29,
        "circuits.circuittermination": 45,
        "circuits.circuittype": 4,
        "circuits.provider": 9,
        "circuits.providernetwork": 1,
        "dcim.cable": 108,
        "dcim.consoleport": 41,
        "dcim.consoleporttemplate": 11,
        "dcim.device": 72,
        "dcim.devicebay": 14,
        "dcim.devicebaytemplate": 14,
        "dcim.devicetype": 14,
        "dcim.frontport": 912,
        "dcim.frontporttemplate": 120,
        "dcim.interface": 1554,
        "dcim.interfacetemplate": 268,
        "dcim.location": 95,
        "dcim.locationtype": 3,
        "dcim.manufacturer": 15,
        "dcim.platform": 3,
        "dcim.powerfeed": 48,
        "dcim.poweroutlet": 104,
        "dcim.poweroutlettemplate": 8,
        "dcim.powerpanel": 4,
        "dcim.powerport": 75,
        "dcim.powerporttemplate": 26,
        "dcim.rack": 42,
        "dcim.rackreservation": 2,
        "dcim.rearport": 630,
        "dcim.rearporttemplate": 73,
        "dcim.virtualchassis": 4,
        "extras.customfield": 1,
        "extras.role": 18,
        "extras.status": 6,
        "extras.tag": 26,
        "extras.taggeditem": 72,
        "ipam.ipaddress": 30,
        "ipam.prefix": 73,
        "ipam.rir": 8,
        "ipam.vlan": 63,
        "ipam.vlangroup": 7,
        "tenancy.tenant": 11,
        "tenancy.tenantgroup": 1,
        "users.user": 6,
        "virtualization.cluster": 32,
        "virtualization.clustergroup": 4,
        "virtualization.clustertype": 6,
        "virtualization.virtualmachine": 180,
        "virtualization.vminterface": 720,
    },
    "3.2": {
        "auth.group": 1,
        "circuits.circuit": 29,
        "circuits.circuittermination": 45,
        "circuits.circuittype": 4,
        "circuits.provider": 9,
        "circuits.providernetwork": 1,
        "dcim.cable": 108,
        "dcim.consoleport": 41,
        "dcim.consoleporttemplate": 11,
        "dcim.device": 72,
        "dcim.devicebay": 14,
        "dcim.devicebaytemplate": 14,
        "dcim.devicetype": 15,
        "dcim.frontport": 912,
        "dcim.frontporttemplate": 120,
        "dcim.interface": 1586,
        "dcim.interfacetemplate": 300,
        "dcim.location": 95,
        "dcim.locationtype": 3,
        "dcim.manufacturer": 15,
        "dcim.platform": 3,
        "dcim.powerfeed": 48,
        "dcim.poweroutlet": 104,
        "dcim.poweroutlettemplate": 8,
        "dcim.powerpanel": 4,
        "dcim.powerport": 75,
        "dcim.powerporttemplate": 26,
        "dcim.rack": 42,
        "dcim.rackreservation": 2,
        "dcim.rearport": 630,
        "dcim.rearporttemplate": 73,
        "dcim.virtualchassis": 4,
        "extras.customfield": 1,
        "extras.role": 18,
        "extras.status": 6,
        "extras.tag": 26,
        "extras.taggeditem": 72,
        "ipam.ipaddress": 180,
        "ipam.prefix": 94,
        "ipam.rir": 8,
        "ipam.routetarget": 12,
        "ipam.vlan": 63,
        "ipam.vlangroup": 7,
        "ipam.vrf": 6,
        "tenancy.tenant": 11,
        "tenancy.tenantgroup": 1,
        "users.user": 6,
        "virtualization.cluster": 32,
        "virtualization.clustergroup": 4,
        "virtualization.clustertype": 6,
        "virtualization.virtualmachine": 180,
        "virtualization.vminterface": 720,
    },
}


class TestSync(TestCase):
    """Unittest for NetBox adapter."""

    def test_sync_3_0(self):
        self._sync("3.0")

    def test_sync_3_1(self):
        self._sync("3.1")

    def test_sync_3_2(self):
        self._sync("3.2")

    def _sync(self, version: str):
        """Test sync."""
        enable_logging()

        url = f"https://raw.githubusercontent.com/netbox-community/netbox-demo-data/master/netbox-demo-v{version}.json"
        response = requests.get(url)
        response.raise_for_status()

        with NamedTemporaryFile(mode="w+", delete=False) as tmp_file:
            tmp_file.write(response.text)
            tmp_filename = tmp_file.name

        netbox = sync_to_nautobot(tmp_filename, dry_run=False)

        for content_type, expected_count in _EXPECTED_COUNTS[version].items():
            model = get_model_from_name(content_type)
            imported_count = netbox.get_wrapper(content_type).nautobot.count
            self.assertEqual(imported_count, expected_count, f"Import count mismatch for {content_type}")
            current_count = model.objects.count()
            self.assertGreaterEqual(current_count, expected_count, f"Count mismatch for {content_type}")
