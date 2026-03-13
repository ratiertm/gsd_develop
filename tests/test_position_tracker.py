"""Tests for PositionTracker -- position management, P&L, and limit checks."""

import pytest

from kiwoom_trader.core.models import Position, RiskConfig
from kiwoom_trader.core.position_tracker import PositionTracker


@pytest.fixture
def tracker(mock_risk_config):
    """PositionTracker with default RiskConfig."""
    return PositionTracker(mock_risk_config)


class TestAddPosition:
    def test_add_position_creates_and_stores(self, tracker):
        pos = tracker.add_position("005930", 10, 70000)
        assert pos.code == "005930"
        assert pos.qty == 10
        assert pos.avg_price == 70000
        assert pos.high_water_mark == 70000

    def test_add_position_sets_stop_loss(self, tracker):
        pos = tracker.add_position("005930", 10, 100000)
        # stop_loss_pct = -2.0 => stop at 98000
        assert pos.stop_loss_price == 98000

    def test_add_position_sets_take_profit(self, tracker):
        pos = tracker.add_position("005930", 10, 100000)
        # take_profit_pct = 3.0 => take profit at 103000
        assert pos.take_profit_price == 103000

    def test_add_position_sets_trailing_stop(self, tracker):
        pos = tracker.add_position("005930", 10, 100000)
        # trailing_stop_pct = 1.5 => trailing stop at 98500
        assert pos.trailing_stop_price == 98500


class TestUpdatePosition:
    def test_update_existing_position(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.update_position("005930", 15, 72000)
        pos = tracker.get_position("005930")
        assert pos.qty == 15
        assert pos.avg_price == 72000

    def test_update_removes_when_qty_zero(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.update_position("005930", 0, 70000)
        assert tracker.get_position("005930") is None


class TestUpdateFromChejan:
    def test_update_from_chejan_adds_new(self, tracker):
        tracker.update_from_chejan("005930", 10, 70000, 72000)
        pos = tracker.get_position("005930")
        assert pos is not None
        assert pos.qty == 10
        assert pos.avg_price == 70000
        assert pos.unrealized_pnl == 20000  # (72000 - 70000) * 10

    def test_update_from_chejan_removes_when_zero(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.update_from_chejan("005930", 0, 70000, 70000)
        assert tracker.get_position("005930") is None

    def test_update_from_chejan_updates_existing(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.update_from_chejan("005930", 5, 70000, 75000)
        pos = tracker.get_position("005930")
        assert pos.qty == 5
        assert pos.unrealized_pnl == 25000  # (75000 - 70000) * 5


class TestGetPosition:
    def test_get_existing(self, tracker):
        tracker.add_position("005930", 10, 70000)
        assert tracker.get_position("005930") is not None

    def test_get_nonexistent_returns_none(self, tracker):
        assert tracker.get_position("999999") is None


class TestGetAllPositions:
    def test_returns_all(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.add_position("000660", 5, 120000)
        positions = tracker.get_all_positions()
        assert len(positions) == 2
        assert "005930" in positions
        assert "000660" in positions


class TestUpdatePrice:
    def test_update_price_recalculates_pnl(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.update_price("005930", 73000)
        pos = tracker.get_position("005930")
        assert pos.unrealized_pnl == 30000  # (73000 - 70000) * 10


class TestPnL:
    def test_get_unrealized_pnl_sums_all(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.update_price("005930", 73000)
        tracker.add_position("000660", 5, 120000)
        tracker.update_price("000660", 118000)
        # 30000 + (-10000) = 20000
        assert tracker.get_unrealized_pnl() == 20000

    def test_get_daily_pnl_includes_realized(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.update_price("005930", 73000)  # unrealized: 30000
        tracker.record_realized_pnl(50000)
        assert tracker.get_daily_pnl() == 80000  # 50000 + 30000

    def test_record_realized_pnl_accumulates(self, tracker):
        tracker.record_realized_pnl(10000)
        tracker.record_realized_pnl(20000)
        assert tracker.get_daily_pnl() == 30000  # no unrealized


class TestTotalInvested:
    def test_get_total_invested(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.add_position("000660", 5, 120000)
        # 700000 + 600000
        assert tracker.get_total_invested() == 1300000


class TestSymbolWeight:
    def test_within_limit(self, tracker):
        # max_symbol_weight_pct = 20.0
        # total_capital = 10_000_000, order_amount = 1_000_000 (10%)
        assert tracker.check_symbol_weight("005930", 1_000_000, 10_000_000) is True

    def test_exceeds_limit(self, tracker):
        # Existing position: 10 * 70000 = 700000
        tracker.add_position("005930", 10, 70000)
        # order_amount=1_500_000, total = 2_200_000, capital = 10_000_000
        # 2_200_000 / 10_000_000 = 22% > 20%
        assert tracker.check_symbol_weight("005930", 1_500_000, 10_000_000) is False

    def test_existing_position_plus_order_within(self, tracker):
        tracker.add_position("005930", 10, 70000)
        # existing = 700000, order = 1_000_000, total = 1_700_000 = 17% < 20%
        assert tracker.check_symbol_weight("005930", 1_000_000, 10_000_000) is True


class TestMaxPositions:
    def test_under_limit(self, tracker):
        # max_positions = 5, currently 0
        assert tracker.check_max_positions("005930") is True

    def test_at_limit_new_code(self, tracker):
        for i in range(5):
            tracker.add_position(f"00{i:04d}", 1, 10000)
        assert tracker.check_max_positions("999999") is False

    def test_existing_code_always_allowed(self, tracker):
        for i in range(5):
            tracker.add_position(f"00{i:04d}", 1, 10000)
        # Adding to existing position is always allowed
        assert tracker.check_max_positions("000000") is True


class TestResetDaily:
    def test_reset_clears_realized_pnl(self, tracker):
        tracker.record_realized_pnl(50000)
        tracker.reset_daily()
        assert tracker.get_daily_pnl() == 0  # assuming no unrealized


class TestPositionRemovalOnZeroQty:
    def test_position_removed_on_update_zero(self, tracker):
        tracker.add_position("005930", 10, 70000)
        tracker.update_position("005930", 0, 70000)
        assert "005930" not in tracker.get_all_positions()
