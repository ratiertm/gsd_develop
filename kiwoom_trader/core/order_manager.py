"""Order lifecycle manager with Enum-based state machine.

Manages order submission, cancellation, and ChejanData event processing.
Tracks every order through its full lifecycle via state machine
(CREATED -> SUBMITTED -> ACCEPTED -> FILLED/CANCELLED/REJECTED).
"""

try:
    from PyQt5.QtCore import QObject, pyqtSignal

    _HAS_PYQT5 = True
except ImportError:
    from unittest.mock import MagicMock

    QObject = object

    def pyqtSignal(*args, **kwargs):
        return MagicMock()

    _HAS_PYQT5 = False

from loguru import logger

from kiwoom_trader.config.constants import (
    CHEJAN_FID,
    ORDER_ERROR,
    OrderType,
    SCREEN,
)
from kiwoom_trader.core.models import (
    Order,
    OrderSide,
    OrderState,
    VALID_TRANSITIONS,
)

# Terminal states -- orders in these states cannot transition further
_TERMINAL_STATES = {OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED}


class OrderManager(QObject if _HAS_PYQT5 else object):
    """Manages order lifecycle with state machine validation.

    Submits orders via KiwoomAPI.send_order(), processes ChejanData events
    to track order state transitions, and emits signals at key lifecycle points.
    """

    # Signals (real pyqtSignal on Windows, MagicMock on macOS/Linux for testing)
    order_submitted = pyqtSignal(str)  # order_no
    order_filled = pyqtSignal(str, str, int, int)  # order_no, code, qty, price
    order_rejected = pyqtSignal(str, str)  # order_no, reason
    order_cancelled = pyqtSignal(str)  # order_no
    position_updated = pyqtSignal(str, int, int, int)  # code, qty, buy_price, current_price

    def __init__(self, kiwoom_api, account_no: str):
        if _HAS_PYQT5:
            super().__init__()
        self._api = kiwoom_api
        self._account_no = account_no
        self._orders: dict[str, Order] = {}
        self._pending_orders: dict[str, Order] = {}  # temp_id -> Order (awaiting real order_no)
        self._screen_counter = SCREEN.ORDER_BASE
        self._internal_id_counter = 0  # For orders before they get a real order_no
        logger.info(f"OrderManager initialized for account {account_no}")

    def submit_order(
        self,
        code: str,
        side: OrderSide,
        qty: int,
        price: int,
        hoga_gb: str,
    ) -> Order:
        """Create and submit an order. Returns the Order dataclass.

        On send_order() returning 0: transitions to SUBMITTED, stores order.
        On send_order() returning negative: transitions to REJECTED.
        """
        order_type = OrderType.NEW_BUY if side == OrderSide.BUY else OrderType.NEW_SELL
        screen_no = self._next_screen_no()

        # Generate a temporary internal order_no until the exchange assigns one
        self._internal_id_counter += 1
        temp_order_no = f"ORD_{self._internal_id_counter:06d}"

        order = Order(
            code=code,
            side=side,
            qty=qty,
            price=price,
            order_type=order_type,
            hoga_gb=hoga_gb,
            screen_no=screen_no,
            rq_name=f"order_{code}_{temp_order_no}",
            order_no=temp_order_no,
        )

        ret = self._api.send_order(
            order.rq_name,
            screen_no,
            self._account_no,
            order_type,
            code,
            qty,
            price,
            hoga_gb,
            "",  # org_order_no (empty for new orders)
        )

        if ret == ORDER_ERROR.SUCCESS:
            self._transition_state(order, OrderState.SUBMITTED)
            # Store in pending until chejan assigns real order_no
            self._pending_orders[temp_order_no] = order
            self.order_submitted.emit(order.order_no)
            logger.info(
                f"Order submitted: {order.order_no} {side.name} {code} "
                f"qty={qty} price={price}"
            )
        else:
            self._transition_state(order, OrderState.REJECTED)
            self.order_rejected.emit(order.order_no, f"SendOrder failed: ret={ret}")
            logger.error(
                f"Order rejected at send: {order.order_no} {side.name} {code} ret={ret}"
            )

        return order

    def cancel_order(self, order_no: str) -> int:
        """Submit a cancel request for an existing order.

        Returns the send_order return code (0 = accepted, negative = error).
        """
        order = self._orders.get(order_no)
        if order is None:
            logger.error(f"cancel_order: unknown order_no={order_no}")
            return -1

        cancel_type = (
            OrderType.CANCEL_BUY if order.side == OrderSide.BUY else OrderType.CANCEL_SELL
        )
        screen_no = self._next_screen_no()

        ret = self._api.send_order(
            f"cancel_{order.code}_{order_no}",
            screen_no,
            self._account_no,
            cancel_type,
            order.code,
            order.qty,
            0,  # price=0 for cancel
            "",  # hoga_gb="" for cancel
            order_no,  # org_order_no
        )

        logger.info(f"Cancel request sent for {order_no}: ret={ret}")
        return ret

    def handle_chejan_data(self, gubun: str, item_cnt: int, fid_list: str):
        """Process OnReceiveChejanData events.

        gubun="0": Order/execution notification -- parse FIDs and transition state.
        gubun="1": Balance notification -- emit position_updated signal.
        """
        if gubun == "0":
            self._handle_order_chejan()
        elif gubun == "1":
            self._handle_balance_chejan()
        else:
            logger.warning(f"Unknown chejan gubun: {gubun}")

    def _handle_order_chejan(self):
        """Parse gubun=0 (order/execution) chejan data and update order state."""
        # Parse FIDs
        order_no = self._api.get_chejan_data(CHEJAN_FID.ORDER_NO).strip()
        raw_code = self._api.get_chejan_data(CHEJAN_FID.CODE).strip()
        order_status = self._api.get_chejan_data(CHEJAN_FID.ORDER_STATUS).strip()
        unfilled_qty = self._parse_int(self._api.get_chejan_data(CHEJAN_FID.UNFILLED_QTY))
        exec_price = self._parse_price(self._api.get_chejan_data(CHEJAN_FID.EXEC_PRICE))
        exec_qty = self._parse_int(self._api.get_chejan_data(CHEJAN_FID.EXEC_QTY))

        # Strip leading "A" from code (Kiwoom prefixes stock codes with "A")
        code = raw_code.replace("A", "")

        # Look up order -- try main dict first, then resolve from pending
        order = self._orders.get(order_no)
        if order is None:
            # Check pending orders: match by code (first pending for that code)
            matched_temp = None
            for temp_id, pending in self._pending_orders.items():
                if pending.code == code:
                    matched_temp = temp_id
                    break

            if matched_temp:
                order = self._pending_orders.pop(matched_temp)
                order.order_no = order_no
                self._orders[order_no] = order
                logger.info(
                    f"주문번호 매핑: {matched_temp} -> {order_no} ({code})"
                )
            else:
                logger.warning(
                    f"Chejan data for untracked order: order_no={order_no}, "
                    f"code={code}, status={order_status}"
                )
                return

        # Determine new state from order_status + execution data
        new_state = self._determine_state(order_status, unfilled_qty, exec_qty)
        if new_state is None:
            logger.warning(
                f"Could not determine state from chejan: "
                f"order_status={order_status}, unfilled={unfilled_qty}, exec_qty={exec_qty}"
            )
            return

        # Attempt transition
        old_state = order.state
        if self._transition_state(order, new_state):
            # Update fill data
            if exec_qty > 0:
                order.filled_qty = exec_qty
                order.filled_price = exec_price

            # Emit signals based on new state
            if new_state == OrderState.FILLED:
                self.order_filled.emit(order_no, code, exec_qty, exec_price)
            elif new_state == OrderState.CANCELLED:
                self.order_cancelled.emit(order_no)
            elif new_state == OrderState.REJECTED:
                self.order_rejected.emit(order_no, f"Rejected via chejan: {order_status}")

            logger.info(
                f"Order {order_no} transition: {old_state.name} -> {new_state.name}"
            )

    def _handle_balance_chejan(self):
        """Parse gubun=1 (balance) chejan data and emit position signal."""
        raw_code = self._api.get_chejan_data(CHEJAN_FID.CODE).strip()
        code = raw_code.replace("A", "")
        holding_qty = self._parse_int(self._api.get_chejan_data(CHEJAN_FID.HOLDING_QTY))
        buy_price = self._parse_price(self._api.get_chejan_data(CHEJAN_FID.BUY_UNIT_PRICE))
        current_price = self._parse_price(self._api.get_chejan_data(CHEJAN_FID.CURRENT_PRICE))

        self.position_updated.emit(code, holding_qty, buy_price, current_price)
        logger.info(
            f"Balance update: {code} qty={holding_qty} "
            f"buy_price={buy_price} current={current_price}"
        )

    def _determine_state(
        self, order_status: str, unfilled_qty: int, exec_qty: int
    ) -> OrderState | None:
        """Determine target OrderState from chejan data fields."""
        if "거부" in order_status:
            return OrderState.REJECTED
        if "취소" in order_status:
            return OrderState.CANCELLED
        if unfilled_qty == 0 and exec_qty > 0:
            return OrderState.FILLED
        if unfilled_qty > 0 and exec_qty > 0:
            return OrderState.PARTIAL_FILL
        if "접수" in order_status:
            return OrderState.ACCEPTED
        return None

    def _transition_state(self, order: Order, new_state: OrderState) -> bool:
        """Validate and apply state transition.

        Returns True if transition was applied, False if illegal.
        """
        allowed = VALID_TRANSITIONS.get(order.state, set())
        if new_state not in allowed:
            logger.error(
                f"Illegal transition for order {order.order_no}: "
                f"{order.state.name} -> {new_state.name} "
                f"(allowed: {[s.name for s in allowed]})"
            )
            return False
        order.state = new_state
        return True

    def get_order(self, order_no: str) -> Order | None:
        """Retrieve an order by order_no. Returns None if not found."""
        return self._orders.get(order_no)

    def get_active_orders(self) -> list[Order]:
        """Return all orders not in terminal states (FILLED, CANCELLED, REJECTED)."""
        return [
            order
            for order in self._orders.values()
            if order.state not in _TERMINAL_STATES
        ]

    def _next_screen_no(self) -> str:
        """Auto-increment screen number from SCREEN.ORDER_BASE."""
        self._screen_counter += 1
        return f"{self._screen_counter:04d}"

    @staticmethod
    def _parse_int(value: str) -> int:
        """Parse integer from chejan string, default to 0 on empty/error."""
        value = value.strip()
        if not value:
            return 0
        try:
            return abs(int(value))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_price(value: str) -> int:
        """Parse price with abs() for Kiwoom's signed price convention."""
        value = value.strip()
        if not value:
            return 0
        try:
            return abs(int(value))
        except (ValueError, TypeError):
            return 0
