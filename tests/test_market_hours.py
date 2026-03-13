"""Tests for MarketHoursManager -- time-based trading permission control."""

import datetime

import pytest

from kiwoom_trader.config.constants import MarketState
from kiwoom_trader.core.models import RiskConfig
from kiwoom_trader.core.market_hours import MarketHoursManager


def make_time(hour: int, minute: int) -> datetime.time:
    """Helper to create time for injection."""
    return datetime.time(hour, minute)


@pytest.fixture
def manager(mock_risk_config):
    """MarketHoursManager with default RiskConfig and injectable time."""

    def _manager(hour: int, minute: int):
        return MarketHoursManager(
            mock_risk_config, time_func=lambda: make_time(hour, minute)
        )

    return _manager


class TestGetMarketState:
    def test_pre_market_auction_0845(self, manager):
        m = manager(8, 45)
        assert m.get_market_state() == MarketState.PRE_MARKET_AUCTION

    def test_market_open_buffer_0902(self, manager):
        m = manager(9, 2)
        assert m.get_market_state() == MarketState.MARKET_OPEN_BUFFER

    def test_trading_0905(self, manager):
        m = manager(9, 5)
        assert m.get_market_state() == MarketState.TRADING

    def test_trading_1030(self, manager):
        m = manager(10, 30)
        assert m.get_market_state() == MarketState.TRADING

    def test_closing_1515(self, manager):
        m = manager(15, 15)
        assert m.get_market_state() == MarketState.CLOSING

    def test_closing_auction_1522(self, manager):
        m = manager(15, 22)
        assert m.get_market_state() == MarketState.CLOSING_AUCTION

    def test_closed_1535(self, manager):
        m = manager(15, 35)
        assert m.get_market_state() == MarketState.CLOSED

    def test_closed_before_market_0700(self, manager):
        m = manager(7, 0)
        assert m.get_market_state() == MarketState.CLOSED

    def test_boundary_auction_start_0830(self, manager):
        m = manager(8, 30)
        assert m.get_market_state() == MarketState.PRE_MARKET_AUCTION

    def test_boundary_auction_end_0900(self, manager):
        m = manager(9, 0)
        assert m.get_market_state() == MarketState.MARKET_OPEN_BUFFER

    def test_boundary_closing_auction_start_1520(self, manager):
        m = manager(15, 20)
        assert m.get_market_state() == MarketState.CLOSING_AUCTION

    def test_boundary_closing_auction_end_1530(self, manager):
        m = manager(15, 30)
        assert m.get_market_state() == MarketState.CLOSED


class TestTradingAllowed:
    def test_trading_allowed_during_trading(self, manager):
        m = manager(10, 0)
        assert m.is_trading_allowed() is True

    def test_trading_not_allowed_during_auction(self, manager):
        m = manager(8, 45)
        assert m.is_trading_allowed() is False

    def test_trading_not_allowed_during_closing(self, manager):
        m = manager(15, 17)
        assert m.is_trading_allowed() is False


class TestNewBuyAllowed:
    def test_new_buy_allowed_during_trading(self, manager):
        m = manager(10, 0)
        assert m.is_new_buy_allowed() is True

    def test_new_buy_blocked_during_closing(self, manager):
        m = manager(15, 17)
        assert m.is_new_buy_allowed() is False


class TestOrderBlocked:
    def test_blocked_pre_market_auction(self, manager):
        m = manager(8, 45)
        assert m.is_order_blocked() is True

    def test_blocked_closing_auction(self, manager):
        m = manager(15, 25)
        assert m.is_order_blocked() is True

    def test_blocked_market_open_buffer(self, manager):
        m = manager(9, 2)
        assert m.is_order_blocked() is True

    def test_blocked_closed(self, manager):
        m = manager(16, 0)
        assert m.is_order_blocked() is True

    def test_not_blocked_during_trading(self, manager):
        m = manager(10, 0)
        assert m.is_order_blocked() is False

    def test_not_blocked_during_closing(self, manager):
        # CLOSING allows sell/liquidation orders
        m = manager(15, 17)
        assert m.is_order_blocked() is False


class TestClosingTime:
    def test_is_closing_time_true(self, manager):
        m = manager(15, 17)
        assert m.is_closing_time() is True

    def test_is_closing_time_false_during_trading(self, manager):
        m = manager(10, 0)
        assert m.is_closing_time() is False


