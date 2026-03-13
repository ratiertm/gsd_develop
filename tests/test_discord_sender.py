"""Tests for Discord webhook sender and embed builder."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestBuildTradeEmbed:
    """Test Discord embed payload construction."""

    def test_discord_embed_buy_green(self):
        """build_trade_embed with side='BUY' returns color=0x26A69A."""
        from kiwoom_trader.gui.notification.discord_sender import build_trade_embed

        trade_data = {
            "code": "005930",
            "price": 72000,
            "qty": 10,
            "strategy": "RSI_REVERSAL",
            "pnl_pct": 1.5,
            "timestamp": "2026-03-14T10:00:00Z",
        }
        result = build_trade_embed(trade_data, side="BUY")
        embed = result["embeds"][0]
        assert embed["color"] == 0x26A69A

    def test_discord_embed_sell_red(self):
        """build_trade_embed with side='SELL' returns color=0xEF5350."""
        from kiwoom_trader.gui.notification.discord_sender import build_trade_embed

        trade_data = {
            "code": "035720",
            "price": 150000,
            "qty": 5,
            "strategy": "MA_CROSSOVER",
            "pnl_pct": -0.8,
            "timestamp": "2026-03-14T14:30:00Z",
        }
        result = build_trade_embed(trade_data, side="SELL")
        embed = result["embeds"][0]
        assert embed["color"] == 0xEF5350

    def test_discord_embed_fields(self):
        """Embed contains code, price, qty, strategy, pnl_pct fields."""
        from kiwoom_trader.gui.notification.discord_sender import build_trade_embed

        trade_data = {
            "code": "005930",
            "price": 72000,
            "qty": 10,
            "strategy": "RSI_REVERSAL",
            "pnl_pct": 1.5,
            "timestamp": "2026-03-14T10:00:00Z",
        }
        result = build_trade_embed(trade_data, side="BUY")
        embed = result["embeds"][0]
        field_names = [f["name"] for f in embed["fields"]]
        # Should contain all required fields (Korean names)
        assert len(embed["fields"]) >= 5
        # Check price is formatted with comma
        price_field = next(f for f in embed["fields"] if "72,000" in f["value"])
        assert price_field is not None


class TestDiscordSendWorker:
    """Test DiscordSendWorker error handling."""

    def test_discord_sender_handles_no_url(self):
        """DiscordSendWorker with empty URL does nothing (no crash)."""
        from kiwoom_trader.gui.notification.discord_sender import DiscordSendWorker

        worker = DiscordSendWorker(payload={"content": "test"}, webhook_url="")
        # run() should return without error
        worker.run()

    @patch("kiwoom_trader.gui.notification.discord_sender.urllib.request.urlopen")
    def test_discord_sender_handles_network_error(self, mock_urlopen):
        """urlopen failure logs error, does not raise."""
        from kiwoom_trader.gui.notification.discord_sender import DiscordSendWorker

        mock_urlopen.side_effect = Exception("Network error")
        worker = DiscordSendWorker(
            payload={"content": "test"},
            webhook_url="https://discord.com/api/webhooks/fake/url",
        )
        # Should not raise
        worker.run()
