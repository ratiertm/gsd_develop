"""Tests for OrderManager - order lifecycle state machine and ChejanData parsing."""

from unittest.mock import MagicMock, call

import pytest

from kiwoom_trader.core.models import Order, OrderSide, OrderState, VALID_TRANSITIONS
from kiwoom_trader.config.constants import (
    CHEJAN_FID,
    OrderType,
    HogaGb,
    SCREEN,
    ORDER_ERROR,
)
from kiwoom_trader.core.order_manager import OrderManager


@pytest.fixture
def order_manager(mock_kiwoom_api):
    """Create OrderManager with mock API and test account."""
    return OrderManager(mock_kiwoom_api, account_no="1234567890")


def _setup_chejan_data(mock_api, fid_map: dict):
    """Configure mock get_chejan_data to return specific FID values."""

    def side_effect(fid):
        return fid_map.get(fid, "")

    mock_api.get_chejan_data.side_effect = side_effect


class TestSubmitOrder:
    """submit_order creates Order, calls send_order, transitions state."""

    def test_submit_order_success_transitions_to_submitted(self, order_manager, mock_kiwoom_api):
        """On send_order returning 0, order transitions CREATED->SUBMITTED."""
        mock_kiwoom_api.send_order.return_value = 0

        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )

        assert order.state == OrderState.SUBMITTED
        assert order.code == "005930"
        assert order.side == OrderSide.BUY
        assert order.qty == 10
        assert order.price == 70000
        mock_kiwoom_api.send_order.assert_called_once()

    def test_submit_order_failure_transitions_to_rejected(self, order_manager, mock_kiwoom_api):
        """On send_order returning negative, order transitions CREATED->REJECTED."""
        mock_kiwoom_api.send_order.return_value = ORDER_ERROR.SEND_FAIL

        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )

        assert order.state == OrderState.REJECTED

    def test_submit_order_emits_order_submitted(self, order_manager, mock_kiwoom_api):
        """order_submitted signal emitted on successful submission."""
        mock_kiwoom_api.send_order.return_value = 0

        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )

        order_manager.order_submitted.emit.assert_called()

    def test_submit_order_rejected_emits_order_rejected(self, order_manager, mock_kiwoom_api):
        """order_rejected signal emitted on send failure."""
        mock_kiwoom_api.send_order.return_value = ORDER_ERROR.SEND_FAIL

        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )

        order_manager.order_rejected.emit.assert_called()


class TestChejanDataParsing:
    """handle_chejan_data parses FIDs and transitions order states."""

    def test_accepted_on_order_status_접수(self, order_manager, mock_kiwoom_api):
        """SUBMITTED -> ACCEPTED when order_status contains '접수'."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order_no = order.order_no

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "접수",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "10",
            CHEJAN_FID.EXEC_PRICE: "0",
            CHEJAN_FID.EXEC_QTY: "0",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        assert order.state == OrderState.ACCEPTED

    def test_partial_fill_when_unfilled_qty_gt_0(self, order_manager, mock_kiwoom_api):
        """ACCEPTED -> PARTIAL_FILL when unfilled_qty > 0 and exec_qty > 0."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order_no = order.order_no
        # First transition to ACCEPTED
        order._state_override = OrderState.ACCEPTED
        order.state = OrderState.ACCEPTED

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "체결",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "5",
            CHEJAN_FID.EXEC_PRICE: "-70000",
            CHEJAN_FID.EXEC_QTY: "5",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        assert order.state == OrderState.PARTIAL_FILL
        assert order.filled_qty == 5
        assert order.filled_price == 70000

    def test_filled_when_unfilled_qty_eq_0(self, order_manager, mock_kiwoom_api):
        """ACCEPTED -> FILLED when unfilled_qty == 0."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order_no = order.order_no
        order.state = OrderState.ACCEPTED

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "체결",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "0",
            CHEJAN_FID.EXEC_PRICE: "-70000",
            CHEJAN_FID.EXEC_QTY: "10",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        assert order.state == OrderState.FILLED

    def test_cancelled_on_cancel_confirmation(self, order_manager, mock_kiwoom_api):
        """ACCEPTED -> CANCELLED on cancel status."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order_no = order.order_no
        order.state = OrderState.ACCEPTED

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "취소",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "10",
            CHEJAN_FID.EXEC_PRICE: "0",
            CHEJAN_FID.EXEC_QTY: "0",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        assert order.state == OrderState.CANCELLED

    def test_rejected_on_reject_status(self, order_manager, mock_kiwoom_api):
        """SUBMITTED -> REJECTED on reject status."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order_no = order.order_no

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "거부",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "10",
            CHEJAN_FID.EXEC_PRICE: "0",
            CHEJAN_FID.EXEC_QTY: "0",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        assert order.state == OrderState.REJECTED


class TestIllegalTransitions:
    """Illegal state transitions are rejected."""

    def test_filled_to_accepted_rejected(self, order_manager, mock_kiwoom_api):
        """FILLED -> ACCEPTED is illegal and should not change state."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order_no = order.order_no
        order.state = OrderState.FILLED

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "접수",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "10",
            CHEJAN_FID.EXEC_PRICE: "0",
            CHEJAN_FID.EXEC_QTY: "0",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        assert order.state == OrderState.FILLED  # Should not change


