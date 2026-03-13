"""Tests for RiskManager: pre-trade validation, real-time triggers, split orders."""

from unittest.mock import MagicMock, call, patch

import pytest

from kiwoom_trader.config.constants import FID, HogaGb
from kiwoom_trader.core.models import OrderSide, Position, RiskConfig


@pytest.fixture
def risk_config():
    return RiskConfig(
        stop_loss_pct=-2.0,
        take_profit_pct=3.0,
        trailing_stop_pct=1.5,
        max_symbol_weight_pct=20.0,
        max_positions=5,
        daily_loss_limit_pct=3.0,
        split_count=3,
        split_interval_sec=45,
    )


@pytest.fixture
def order_manager():
    mock = MagicMock()
    mock.submit_order.return_value = MagicMock()
    return mock


@pytest.fixture
def position_tracker():
    mock = MagicMock()
    mock.get_daily_pnl.return_value = 0.0
    mock.check_symbol_weight.return_value = True
    mock.check_max_positions.return_value = True
    mock.get_all_positions.return_value = {}
    mock.get_position.return_value = None
    return mock


@pytest.fixture
def market_hours():
    mock = MagicMock()
    mock.is_order_blocked.return_value = False
    mock.is_new_buy_allowed.return_value = True
    return mock


@pytest.fixture
def risk_manager(order_manager, position_tracker, market_hours, risk_config):
    from kiwoom_trader.core.risk_manager import RiskManager

    return RiskManager(
        order_manager=order_manager,
        position_tracker=position_tracker,
        market_hours=market_hours,
        risk_config=risk_config,
        total_capital=10_000_000,
    )


# === Pre-trade validation tests ===


class TestValidateOrder:
    def test_rejects_when_orders_blocked(self, risk_manager, market_hours):
        market_hours.is_order_blocked.return_value = True
        ok, reason = risk_manager.validate_order("005930", OrderSide.BUY, 10, 50000)
        assert ok is False
        assert "blocked" in reason.lower()

    def test_rejects_buy_when_new_buy_not_allowed(self, risk_manager, market_hours):
        market_hours.is_new_buy_allowed.return_value = False
        ok, reason = risk_manager.validate_order("005930", OrderSide.BUY, 10, 50000)
        assert ok is False
        assert "buy" in reason.lower()

    def test_rejects_buy_when_daily_loss_limit_exceeded(
        self, risk_manager, position_tracker
    ):
        # daily_pnl = -400_000, total_capital = 10_000_000 -> -4% > -3% limit
        position_tracker.get_daily_pnl.return_value = -400_000
        ok, reason = risk_manager.validate_order("005930", OrderSide.BUY, 10, 50000)
        assert ok is False
        assert "loss" in reason.lower()

    def test_rejects_when_symbol_weight_exceeded(
        self, risk_manager, position_tracker
    ):
        position_tracker.check_symbol_weight.return_value = False
        ok, reason = risk_manager.validate_order("005930", OrderSide.BUY, 10, 50000)
        assert ok is False
        assert "weight" in reason.lower()

    def test_rejects_when_max_positions_exceeded(
        self, risk_manager, position_tracker
    ):
        position_tracker.check_max_positions.return_value = False
        ok, reason = risk_manager.validate_order("005930", OrderSide.BUY, 10, 50000)
        assert ok is False
        assert "position" in reason.lower()

    def test_passes_when_all_checks_ok(self, risk_manager):
        ok, reason = risk_manager.validate_order("005930", OrderSide.BUY, 10, 50000)
        assert ok is True
        assert reason == "OK"

    def test_rejects_buy_when_daily_buy_blocked(self, risk_manager):
        risk_manager._daily_buy_blocked = True
        ok, reason = risk_manager.validate_order("005930", OrderSide.BUY, 10, 50000)
        assert ok is False
        assert "blocked" in reason.lower() or "loss" in reason.lower()

    def test_sell_allowed_when_daily_buy_blocked(self, risk_manager):
        """Sells should still be allowed even when daily buy is blocked."""
        risk_manager._daily_buy_blocked = True
        ok, reason = risk_manager.validate_order("005930", OrderSide.SELL, 10, 50000)
        assert ok is True


