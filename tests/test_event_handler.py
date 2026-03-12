"""Tests for EventHandlerRegistry - event routing for TR and real-time data."""

from unittest.mock import MagicMock, patch

from kiwoom_trader.api.event_handler import EventHandlerRegistry


class TestTRHandlers:
    """TR response handler registration and dispatch."""

    def test_register_and_handle_tr(self):
        """Register handler for rq_name, verify callback receives args."""
        registry = EventHandlerRegistry()
        callback = MagicMock()

        registry.register_tr_handler("rq_test", callback)
        registry.handle_tr_data("rq_test", "screen", "tr_code", "record", "0")

        callback.assert_called_once_with("screen", "tr_code", "record", "0")

    def test_unregistered_tr_logs_warning(self, caplog):
        """handle_tr_data for unknown rq_name logs warning, does not raise."""
        registry = EventHandlerRegistry()

        # Should not raise
        registry.handle_tr_data("unknown_rq", "screen", "tr_code", "record", "0")

    def test_tr_handler_replaced_on_reregister(self):
        """Registering a new handler for same rq_name replaces the old one."""
        registry = EventHandlerRegistry()
        old_callback = MagicMock()
        new_callback = MagicMock()

        registry.register_tr_handler("rq_test", old_callback)
        registry.register_tr_handler("rq_test", new_callback)
        registry.handle_tr_data("rq_test", "arg1")

        old_callback.assert_not_called()
        new_callback.assert_called_once_with("arg1")


class TestRealHandlers:
    """Real-time data handler registration and dispatch (observer pattern)."""

    def test_register_multiple_real_handlers(self):
        """Two handlers for same real_type both get called."""
        registry = EventHandlerRegistry()
        handler_a = MagicMock()
        handler_b = MagicMock()

        registry.register_real_handler("stock_exec", handler_a)
        registry.register_real_handler("stock_exec", handler_b)
        registry.handle_real_data("stock_exec", "005930", "raw_data")

        handler_a.assert_called_once_with("005930", "raw_data")
        handler_b.assert_called_once_with("005930", "raw_data")

    def test_real_handler_receives_code_and_data(self):
        """Verify correct (code, data) args passed to real handler."""
        registry = EventHandlerRegistry()
        handler = MagicMock()

        registry.register_real_handler("orderbook", handler)
        registry.handle_real_data("orderbook", "000660", "fid_data_string")

        handler.assert_called_once_with("000660", "fid_data_string")

    def test_no_real_handler_silent(self):
        """handle_real_data for unregistered real_type does not raise."""
        registry = EventHandlerRegistry()

        # Should not raise
        registry.handle_real_data("unregistered_type", "005930", "data")