class TestCancelOrder:
    """cancel_order sends cancel request via API."""

    def test_cancel_buy_order(self, order_manager, mock_kiwoom_api):
        """cancel_order for BUY order uses OrderType.CANCEL_BUY."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order.state = OrderState.ACCEPTED

        order_manager.cancel_order(order.order_no)

        # Second call should be the cancel
        cancel_call = mock_kiwoom_api.send_order.call_args_list[-1]
        assert cancel_call[1].get("order_type", cancel_call[0][3]) == OrderType.CANCEL_BUY

    def test_cancel_sell_order(self, order_manager, mock_kiwoom_api):
        """cancel_order for SELL order uses OrderType.CANCEL_SELL."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.SELL, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order.state = OrderState.ACCEPTED

        order_manager.cancel_order(order.order_no)

        cancel_call = mock_kiwoom_api.send_order.call_args_list[-1]
        assert cancel_call[1].get("order_type", cancel_call[0][3]) == OrderType.CANCEL_SELL


class TestOrderQueries:
    """get_order and get_active_orders."""

    def test_get_order_by_order_no(self, order_manager, mock_kiwoom_api):
        """get_order retrieves order by order_no."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )

        found = order_manager.get_order(order.order_no)
        assert found is order

    def test_get_order_returns_none_for_unknown(self, order_manager):
        """get_order returns None for unknown order_no."""
        assert order_manager.get_order("UNKNOWN") is None

    def test_get_active_orders_excludes_terminal(self, order_manager, mock_kiwoom_api):
        """get_active_orders returns only non-terminal orders."""
        mock_kiwoom_api.send_order.return_value = 0
        order1 = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order2 = order_manager.submit_order(
            code="000660", side=OrderSide.BUY, qty=5, price=120000, hoga_gb=HogaGb.LIMIT
        )
        # Mark order1 as FILLED (terminal)
        order1.state = OrderState.FILLED

        active = order_manager.get_active_orders()
        assert order1 not in active
        assert order2 in active


class TestBalanceNotification:
    """handle_chejan_data with gubun='1' emits position_updated."""

    def test_gubun_1_emits_position_updated(self, order_manager, mock_kiwoom_api):
        """gubun=1 (balance) parses position data and emits signal."""
        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.HOLDING_QTY: "100",
            CHEJAN_FID.BUY_UNIT_PRICE: "70000",
            CHEJAN_FID.CURRENT_PRICE: "-71000",
        })

        order_manager.handle_chejan_data("1", 4, "9001;930;931;10")
        order_manager.position_updated.emit.assert_called_once_with(
            "005930", 100, 70000, 71000
        )


class TestScreenNumberAutoIncrement:
    """Screen numbers auto-increment from SCREEN.ORDER_BASE."""

    def test_screen_numbers_increment(self, order_manager, mock_kiwoom_api):
        """Each submitted order gets a unique incrementing screen number."""
        mock_kiwoom_api.send_order.return_value = 0

        order1 = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order2 = order_manager.submit_order(
            code="000660", side=OrderSide.BUY, qty=5, price=120000, hoga_gb=HogaGb.LIMIT
        )

        assert order1.screen_no == f"{SCREEN.ORDER_BASE + 1:04d}"
        assert order2.screen_no == f"{SCREEN.ORDER_BASE + 2:04d}"


class TestPriceFieldParsing:
    """Price fields use abs(int(value)) pattern."""

    def test_negative_price_becomes_positive(self, order_manager, mock_kiwoom_api):
        """Negative exec_price is converted via abs()."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order.state = OrderState.ACCEPTED

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order.order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "체결",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "0",
            CHEJAN_FID.EXEC_PRICE: "-70000",
            CHEJAN_FID.EXEC_QTY: "10",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        assert order.filled_price == 70000

    def test_empty_price_defaults_to_zero(self, order_manager, mock_kiwoom_api):
        """Empty string price fields default to 0."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order.order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "접수",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "10",
            CHEJAN_FID.EXEC_PRICE: "",
            CHEJAN_FID.EXEC_QTY: "",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        # Should not crash, price defaults to 0
        assert order.state == OrderState.ACCEPTED


class TestSignals:
    """Signals emitted at state transitions."""

    def test_order_filled_signal(self, order_manager, mock_kiwoom_api):
        """order_filled signal emitted when order reaches FILLED."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order.state = OrderState.ACCEPTED

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order.order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "체결",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "0",
            CHEJAN_FID.EXEC_PRICE: "-70000",
            CHEJAN_FID.EXEC_QTY: "10",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        order_manager.order_filled.emit.assert_called_once_with(
            order.order_no, "005930", 10, 70000
        )

    def test_order_rejected_signal(self, order_manager, mock_kiwoom_api):
        """order_rejected signal emitted when order reaches REJECTED."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order.order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "거부",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "10",
            CHEJAN_FID.EXEC_PRICE: "0",
            CHEJAN_FID.EXEC_QTY: "0",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        order_manager.order_rejected.emit.assert_called()

    def test_order_cancelled_signal(self, order_manager, mock_kiwoom_api):
        """order_cancelled signal emitted when order reaches CANCELLED."""
        mock_kiwoom_api.send_order.return_value = 0
        order = order_manager.submit_order(
            code="005930", side=OrderSide.BUY, qty=10, price=70000, hoga_gb=HogaGb.LIMIT
        )
        order.state = OrderState.ACCEPTED

        _setup_chejan_data(mock_kiwoom_api, {
            CHEJAN_FID.ORDER_NO: order.order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "취소",
            CHEJAN_FID.ORDER_QTY: "10",
            CHEJAN_FID.UNFILLED_QTY: "10",
            CHEJAN_FID.EXEC_PRICE: "0",
            CHEJAN_FID.EXEC_QTY: "0",
            CHEJAN_FID.SELL_BUY: "2",
        })

        order_manager.handle_chejan_data("0", 8, "9203;9001;913;900;902;910;911;907")
        order_manager.order_cancelled.emit.assert_called_once_with(order.order_no)