# === Real-time price trigger tests ===


class TestOnPriceUpdate:
    def _make_position(self, avg_price=50000, qty=10):
        return Position(
            code="005930",
            qty=qty,
            avg_price=avg_price,
            high_water_mark=avg_price,
            stop_loss_price=int(avg_price * (1 + (-2.0) / 100)),  # 49000
            take_profit_price=int(avg_price * (1 + 3.0 / 100)),  # 51500
            trailing_stop_price=int(avg_price * (1 - 1.5 / 100)),  # 49250
        )

    def test_stop_loss_triggers_sell(
        self, risk_manager, position_tracker, order_manager
    ):
        pos = self._make_position()
        position_tracker.get_position.return_value = pos

        data = {FID.CURRENT_PRICE: "48900"}  # below stop_loss 49000
        risk_manager.on_price_update("005930", data)

        order_manager.submit_order.assert_called_once_with(
            "005930", OrderSide.SELL, pos.qty, 0, HogaGb.MARKET
        )

    def test_take_profit_triggers_sell(
        self, risk_manager, position_tracker, order_manager
    ):
        pos = self._make_position()
        position_tracker.get_position.return_value = pos

        data = {FID.CURRENT_PRICE: "51600"}  # above take_profit 51500
        risk_manager.on_price_update("005930", data)

        order_manager.submit_order.assert_called_once_with(
            "005930", OrderSide.SELL, pos.qty, 0, HogaGb.MARKET
        )

    def test_updates_high_water_mark_on_price_rise(
        self, risk_manager, position_tracker, order_manager
    ):
        pos = self._make_position()
        pos.high_water_mark = 50000
        position_tracker.get_position.return_value = pos

        data = {FID.CURRENT_PRICE: "50500"}  # above high_water_mark but below TP
        risk_manager.on_price_update("005930", data)

        assert pos.high_water_mark == 50500
        # Should NOT have triggered any sell
        order_manager.submit_order.assert_not_called()

    def test_recalculates_trailing_stop_after_hwm_update(
        self, risk_manager, position_tracker, order_manager
    ):
        pos = self._make_position()
        pos.high_water_mark = 50000
        position_tracker.get_position.return_value = pos

        data = {FID.CURRENT_PRICE: "51000"}  # new HWM, below TP (51500)
        risk_manager.on_price_update("005930", data)

        assert pos.high_water_mark == 51000
        # trailing_stop = 51000 * (1 - 1.5/100) = 50235
        assert pos.trailing_stop_price == int(51000 * (1 - 1.5 / 100))

    def test_trailing_stop_triggers_sell(
        self, risk_manager, position_tracker, order_manager
    ):
        pos = self._make_position()
        pos.high_water_mark = 52000
        pos.trailing_stop_price = int(52000 * (1 - 1.5 / 100))  # 51220
        position_tracker.get_position.return_value = pos

        data = {FID.CURRENT_PRICE: "51200"}  # below trailing_stop 51220
        risk_manager.on_price_update("005930", data)

        order_manager.submit_order.assert_called_once_with(
            "005930", OrderSide.SELL, pos.qty, 0, HogaGb.MARKET
        )

    def test_daily_loss_triggers_liquidate_all(
        self, risk_manager, position_tracker, order_manager
    ):
        pos = self._make_position()
        position_tracker.get_position.return_value = pos
        # daily P&L = -350_000 => -3.5% of 10M -> exceeds -3% limit
        position_tracker.get_daily_pnl.return_value = -350_000
        position_tracker.get_all_positions.return_value = {"005930": pos}

        data = {FID.CURRENT_PRICE: "50000"}
        risk_manager.on_price_update("005930", data)

        # Should have called liquidate_all -> sell all positions
        order_manager.submit_order.assert_called()
        assert risk_manager._daily_buy_blocked is True


# === Liquidate all tests ===


