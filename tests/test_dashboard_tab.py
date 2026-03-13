"""Tests for DashboardTab widget data binding and update logic."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure PyQt5 mocking is available
sys.modules.setdefault("PyQt5", MagicMock())
sys.modules.setdefault("PyQt5.QtCore", MagicMock())
sys.modules.setdefault("PyQt5.QtWidgets", MagicMock())
sys.modules.setdefault("PyQt5.QtGui", MagicMock())

from kiwoom_trader.core.models import Order, OrderSide, OrderState, Position
from kiwoom_trader.gui.dashboard_tab import (
    DashboardTab,
    pnl_color,
)


@pytest.fixture
def dashboard():
    """Create a DashboardTab instance with mocked Qt widgets."""
    tab = DashboardTab()
    return tab


# --- Positions table ---


def test_positions_table_columns(dashboard):
    """Positions table has 8 columns."""
    expected = [
        "종목코드", "종목명", "수량", "매입가", "현재가",
        "평가손익", "수익률(%)", "비중(%)",
    ]
    assert dashboard.POSITION_COLUMNS == expected
    assert len(dashboard.POSITION_COLUMNS) == 8


def test_update_positions(dashboard):
    """update_positions populates internal position data correctly."""
    positions = {
        "005930": Position(code="005930", qty=10, avg_price=70000, unrealized_pnl=5000),
        "000660": Position(code="000660", qty=5, avg_price=120000, unrealized_pnl=-3000),
    }
    total_invested = 10 * 70000 + 5 * 120000  # 1,300,000

    rows = dashboard.build_position_rows(positions, total_invested)

    assert len(rows) == 2
    # Check first position row data
    row_005930 = [r for r in rows if r[0] == "005930"][0]
    assert row_005930[2] == 10  # qty
    assert row_005930[3] == 70000  # avg_price
    assert row_005930[5] == 5000  # unrealized_pnl


def test_pnl_coloring():
    """Positive P&L -> red (#EF5350), negative -> blue (#42A5F5), zero -> None."""
    assert pnl_color(5000) == "#EF5350"
    assert pnl_color(-3000) == "#42A5F5"
    assert pnl_color(0) is None


# --- Orders table ---


def test_update_orders(dashboard):
    """update_orders splits orders into pending and filled lists."""
    orders = [
        Order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000,
            order_type=1, hoga_gb="00", order_no="ORD_001",
            state=OrderState.ACCEPTED,
        ),
        Order(
            code="000660", side=OrderSide.SELL, qty=5, price=120000,
            order_type=2, hoga_gb="00", order_no="ORD_002",
            state=OrderState.FILLED, filled_qty=5, filled_price=121000,
        ),
        Order(
            code="035720", side=OrderSide.BUY, qty=3, price=50000,
            order_type=1, hoga_gb="00", order_no="ORD_003",
            state=OrderState.CANCELLED,
        ),
    ]

    pending, filled = dashboard.split_orders(orders)

    assert len(pending) == 1
    assert pending[0].order_no == "ORD_001"
    assert len(filled) == 1
    assert filled[0].order_no == "ORD_002"


# --- P&L summary ---


def test_update_pnl_summary(dashboard):
    """update_pnl stores summary data correctly."""
    dashboard.update_pnl(daily_pnl=15000.0, unrealized_pnl=8000, total_invested=1300000)

    assert dashboard._pnl_data["daily_pnl"] == 15000.0
    assert dashboard._pnl_data["unrealized_pnl"] == 8000
    assert dashboard._pnl_data["total_invested"] == 1300000


# --- System status ---


def test_update_system_status(dashboard):
    """update_status stores system status data correctly."""
    dashboard.update_status(
        connected=True, market_state="TRADING",
        strategy_count=3, mode="paper",
    )

    assert dashboard._status_data["connected"] is True
    assert dashboard._status_data["market_state"] == "TRADING"
    assert dashboard._status_data["strategy_count"] == 3
    assert dashboard._status_data["mode"] == "paper"


# --- Log panel ---


def test_append_log(dashboard):
    """append_log adds text to the log buffer."""
    dashboard.append_log("Order submitted: ORD_001")
    dashboard.append_log("Order filled: ORD_001")

    assert len(dashboard._log_lines) == 2
    assert "Order submitted: ORD_001" in dashboard._log_lines[0]
    assert "Order filled: ORD_001" in dashboard._log_lines[1]


def test_log_panel_max_lines(dashboard):
    """Log panel trims to 500 lines max."""
    for i in range(550):
        dashboard.append_log(f"Log line {i}")

    assert len(dashboard._log_lines) == 500
    # Oldest lines should be trimmed -- first remaining should be line 50
    assert "Log line 50" in dashboard._log_lines[0]
