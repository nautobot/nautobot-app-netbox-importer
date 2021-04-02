"""Test the primary key (PK) handling of this plugin."""
from unittest import TestCase
import uuid

from nautobot_netbox_importer.diffsync.models.validation import netbox_pk_to_nautobot_pk


class TestPrimaryKeyConversion(TestCase):
    """Test cases for the netbox_pk_to_nautobot_pk() function."""

    def test_uuids_are_deterministic(self):
        """PK generation must be deterministic and repeatable."""
        pk_1 = netbox_pk_to_nautobot_pk("test", 1)
        self.assertIsInstance(pk_1, uuid.UUID)
        pk_2 = netbox_pk_to_nautobot_pk("test", 1)
        self.assertIsInstance(pk_2, uuid.UUID)
        self.assertEqual(pk_1, pk_2)

    def test_uuids_for_different_pks_are_different(self):
        """Different PKs must generate different UUIDs."""
        pk_1 = netbox_pk_to_nautobot_pk("test", 1)
        self.assertIsInstance(pk_1, uuid.UUID)
        pk_2 = netbox_pk_to_nautobot_pk("test", 2)
        self.assertIsInstance(pk_2, uuid.UUID)
        self.assertNotEqual(pk_1, pk_2)

        pk_3 = netbox_pk_to_nautobot_pk("test", 1)
        self.assertIsInstance(pk_3, uuid.UUID)
        self.assertEqual(pk_1, pk_3)

    def test_uuids_for_different_models_are_different(self):
        """Different models must generate different UUIDs even for the same PK."""
        pk_1 = netbox_pk_to_nautobot_pk("model1", 1)
        self.assertIsInstance(pk_1, uuid.UUID)
        pk_2 = netbox_pk_to_nautobot_pk("model2", 1)
        self.assertIsInstance(pk_2, uuid.UUID)
        self.assertNotEqual(pk_1, pk_2)