class TestLiquidateAll:
    def test_submits_sell_for_all_positions(
        self, risk_manager, position_tracker, order_manager
    ):
        pos1 = Position(
            code="005930", qty=10, avg_price=50000, unrealized_pnl=-50000
        )
        pos2 = Position(
            code="000660", qty=5, avg_price=80000, unrealized_pnl=-20000
        )
        position_tracker.get_all_positions.return_value = {
            "005930": pos1,
            "000660": pos2,
        }

        risk_manager.liquidate_all()

        assert order_manager.submit_order.call_count == 2
        assert risk_manager._daily_buy_blocked is True

    def test_liquidates_worst_positions_first(
        self, risk_manager, position_tracker, order_manager
    ):
        pos1 = Position(
            code="005930", qty=10, avg_price=50000, unrealized_pnl=-50000
        )
        pos2 = Position(
            code="000660", qty=5, avg_price=80000, unrealized_pnl=-20000
        )
        position_tracker.get_all_positions.return_value = {
            "005930": pos1,
            "000660": pos2,
        }

        risk_manager.liquidate_all()

        # Worst first: pos1 (-50000) before pos2 (-20000)
        calls = order_manager.submit_order.call_args_list
        assert calls[0] == call("005930", OrderSide.SELL, 10, 0, HogaGb.MARKET)
        assert calls[1] == call("000660", OrderSide.SELL, 5, 0, HogaGb.MARKET)


# === Daily buy block tests ===


class TestDailyBuyBlock:
    def test_daily_buy_blocked_prevents_new_buys(self, risk_manager):
        risk_manager._daily_buy_blocked = True
        ok, reason = risk_manager.validate_order("005930", OrderSide.BUY, 10, 50000)
        assert ok is False

    def test_reset_daily_clears_buy_block(self, risk_manager):
        risk_manager._daily_buy_blocked = True
        risk_manager.reset_daily()
        assert risk_manager._daily_buy_blocked is False


# === Split order tests ===


class TestSplitOrders:
    def test_split_buy_creates_first_order_immediately(
        self, risk_manager, order_manager
    ):
        risk_manager.split_buy("005930", 100, 50000, HogaGb.LIMIT)
        # First part (33) submitted immediately
        order_manager.submit_order.assert_called_once_with(
            "005930", OrderSide.BUY, 33, 50000, HogaGb.LIMIT
        )

    def test_split_buy_returns_correct_splits(self, risk_manager):
        splits = risk_manager.split_buy("005930", 100, 50000, HogaGb.LIMIT)
        assert splits == [33, 33, 34]

    def test_split_sell_divides_into_three_parts(self, risk_manager, order_manager):
        splits = risk_manager.split_sell("005930", 100, 50000, HogaGb.LIMIT)
        assert splits == [33, 33, 34]
        # First part submitted immediately
        order_manager.submit_order.assert_called_once_with(
            "005930", OrderSide.SELL, 33, 50000, HogaGb.LIMIT
        )

    def test_compute_splits_distribution(self, risk_manager):
        assert risk_manager._compute_splits(100, 3) == [33, 33, 34]
        assert risk_manager._compute_splits(10, 3) == [3, 3, 4]
        assert risk_manager._compute_splits(99, 3) == [33, 33, 33]


# === End-of-day liquidation tests ===


class TestClosingTime:
    def test_on_closing_time_sells_all_positions(
        self, risk_manager, position_tracker, order_manager
    ):
        pos = Position(code="005930", qty=10, avg_price=50000)
        position_tracker.get_all_positions.return_value = {"005930": pos}

        risk_manager.on_closing_time()

        order_manager.submit_order.assert_called_once_with(
            "005930", OrderSide.SELL, 10, 0, HogaGb.MARKET
        )


# === Reset daily tests ===


class TestResetDaily:
    def test_reset_daily_clears_flag(self, risk_manager):
        risk_manager._daily_buy_blocked = True
        risk_manager.reset_daily()
        assert risk_manager._daily_buy_blocked is False
