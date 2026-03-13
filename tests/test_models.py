"""Tests for core data models and extended constants."""

import pytest
from enum import Enum


class TestOrderState:
    """Tests for OrderState enum."""

    def test_order_state_has_8_states(self):
        from kiwoom_trader.core.models import OrderState

        states = list(OrderState)
        assert len(states) == 8

    def test_order_state_members(self):
        from kiwoom_trader.core.models import OrderState

        assert OrderState.CREATED
        assert OrderState.SUBMITTED
        assert OrderState.ACCEPTED
        assert OrderState.PARTIAL_FILL
        assert OrderState.FILLED
        assert OrderState.CANCELLED
        assert OrderState.REJECTED
        assert OrderState.MODIFY_PENDING

    def test_order_state_is_enum(self):
        from kiwoom_trader.core.models import OrderState

        assert issubclass(OrderState, Enum)


class TestValidTransitions:
    """Tests for VALID_TRANSITIONS mapping."""

    def test_created_transitions(self):
        from kiwoom_trader.core.models import OrderState, VALID_TRANSITIONS

        assert VALID_TRANSITIONS[OrderState.CREATED] == {
            OrderState.SUBMITTED,
            OrderState.REJECTED,
        }

    def test_submitted_transitions(self):
        from kiwoom_trader.core.models import OrderState, VALID_TRANSITIONS

        assert VALID_TRANSITIONS[OrderState.SUBMITTED] == {
            OrderState.ACCEPTED,
            OrderState.REJECTED,
        }

    def test_accepted_transitions(self):
        from kiwoom_trader.core.models import OrderState, VALID_TRANSITIONS

        assert VALID_TRANSITIONS[OrderState.ACCEPTED] == {
            OrderState.PARTIAL_FILL,
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.MODIFY_PENDING,
        }

    def test_partial_fill_transitions(self):
        from kiwoom_trader.core.models import OrderState, VALID_TRANSITIONS

        assert VALID_TRANSITIONS[OrderState.PARTIAL_FILL] == {
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.MODIFY_PENDING,
            OrderState.PARTIAL_FILL,
        }

    def test_modify_pending_transitions(self):
        from kiwoom_trader.core.models import OrderState, VALID_TRANSITIONS

        assert VALID_TRANSITIONS[OrderState.MODIFY_PENDING] == {
            OrderState.ACCEPTED,
            OrderState.REJECTED,
        }

    def test_terminal_states_have_empty_transitions(self):
        from kiwoom_trader.core.models import OrderState, VALID_TRANSITIONS

        assert VALID_TRANSITIONS.get(OrderState.FILLED, set()) == set()
        assert VALID_TRANSITIONS.get(OrderState.CANCELLED, set()) == set()
        assert VALID_TRANSITIONS.get(OrderState.REJECTED, set()) == set()


class TestOrderSide:
    """Tests for OrderSide enum."""

    def test_order_side_buy_sell(self):
        from kiwoom_trader.core.models import OrderSide

        assert OrderSide.BUY
        assert OrderSide.SELL
        assert issubclass(OrderSide, Enum)


class TestOrderDataclass:
    """Tests for Order dataclass."""

    def test_order_required_fields(self):
        from kiwoom_trader.core.models import Order, OrderSide, OrderState

        order = Order(
            code="005930",
            side=OrderSide.BUY,
            qty=10,
            price=70000,
            order_type=1,
            hoga_gb="00",
        )
        assert order.code == "005930"
        assert order.side == OrderSide.BUY
        assert order.qty == 10
        assert order.price == 70000
        assert order.order_type == 1
        assert order.hoga_gb == "00"

    def test_order_defaults(self):
        from kiwoom_trader.core.models import Order, OrderSide, OrderState

        order = Order(
            code="005930",
            side=OrderSide.BUY,
            qty=10,
            price=70000,
            order_type=1,
            hoga_gb="00",
        )
        assert order.state == OrderState.CREATED
        assert order.order_no == ""
        assert order.org_order_no == ""
        assert order.filled_qty == 0
        assert order.filled_price == 0
        assert order.screen_no == ""
        assert order.rq_name == ""
        assert order.created_at is not None


class TestPositionDataclass:
    """Tests for Position dataclass."""

    def test_position_init(self):
        from kiwoom_trader.core.models import Position

        pos = Position(code="005930", qty=10, avg_price=70000)
        assert pos.code == "005930"
        assert pos.qty == 10
        assert pos.avg_price == 70000

    def test_position_defaults(self):
        from kiwoom_trader.core.models import Position

        pos = Position(code="005930", qty=10, avg_price=70000)
        assert pos.high_water_mark == 0
        assert pos.stop_loss_price == 0
        assert pos.take_profit_price == 0
        assert pos.trailing_stop_price == 0
        assert pos.unrealized_pnl == 0


