"""Smoke tests for BacktestDialog rendering and BacktestWorker signals.

Skips gracefully if PyQt5 or pyqtgraph are unavailable (macOS CI compat).
"""

from __future__ import annotations

from datetime import datetime

import pytest

from kiwoom_trader.core.models import BacktestResult, Candle, TradeRecord

# Skip entire module if PyQt5/pyqtgraph unavailable
try:
    from PyQt5.QtWidgets import QApplication
    import pyqtgraph  # noqa: F401

    _HAS_PYQT5 = True
except ImportError:
    _HAS_PYQT5 = False

pytestmark = pytest.mark.skipif(not _HAS_PYQT5, reason="PyQt5/pyqtgraph not available")


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

def _make_dummy_result() -> BacktestResult:
    """Create a BacktestResult with realistic dummy data."""
    now = datetime(2026, 1, 1, 9, 0, 0)
    trades = [
        TradeRecord(
            timestamp=datetime(2026, 1, 2, 10, 0),
            code="005930",
            side="BUY",
            strategy="test_strat",
            price=70000,
            qty=10,
            amount=700000,
            pnl=0,
            pnl_pct=0.0,
            balance=9300000,
            reason="entry signal",
        ),
        TradeRecord(
            timestamp=datetime(2026, 1, 5, 14, 0),
            code="005930",
            side="SELL",
            strategy="test_strat",
            price=72000,
            qty=10,
            amount=720000,
            pnl=20000,
            pnl_pct=2.86,
            balance=10020000,
            reason="exit signal",
        ),
    ]

    equity_curve = [
        (datetime(2026, 1, 1, 9, 0), 10_000_000.0),
        (datetime(2026, 1, 2, 9, 0), 9_950_000.0),
        (datetime(2026, 1, 3, 9, 0), 10_050_000.0),
        (datetime(2026, 1, 4, 9, 0), 10_100_000.0),
        (datetime(2026, 1, 5, 9, 0), 10_020_000.0),
    ]

    return BacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        initial_capital=10_000_000,
        final_capital=10_020_000.0,
        total_return_pct=0.20,
        max_drawdown_pct=0.50,
        win_rate_pct=100.0,
        profit_factor=float("inf"),
        sharpe_ratio=1.25,
        total_trades=1,
        avg_pnl=20000.0,
        max_consecutive_losses=0,
        avg_holding_periods=3.0,
    )


def _make_dummy_candles() -> list[Candle]:
    """Create dummy candle data matching the backtest period."""
    candles = []
    base_prices = [70000, 69500, 71000, 72000, 71500]
    for i, price in enumerate(base_prices):
        candles.append(
            Candle(
                code="005930",
                open=price - 500,
                high=price + 500,
                low=price - 1000,
                close=price,
                volume=100000 + i * 10000,
                timestamp=datetime(2026, 1, 1 + i, 9, 0),
            )
        )
    return candles


# ------------------------------------------------------------------ #
# Tests
# ------------------------------------------------------------------ #

class TestBacktestDialog:
    """Smoke tests for BacktestDialog."""

    def test_dialog_instantiation(self, qapp):
        """BacktestDialog can be created without crashing."""
        from kiwoom_trader.gui.backtest_dialog import BacktestDialog

        result = _make_dummy_result()
        candles = _make_dummy_candles()
        dialog = BacktestDialog(result, candles)
        assert dialog is not None

    def test_summary_table_row_count(self, qapp):
        """Summary table has the expected number of rows (11 metrics)."""
        from kiwoom_trader.gui.backtest_dialog import BacktestDialog, SUMMARY_ROWS

        result = _make_dummy_result()
        candles = _make_dummy_candles()
        dialog = BacktestDialog(result, candles)
        assert dialog._summary_table.rowCount() == len(SUMMARY_ROWS)
        assert dialog._summary_table.rowCount() == 11

    def test_dialog_title(self, qapp):
        """Dialog window title is set correctly."""
        from kiwoom_trader.gui.backtest_dialog import BacktestDialog

        result = _make_dummy_result()
        candles = _make_dummy_candles()
        dialog = BacktestDialog(result, candles)
        assert dialog.windowTitle() == "Backtest Results"

    def test_dialog_with_empty_data(self, qapp):
        """Dialog handles empty equity curve and no trades without crashing."""
        from kiwoom_trader.gui.backtest_dialog import BacktestDialog

        result = BacktestResult(
            trades=[],
            equity_curve=[],
            initial_capital=10_000_000,
            final_capital=10_000_000.0,
        )
        dialog = BacktestDialog(result, [])
        assert dialog is not None

    def test_summary_table_values(self, qapp):
        """Summary table cells contain formatted metric values."""
        from kiwoom_trader.gui.backtest_dialog import BacktestDialog

        result = _make_dummy_result()
        candles = _make_dummy_candles()
        dialog = BacktestDialog(result, candles)

        # First row: Total Return
        metric_name = dialog._summary_table.item(0, 0).text()
        assert metric_name == "Total Return"

        metric_value = dialog._summary_table.item(0, 1).text()
        assert "%" in metric_value


class TestBacktestWorker:
    """Basic import and signal definition tests for BacktestWorker."""

    def test_worker_importable(self):
        """BacktestWorker can be imported."""
        from kiwoom_trader.backtest.backtest_worker import BacktestWorker

        assert BacktestWorker is not None

    def test_worker_has_signals(self):
        """BacktestWorker defines progress/finished/error signals."""
        from kiwoom_trader.backtest.backtest_worker import BacktestWorker, _HAS_PYQT5

        if _HAS_PYQT5:
            assert hasattr(BacktestWorker, "progress")
            assert hasattr(BacktestWorker, "finished")
            assert hasattr(BacktestWorker, "error")
