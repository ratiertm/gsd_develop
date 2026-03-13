"""Tests for Notifier notification dispatcher."""

import time
from unittest.mock import MagicMock, patch, call

import pytest


class TestNotifierRouting:
    """Test that Notifier routes to correct channels based on config."""

    def _make_notifier(self, **overrides):
        """Create a Notifier with configurable channel toggles."""
        from kiwoom_trader.gui.notification.notifier import Notifier

        config = {
            "gui_popup_enabled": False,
            "log_enabled": False,
            "discord_enabled": False,
            "discord_rate_limit_sec": 0,
        }
        config.update(overrides)
        return Notifier(config=config, main_window=overrides.get("main_window"))

    @patch("kiwoom_trader.gui.notification.notifier.logger")
    def test_notifier_routes_to_log(self, mock_logger):
        """notify() with log_enabled=True calls logger.bind(log_type='trade')."""
        mock_bound = MagicMock()
        mock_logger.bind.return_value = mock_bound

        notifier = self._make_notifier(log_enabled=True)
        notifier.notify("trade", "Buy Signal", "Samsung 005930")

        mock_logger.bind.assert_called_with(log_type="trade")
        mock_bound.info.assert_called_once()
        assert "TRADE" in mock_bound.info.call_args[0][0]

    def test_notifier_routes_to_gui(self):
        """notify() with gui_popup_enabled=True calls main_window.show_toast()."""
        mock_window = MagicMock()
        notifier = self._make_notifier(
            gui_popup_enabled=True, main_window=mock_window
        )
        notifier.notify("signal", "Entry Signal", "RSI below 30")

        mock_window.show_toast.assert_called_once_with(
            "Entry Signal", "RSI below 30", "signal"
        )

    @patch("kiwoom_trader.gui.notification.notifier.DiscordSendWorker")
    def test_notifier_routes_to_discord(self, mock_worker_cls):
        """notify() with discord_enabled=True calls _send_discord()."""
        mock_worker = MagicMock()
        mock_worker_cls.return_value = mock_worker

        notifier = self._make_notifier(discord_enabled=True)
        notifier.notify("trade", "Buy", "Samsung", data={"side": "BUY", "code": "005930", "price": 72000, "qty": 10, "strategy": "RSI", "pnl_pct": 0, "timestamp": "2026-01-01"})

        mock_worker.start.assert_called_once()

    @patch("kiwoom_trader.gui.notification.notifier.logger")
    def test_notifier_skips_disabled_channels(self, mock_logger):
        """Disabled channels are NOT called."""
        mock_window = MagicMock()
        notifier = self._make_notifier(
            gui_popup_enabled=False,
            log_enabled=False,
            discord_enabled=False,
            main_window=mock_window,
        )
        notifier.notify("trade", "Test", "Test message")

        mock_logger.bind.assert_not_called()
        mock_window.show_toast.assert_not_called()

    @patch("kiwoom_trader.gui.notification.notifier.logger")
    def test_notifier_handles_no_main_window(self, mock_logger):
        """main_window=None does not crash when gui_popup_enabled."""
        notifier = self._make_notifier(gui_popup_enabled=True)
        # Should not raise
        notifier.notify("trade", "Test", "No window")


class TestNotifierRateLimit:
    """Test Discord rate limiting."""

    @patch("kiwoom_trader.gui.notification.notifier.DiscordSendWorker")
    def test_discord_rate_limit(self, mock_worker_cls):
        """Notifier respects discord_rate_limit_sec (drops messages within interval)."""
        mock_worker = MagicMock()
        mock_worker_cls.return_value = mock_worker

        notifier = self._make_notifier(
            discord_enabled=True, discord_rate_limit_sec=10
        )

        # First send should go through
        notifier.notify("trade", "First", "msg1")
        assert mock_worker.start.call_count == 1

        # Second send within rate limit should be dropped
        notifier.notify("trade", "Second", "msg2")
        assert mock_worker.start.call_count == 1  # Still 1, second was dropped