class TestRiskConfigDataclass:
    """Tests for RiskConfig dataclass with user-locked defaults."""

    def test_risk_config_defaults(self):
        from kiwoom_trader.core.models import RiskConfig

        rc = RiskConfig()
        assert rc.stop_loss_pct == -2.0
        assert rc.take_profit_pct == 3.0
        assert rc.trailing_stop_pct == 1.5
        assert rc.max_symbol_weight_pct == 20.0
        assert rc.max_positions == 5
        assert rc.daily_loss_limit_pct == 3.0
        assert rc.split_count == 3
        assert rc.split_interval_sec == 45
        assert rc.trading_start == "09:05"
        assert rc.trading_end_new_buy == "15:15"
        assert rc.auction_start_am == "08:30"
        assert rc.auction_end_am == "09:00"
        assert rc.auction_start_pm == "15:20"
        assert rc.auction_end_pm == "15:30"


class TestChejanFID:
    """Tests for CHEJAN_FID constants."""

    def test_chejan_fid_order_fields(self):
        from kiwoom_trader.config.constants import CHEJAN_FID

        assert CHEJAN_FID.ORDER_NO == 9203
        assert CHEJAN_FID.CODE == 9001
        assert CHEJAN_FID.ORDER_STATUS == 913
        assert CHEJAN_FID.ORDER_QTY == 900
        assert CHEJAN_FID.ORDER_PRICE == 901
        assert CHEJAN_FID.UNFILLED_QTY == 902
        assert CHEJAN_FID.EXEC_PRICE == 910
        assert CHEJAN_FID.EXEC_QTY == 911
        assert CHEJAN_FID.SELL_BUY == 907
        assert CHEJAN_FID.ORDER_EXEC_TIME == 908
        assert CHEJAN_FID.EXEC_NO == 909

    def test_chejan_fid_balance_fields(self):
        from kiwoom_trader.config.constants import CHEJAN_FID

        assert CHEJAN_FID.HOLDING_QTY == 930
        assert CHEJAN_FID.BUY_UNIT_PRICE == 931
        assert CHEJAN_FID.PNL_RATE == 8019
        assert CHEJAN_FID.CURRENT_PRICE == 10
        assert CHEJAN_FID.BEST_ASK == 27
        assert CHEJAN_FID.BEST_BID == 28

    def test_chejan_fid_has_at_least_25_constants(self):
        from kiwoom_trader.config.constants import CHEJAN_FID

        # Count class attributes that are not dunder
        attrs = [
            a for a in dir(CHEJAN_FID)
            if not a.startswith("_")
        ]
        assert len(attrs) >= 25


class TestOrderType:
    """Tests for OrderType constants."""

    def test_order_type_values(self):
        from kiwoom_trader.config.constants import OrderType

        assert OrderType.NEW_BUY == 1
        assert OrderType.NEW_SELL == 2
        assert OrderType.CANCEL_BUY == 3
        assert OrderType.CANCEL_SELL == 4
        assert OrderType.MODIFY_BUY == 5
        assert OrderType.MODIFY_SELL == 6


class TestHogaGb:
    """Tests for HogaGb constants."""

    def test_hoga_gb_basic(self):
        from kiwoom_trader.config.constants import HogaGb

        assert HogaGb.LIMIT == "00"
        assert HogaGb.MARKET == "03"


class TestOrderError:
    """Tests for ORDER_ERROR constants."""

    def test_order_error_values(self):
        from kiwoom_trader.config.constants import ORDER_ERROR

        assert ORDER_ERROR.SUCCESS == 0
        assert ORDER_ERROR.FAIL == -10
        assert ORDER_ERROR.SEND_FAIL == -307


class TestMarketState:
    """Tests for MarketState enum."""

    def test_market_state_has_6_states(self):
        from kiwoom_trader.config.constants import MarketState

        states = list(MarketState)
        assert len(states) == 6

    def test_market_state_members(self):
        from kiwoom_trader.config.constants import MarketState

        assert MarketState.PRE_MARKET_AUCTION
        assert MarketState.MARKET_OPEN_BUFFER
        assert MarketState.TRADING
        assert MarketState.CLOSING
        assert MarketState.CLOSING_AUCTION
        assert MarketState.CLOSED

    def test_market_state_is_enum(self):
        from kiwoom_trader.config.constants import MarketState

        assert issubclass(MarketState, Enum)


class TestMarketOperation:
    """Tests for MarketOperation FID 215 values."""

    def test_market_operation_values(self):
        from kiwoom_trader.config.constants import MarketOperation

        assert MarketOperation.PRE_MARKET == "0"
        assert MarketOperation.MARKET_OPEN == "3"
        assert MarketOperation.CLOSE_APPROACHING == "2"
        assert MarketOperation.MARKET_CLOSE_48 == "4"
        assert MarketOperation.MARKET_CLOSE_9 == "9"


class TestScreenOrderBase:
    """Tests for SCREEN.ORDER_BASE."""

    def test_screen_order_base(self):
        from kiwoom_trader.config.constants import SCREEN

        assert SCREEN.ORDER_BASE == 2000
