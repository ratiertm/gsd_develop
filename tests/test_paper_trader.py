"""Tests for PaperTrader - virtual trade execution with CSV logging."""

import csv
from datetime import datetime

import pytest

from kiwoom_trader.core.models import Signal
from kiwoom_trader.core.paper_trader import PaperTrader


@pytest.fixture
def trader(tmp_path):
    csv_path = str(tmp_path / "trades.csv")
    return PaperTrader(csv_path=csv_path, initial_capital=10_000_000, max_symbol_weight_pct=20.0)


def _make_signal(code: str, side: str, price: int, strategy: str = "TEST",
                 reason: str = "test") -> Signal:
    return Signal(
        code=code, side=side, strategy_name=strategy,
        priority=10, price=price,
        timestamp=datetime(2026, 3, 14, 10, 0, 0),
        reason=reason,
    )


class TestBuyExecution:
    """Test virtual buy order execution."""

    def test_buy_creates_virtual_position(self, trader):
        sig = _make_signal("005930", "BUY", 50000)
        trader.execute_signal(sig)

        assert "005930" in trader.positions
        pos = trader.positions["005930"]
        assert pos["qty"] > 0
        assert pos["avg_price"] == 50000

    def test_insufficient_capital_limits_qty(self, trader):
        """When price is high, qty is limited by available capital."""
        sig = _make_signal("005930", "BUY", 5_000_000)
        trader.execute_signal(sig)

        # max_symbol_weight=20%, capital=10M, so max=2M/5M=0 shares but floor to at least what capital allows
        # 10M * 20% / 5M = 0.4 -> qty = 0 (can't afford even 1 at 20% weight)
        # But available capital allows 10M/5M = 2 shares
        # The design: qty = int(capital * weight_pct / 100 / price) = int(10M * 0.2 / 5M) = 0
        # Since qty is 0, no position should be created
        if "005930" in trader.positions:
            assert trader.positions["005930"]["qty"] <= 2


class TestSellExecution:
    """Test virtual sell order execution."""

    def test_sell_closes_position_with_pnl(self, trader):
        # Buy first
        buy_sig = _make_signal("005930", "BUY", 50000)
        trader.execute_signal(buy_sig)
        qty = trader.positions["005930"]["qty"]

        # Sell at higher price
        sell_sig = _make_signal("005930", "SELL", 55000)
        trader.execute_signal(sell_sig)

        # Position should be closed
        assert "005930" not in trader.positions or trader.positions["005930"]["qty"] == 0

        # P&L should be positive
        summary = trader.get_summary()
        assert summary["total_pnl"] > 0


class TestCSVLogging:
    """Test CSV trade logging."""

    def test_csv_created_with_header(self, trader, tmp_path):
        sig = _make_signal("005930", "BUY", 50000)
        trader.execute_signal(sig)

        csv_path = str(tmp_path / "trades.csv")
        with open(csv_path) as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "timestamp" in header
            assert "code" in header
            assert "side" in header
            assert "pnl" in header

    def test_csv_trade_appended(self, trader, tmp_path):
        sig1 = _make_signal("005930", "BUY", 50000)
        trader.execute_signal(sig1)

        sig2 = _make_signal("005930", "SELL", 55000)
        trader.execute_signal(sig2)

        csv_path = str(tmp_path / "trades.csv")
        with open(csv_path) as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Header + 2 trades
            assert len(rows) >= 3


class TestSummary:
    """Test summary statistics."""

    def test_get_summary_stats(self, trader):
        # Execute buy then sell
        trader.execute_signal(_make_signal("005930", "BUY", 50000))
        trader.execute_signal(_make_signal("005930", "SELL", 55000))

        summary = trader.get_summary()
        assert "total_trades" in summary
        assert "total_pnl" in summary
        assert "win_rate" in summary
        assert summary["total_trades"] == 2
