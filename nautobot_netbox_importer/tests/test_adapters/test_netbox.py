"""Test cases for NetBox adapter."""
from unittest import TestCase, mock

from nautobot_netbox_importer.diffsync.adapters import netbox

# pylint: disable=protected-access


class TestNetBoxAdapterMockInit(TestCase):
    """Unittest for methods that do not need a real __init__."""

    def setUp(self):
        with mock.patch.object(netbox.NetBox210DiffSync, "__init__") as mock_adapter:
            mock_adapter.return_value = None
            self.mock_adapter = netbox.NetBox210DiffSync()

    @mock.patch.object(netbox.NetBox210DiffSync, "_unsupported_fields", new_callable=mock.PropertyMock)
    def test_unsupported_fields_uses_class_attribute(self, mock_unsupported_fields):
        mock_unsupported_fields.return_value = {}
        self.mock_adapter._unsupported_fields = "a"
        self.assertEqual(self.mock_adapter.unsupported_fields, {})
        mock_unsupported_fields.assert_called()

    @mock.patch.object(netbox, "NautobotBaseModel", autospec=True)
    @mock.patch("pydantic.Field", autospec=True)
    def test_get_ignored_fields(self, mock_field_class, mock_nautobot_model):
        netbox_data = {"a": 1}
        nautobot_instance = mock_nautobot_model()
        mock_field = mock_field_class()
        nautobot_instance.__fields_set__ = {"a"}
        nautobot_instance.__fields__ = {"a": mock_field}
        nautobot_instance.ignored_fields = set()
        actual = self.mock_adapter._get_ignored_fields(netbox_data, nautobot_instance)
        self.assertEqual(actual, set())

    @mock.patch.object(netbox, "NautobotBaseModel", autospec=True)
    @mock.patch("pydantic.Field", autospec=True)
    def test_get_ignored_fields_alias(self, mock_field_class, mock_nautobot_model):
        netbox_data = {"a": 1}
        nautobot_instance = mock_nautobot_model()
        mock_field = mock_field_class()
        mock_field.alias = "a"
        mock_field.name = "b"
        nautobot_instance.__fields_set__ = {"b"}
        nautobot_instance.__fields__ = {"b": mock_field}
        nautobot_instance.ignored_fields = set()
        actual = self.mock_adapter._get_ignored_fields(netbox_data, nautobot_instance)
        self.assertEqual(actual, set())

    @mock.patch.object(netbox, "NautobotBaseModel", autospec=True)
    @mock.patch("pydantic.Field", autospec=True)
    def test_get_ignored_fields_class_ignores_field(self, mock_field_class, mock_nautobot_model):
        netbox_data = {"a": 1, "b": 2}
        nautobot_instance = mock_nautobot_model()
        mock_field = mock_field_class()
        nautobot_instance.__fields_set__ = {"a"}
        nautobot_instance.__fields__ = {"a": mock_field}
        nautobot_instance.ignored_fields = {"b"}
        actual = self.mock_adapter._get_ignored_fields(netbox_data, nautobot_instance)
        self.assertEqual(actual, set())

    @mock.patch.object(netbox, "NautobotBaseModel", autospec=True)
    @mock.patch("pydantic.Field", autospec=True)
    def test_get_ignored_fields_returns_fields(self, mock_field_class, mock_nautobot_model):
        netbox_data = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
        nautobot_instance = mock_nautobot_model()
        mock_field_a = mock_field_class()
        mock_field_d = mock_field_class()
        mock_field_e = mock_field_class()
        nautobot_instance.__fields_set__ = {"a", "d", "e"}
        nautobot_instance.__fields__ = {"a": mock_field_a, "d": mock_field_d, "e": mock_field_e}
        nautobot_instance.ignored_fields = set()
        actual = self.mock_adapter._get_ignored_fields(netbox_data, nautobot_instance)
        self.assertEqual(actual, {"b", "c"})

    @mock.patch.object(netbox, "NautobotBaseModel", autospec=True)
    def test_log_ignored_fields_details(self, mock_nautobot_model):
        netbox_data = {"a": 1, "b": 2, "c": 3}
        nautobot_instance = mock_nautobot_model()
        nautobot_instance.pk = "abc123"
        model_name = "mockmodel"
        ignored_fields = {"a", "c"}
        with mock.patch.object(self.mock_adapter.logger, "debug") as mock_debug_logger:
            self.mock_adapter._log_ignored_fields_details(netbox_data, nautobot_instance, model_name, ignored_fields)
            debug_args = mock_debug_logger.mock_calls[0].kwargs
            comment = debug_args["comment"]
            pk = debug_args["pk"]
            self.assertIn("a=1", comment)
            self.assertIn("c=3", comment)
            self.assertNotIn("b=2", comment)
            self.assertIn(model_name, comment)
            self.assertEqual(pk, nautobot_instance.pk)

    def test_log_ignored_fields_info_first_time_log_warning(self):
        model_name = "mockmodel"
        ignored_fields = {"a", "b"}
        with mock.patch.object(self.mock_adapter.logger, "warning") as mock_warning_logger:
            self.mock_adapter.__class__._unsupported_fields = {}
            self.mock_adapter._log_ignored_fields_info(model_name, ignored_fields)
            mock_warning_logger.assert_called()
            warning_message = mock_warning_logger.mock_calls[0].args[0]
            # account for any order of ignored fields
            self.assertTrue("a, b" in warning_message or "b, a" in warning_message)
            self.assertEqual(self.mock_adapter.unsupported_fields, {model_name: ignored_fields})

    def test_log_ignored_fields_info_subsequent_time_log_warning(self):
        model_name = "mockmodel"
        existing_field = "cccccccccc"
        ignored_fields = {"a", "b", existing_field}
        with mock.patch.object(self.mock_adapter.logger, "warning") as mock_warning_logger:
            self.mock_adapter.__class__._unsupported_fields = {model_name: {existing_field}}
            self.mock_adapter._log_ignored_fields_info(model_name, ignored_fields)
            mock_warning_logger.assert_called()
            warning_message = mock_warning_logger.mock_calls[0].args[0]
            # account for any order of ignored fields
            self.assertTrue("a, b" in warning_message or "b, a" in warning_message)
            # ensure that existing field was skipped
            self.assertNotIn(existing_field, warning_message)
            self.assertEqual(self.mock_adapter.unsupported_fields, {model_name: ignored_fields})

    def test_log_ignored_fields_info_subsequent_time_no_log(self):
        model_name = "mockmodel"
        ignored_fields = {"a", "b"}
        with mock.patch.object(self.mock_adapter.logger, "warning") as mock_warning_logger:
            self.mock_adapter.__class__._unsupported_fields = {model_name: ignored_fields}
            self.mock_adapter._log_ignored_fields_info(model_name, ignored_fields)
            mock_warning_logger.assert_not_called()

    @mock.patch.object(netbox.NetBox210DiffSync, "_log_ignored_fields_info")
    @mock.patch.object(netbox.NetBox210DiffSync, "_log_ignored_fields_details")
    @mock.patch.object(netbox.NetBox210DiffSync, "_get_ignored_fields", return_value={"a"})
    @mock.patch.object(netbox, "NautobotBaseModel", autospec=True)
    def test_log_ignored_fields_log_messages(
        self,
        mock_nautobot_model,
        mock_ignored_fields,  # pylint: disable=unused-argument
        mock_log_details,
        mock_log_info,
    ):
        netbox_data = {"a": 1}
        nautobot_instance = mock_nautobot_model()
        self.mock_adapter._log_ignored_fields(netbox_data, nautobot_instance)
        mock_log_details.assert_called_with(
            netbox_data, nautobot_instance, nautobot_instance._modelname, mock_ignored_fields.return_value
        )
        mock_log_info.assert_called_with(nautobot_instance._modelname, mock_ignored_fields.return_value)

    @mock.patch.object(netbox.NetBox210DiffSync, "_log_ignored_fields_info")
    @mock.patch.object(netbox.NetBox210DiffSync, "_log_ignored_fields_details")
    @mock.patch.object(netbox.NetBox210DiffSync, "_get_ignored_fields", return_value={})
    @mock.patch.object(netbox, "NautobotBaseModel", autospec=True)
    def test_log_ignored_fields_no_log(
        self,
        mock_nautobot_model,
        mock_ignored_fields,  # pylint: disable=unused-argument
        mock_log_details,
        mock_log_info,
    ):
        netbox_data = {"a": 1}
        nautobot_instance = mock_nautobot_model()
        self.mock_adapter._log_ignored_fields(netbox_data, nautobot_instance)
        mock_log_details.assert_not_called()
        mock_log_info.assert_not_called()
