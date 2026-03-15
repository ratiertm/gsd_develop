"""Tests for chart widgets: CandlestickItem data logic, ChartTab data management.

Tests verify data conversion, sliding window, indicator toggles, trade markers,
watchlist selection, and candle buffer management -- all without requiring
a running PyQt5/pyqtgraph display.
"""

from __future__ import annotations

import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Ensure PyQt5/pyqtgraph imports fail so chart_tab falls back to object base class.
# This avoids MagicMock inheritance issues with staticmethod/class methods.
# We block imports, import the chart modules (which cache _HAS_PYQT5=False),
# then RESTORE sys.modules so later tests can use real PyQt5.
_BLOCK_MODULES = ["PyQt5", "PyQt5.QtWidgets", "PyQt5.QtCore", "PyQt5.QtGui", "pyqtgraph"]
_saved = {}
for _mod in _BLOCK_MODULES:
    _saved[_mod] = sys.modules.get(_mod)
    sys.modules[_mod] = None  # type: ignore[assignment]  # Forces ImportError

from kiwoom_trader.core.models import Candle
from kiwoom_trader.gui.chart_tab import ChartTab  # noqa: E402 — import under blocked PyQt5

# Restore sys.modules so other test files can import PyQt5 normally
for _mod in _BLOCK_MODULES:
    if _saved[_mod] is None:
        sys.modules.pop(_mod, None)
    else:
        sys.modules[_mod] = _saved[_mod]


def _make_candle(code: str = "005930", open_: int = 100, close: int = 110,
                 low: int = 90, high: int = 115, volume: int = 1000,
                 cum_pv: float = 0.0, cum_vol: int = 0) -> Candle:
    """Helper to create a Candle for testing."""
    return Candle(
        code=code,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=datetime.now(),
        cum_price_volume=cum_pv,
        cum_volume=cum_vol,
    )


class TestCandleDataConversion:
    """Test Candle dataclass -> (index, open, close, low, high) tuple conversion."""

    def test_candle_data_conversion(self):
        from kiwoom_trader.gui.chart_tab import ChartTab
        candle = _make_candle(open_=100, close=110, low=90, high=115)
        result = ChartTab.candle_to_tuple(0, candle)
        assert result == (0, 100, 110, 90, 115)

    def test_candle_data_conversion_down(self):
        from kiwoom_trader.gui.chart_tab import ChartTab
        candle = _make_candle(open_=110, close=95, low=90, high=115)
        result = ChartTab.candle_to_tuple(5, candle)
        assert result == (5, 110, 95, 90, 115)


class TestSlidingWindow:
    """Test that only the last 120 candles are retained."""

    def test_sliding_window(self):
        from kiwoom_trader.gui.chart_tab import ChartTab
        settings = MagicMock()
        settings._config = {"watchlist": ["005930"]}
        tab = ChartTab(settings)

        # Add 130 candles
        for i in range(130):
            candle = _make_candle(code="005930", close=100 + i)
            tab.on_new_candle("005930", candle)

        assert len(tab._candle_buffers["005930"]) == 120


class TestIndicatorToggleState:
    """Test that toggling indicators updates visible_indicators set."""

    def test_indicator_toggle_state(self):
        from kiwoom_trader.gui.chart_tab import ChartTab
        settings = MagicMock()
        settings._config = {"watchlist": ["005930"]}
        tab = ChartTab(settings)

        assert "rsi" not in tab._visible_indicators
        tab.toggle_indicator("rsi", True)
        assert "rsi" in tab._visible_indicators
        tab.toggle_indicator("rsi", False)
        assert "rsi" not in tab._visible_indicators


class TestTradeMarkerData:
    """Test that add_trade_marker stores (index, price, side) correctly."""

    def test_trade_marker_data(self):
        from kiwoom_trader.gui.chart_tab import ChartTab
        settings = MagicMock()
        settings._config = {"watchlist": ["005930"]}
        tab = ChartTab(settings)

        tab.add_trade_marker("005930", 10, 50000, "BUY")
        tab.add_trade_marker("005930", 15, 51000, "SELL")

        markers = tab._trade_markers["005930"]
        assert len(markers) == 2
        assert markers[0] == (10, 50000, "BUY")
        assert markers[1] == (15, 51000, "SELL")


class TestWatchlistSelection:
    """Test that selecting a stock code updates current_code."""

    def test_watchlist_selection(self):
        from kiwoom_trader.gui.chart_tab import ChartTab
        settings = MagicMock()
        settings._config = {"watchlist": ["005930", "035720"]}
        tab = ChartTab(settings)

        assert tab._current_code == "005930"  # First in watchlist
        tab.switch_chart("035720")
        assert tab._current_code == "035720"


class TestOnNewCandle:
    """Test on_new_candle buffer management."""

    def test_on_new_candle_appends(self):
        from kiwoom_trader.gui.chart_tab import ChartTab
        settings = MagicMock()
        settings._config = {"watchlist": ["005930"]}
        tab = ChartTab(settings)

        candle = _make_candle(code="005930")
        tab.on_new_candle("005930", candle)

        assert len(tab._candle_buffers["005930"]) == 1

    def test_on_new_candle_ignores_other_code(self):
        from kiwoom_trader.gui.chart_tab import ChartTab
        settings = MagicMock()
        settings._config = {"watchlist": ["005930", "035720"]}
        tab = ChartTab(settings)
        tab._current_code = "005930"

        # Send candle for a different code
        candle = _make_candle(code="035720")
        tab.on_new_candle("035720", candle)

        # Should be stored in buffer but current code unchanged
        assert len(tab._candle_buffers.get("035720", [])) == 1
        assert tab._current_code == "005930"