class TestCustomConfig:
    def test_custom_trading_start(self):
        config = RiskConfig(trading_start="09:10")
        m = MarketHoursManager(config, time_func=lambda: make_time(9, 7))
        # 09:07 should be MARKET_OPEN_BUFFER with custom start at 09:10
        assert m.get_market_state() == MarketState.MARKET_OPEN_BUFFER


class TestTimeInjection:
    def test_uses_injected_time_function(self, mock_risk_config):
        called = []

        def time_func():
            called.append(True)
            return make_time(10, 0)

        m = MarketHoursManager(mock_risk_config, time_func=time_func)
        m.get_market_state()
        assert len(called) == 1


class TestStateTransition:
    """Tests for state transition detection and callback system."""

    def test_check_state_transition_returns_tuple_on_change(self, mock_risk_config):
        """check_state_transition() returns (old_state, new_state) when state changes."""
        current_time = [make_time(9, 2)]  # MARKET_OPEN_BUFFER

        def time_func():
            return current_time[0]

        m = MarketHoursManager(mock_risk_config, time_func=time_func)
        # First call initializes _previous_state
        m.check_state_transition()

        # Change time to TRADING
        current_time[0] = make_time(9, 10)
        result = m.check_state_transition()

        assert result is not None
        assert result == (MarketState.MARKET_OPEN_BUFFER, MarketState.TRADING)

    def test_check_state_transition_returns_none_when_no_change(self, mock_risk_config):
        """check_state_transition() returns None when state has NOT changed."""
        m = MarketHoursManager(mock_risk_config, time_func=lambda: make_time(10, 0))
        # First call initializes
        m.check_state_transition()
        # Second call with same state
        result = m.check_state_transition()
        assert result is None

    def test_on_state_changed_callback_fires(self, mock_risk_config):
        """on_state_changed callback fires with (old_state, new_state) on transition."""
        current_time = [make_time(9, 2)]  # MARKET_OPEN_BUFFER
        callback_args = []

        def time_func():
            return current_time[0]

        def on_changed(old_state, new_state):
            callback_args.append((old_state, new_state))

        m = MarketHoursManager(mock_risk_config, time_func=time_func)
        m.register_state_callback(on_changed)

        # Initialize
        m.check_state_transition()

        # Transition to TRADING
        current_time[0] = make_time(9, 10)
        m.check_state_transition()

        assert len(callback_args) == 1
        assert callback_args[0] == (MarketState.MARKET_OPEN_BUFFER, MarketState.TRADING)

    def test_buffer_to_trading_transition_detected(self, mock_risk_config):
        """Transition from MARKET_OPEN_BUFFER to TRADING is detected (the critical reset trigger)."""
        current_time = [make_time(9, 2)]  # MARKET_OPEN_BUFFER

        def time_func():
            return current_time[0]

        m = MarketHoursManager(mock_risk_config, time_func=time_func)
        m.check_state_transition()  # init

        current_time[0] = make_time(9, 5)  # Exactly at trading_start boundary
        result = m.check_state_transition()

        assert result is not None
        old_state, new_state = result
        assert old_state == MarketState.MARKET_OPEN_BUFFER
        assert new_state == MarketState.TRADING

    def test_multiple_callbacks_all_fire(self, mock_risk_config):
        """Multiple callbacks can be registered and all fire on transition."""
        current_time = [make_time(9, 2)]
        results_a = []
        results_b = []

        def time_func():
            return current_time[0]

        m = MarketHoursManager(mock_risk_config, time_func=time_func)
        m.register_state_callback(lambda o, n: results_a.append((o, n)))
        m.register_state_callback(lambda o, n: results_b.append((o, n)))

        m.check_state_transition()  # init
        current_time[0] = make_time(9, 10)  # TRADING
        m.check_state_transition()

        assert len(results_a) == 1
        assert len(results_b) == 1
        assert results_a[0] == results_b[0]

    def test_first_call_returns_none_initializes_state(self, mock_risk_config):
        """First call to check_state_transition sets _previous_state and returns None."""
        m = MarketHoursManager(mock_risk_config, time_func=lambda: make_time(10, 0))
        result = m.check_state_transition()
        assert result is None
