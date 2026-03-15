"""Risk management: pre-trade validation, real-time triggers, split orders.

Central safety layer -- no order reaches the market without passing market hours,
position limits, and daily loss checks. Real-time price triggers protect profits
and limit losses. Split order execution enables gradual position building/unwinding.
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

from kiwoom_trader.config.constants import FID, HogaGb
from kiwoom_trader.core.models import OrderSide, RiskConfig


class RiskManager(QObject if _HAS_PYQT5 else object):
    """Pre-trade validation, real-time risk triggers, and split order execution.

    Gates all orders through 6 checks (market hours, buy permission, daily buy
    block, daily loss, symbol weight, max positions). Monitors real-time prices
    for stop-loss, take-profit, and trailing stop triggers. Enforces daily loss
    limit with full portfolio liquidation.
    """

    # Signals
    trigger_stop_loss = pyqtSignal(str, int)  # code, price
    trigger_take_profit = pyqtSignal(str, int)  # code, price
    trigger_trailing_stop = pyqtSignal(str, int)  # code, price
    daily_loss_limit_hit = pyqtSignal()
    position_liquidated = pyqtSignal(str)  # code

    def __init__(
        self,
        order_manager,
        position_tracker,
        market_hours,
        risk_config: RiskConfig,
        total_capital: int,
    ):
        if _HAS_PYQT5:
            super().__init__()
        self._order_manager = order_manager
        self._position_tracker = position_tracker
        self._market_hours = market_hours
        self._risk_config = risk_config
        if total_capital <= 0:
            raise ValueError(f"total_capital must be > 0, got {total_capital}")
        self._total_capital = total_capital
        self._daily_buy_blocked = False
        logger.info(
            f"RiskManager initialized: capital={total_capital}, "
            f"SL={risk_config.stop_loss_pct}%, TP={risk_config.take_profit_pct}%, "
            f"TS={risk_config.trailing_stop_pct}%"
        )

    def validate_order(
        self, code: str, side: OrderSide, qty: int, price: int
    ) -> tuple[bool, str]:
        """Pre-trade validation gate. All checks must pass.

        Returns (True, "OK") if valid, or (False, reason) if rejected.
        """
        # 1. Market hours block
        if self._market_hours.is_order_blocked():
            return False, "Orders blocked during current market state"

        # BUY-specific checks
        if side == OrderSide.BUY:
            # 2. New buy permission
            if not self._market_hours.is_new_buy_allowed():
                return False, "New buys not allowed in current state"

            # 3. Daily buy block (set after daily loss limit hit)
            if self._daily_buy_blocked:
                return False, "Daily loss limit reached, buys blocked"

            # 4. Daily P&L check
            daily_pnl_pct = (
                self._position_tracker.get_daily_pnl() / self._total_capital * 100
            )
            if daily_pnl_pct <= -self._risk_config.daily_loss_limit_pct:
                return False, "Daily loss limit exceeded"

            # 5. Symbol weight
            if not self._position_tracker.check_symbol_weight(
                code, qty * price, self._total_capital
            ):
                return False, "Symbol weight limit exceeded"

            # 6. Max positions
            if not self._position_tracker.check_max_positions(code):
                return False, "Max positions limit exceeded"

        return True, "OK"

    def on_price_update(self, code: str, data_dict: dict) -> None:
        """Real-time price subscriber callback. Evaluates risk triggers.

        Called by RealDataManager on every price tick for subscribed stocks.
        """
        # 1. Extract current price
        raw = data_dict.get(FID.CURRENT_PRICE, "0") or "0"
        current_price = abs(int(raw))
        if current_price == 0:
            return

        # 2. Update position price (unrealized P&L recalc)
        self._position_tracker.update_price(code, current_price)

        # 3. Get position
        position = self._position_tracker.get_position(code)
        if position is None:
            return

        # 4. Daily loss check (realized + unrealized)
        daily_pnl_pct = (
            self._position_tracker.get_daily_pnl() / self._total_capital * 100
        )
        if daily_pnl_pct <= -self._risk_config.daily_loss_limit_pct:
            logger.warning(
                f"Daily loss limit hit: {daily_pnl_pct:.2f}% "
                f"(limit: -{self._risk_config.daily_loss_limit_pct}%)"
            )
            self.daily_loss_limit_hit.emit()
            self.liquidate_all()
            self._daily_buy_blocked = True
            return

        # 5. Stop-loss check
        if position.stop_loss_price > 0 and current_price <= position.stop_loss_price:
            logger.info(
                f"Stop-loss triggered: {code} price={current_price} "
                f"<= SL={position.stop_loss_price}"
            )
            self.trigger_stop_loss.emit(code, current_price)
            self._order_manager.submit_order(
                code, OrderSide.SELL, position.qty, 0, HogaGb.MARKET
            )
            return

        # 6. Take-profit check
        if (
            position.take_profit_price > 0
            and current_price >= position.take_profit_price
        ):
            logger.info(
                f"Take-profit triggered: {code} price={current_price} "
                f">= TP={position.take_profit_price}"
            )
            self.trigger_take_profit.emit(code, current_price)
            self._order_manager.submit_order(
                code, OrderSide.SELL, position.qty, 0, HogaGb.MARKET
            )
            return

        # 7. Trailing stop: update HWM or check trigger
        if current_price > position.high_water_mark:
            position.high_water_mark = current_price
            position.trailing_stop_price = int(
                current_price * (1 - self._risk_config.trailing_stop_pct / 100)
            )
        elif (
            position.trailing_stop_price > 0
            and current_price <= position.trailing_stop_price
        ):
            logger.info(
                f"Trailing stop triggered: {code} price={current_price} "
                f"<= TS={position.trailing_stop_price}"
            )
            self.trigger_trailing_stop.emit(code, current_price)
            self._order_manager.submit_order(
                code, OrderSide.SELL, position.qty, 0, HogaGb.MARKET
            )

    def liquidate_all(self) -> None:
        """Emergency liquidation: sell all positions, worst first."""
        positions = self._position_tracker.get_all_positions()
        # Sort by unrealized_pnl ascending (worst first)
        sorted_positions = sorted(
            positions.values(), key=lambda p: p.unrealized_pnl
        )

        for pos in sorted_positions:
            logger.warning(f"Liquidating position: {pos.code} qty={pos.qty}")
            self._order_manager.submit_order(
                pos.code, OrderSide.SELL, pos.qty, 0, HogaGb.MARKET
            )
            self.position_liquidated.emit(pos.code)

        self._daily_buy_blocked = True

    def on_closing_time(self) -> None:
        """End-of-day liquidation. Called when market transitions to CLOSING."""
        positions = self._position_tracker.get_all_positions()
        if not positions:
            return

        logger.info("End-of-day liquidation triggered")
        for pos in positions.values():
            self._order_manager.submit_order(
                pos.code, OrderSide.SELL, pos.qty, 0, HogaGb.MARKET
            )

    def split_buy(
        self, code: str, total_qty: int, price: int, hoga_gb: str
    ) -> list[int]:
        """Split buy into parts. Submits first part immediately.

        Returns list of quantity splits (e.g., [33, 33, 34]).
        Callers are responsible for scheduling remaining parts.
        """
        splits = self._compute_splits(total_qty, self._risk_config.split_count)
        # Submit first part immediately
        self._order_manager.submit_order(
            code, OrderSide.BUY, splits[0], price, hoga_gb
        )
        logger.info(
            f"Split buy: {code} total={total_qty} -> {splits}, "
            f"first part submitted"
        )
        return splits

    def split_sell(
        self, code: str, total_qty: int, price: int, hoga_gb: str
    ) -> list[int]:
        """Split sell into parts. Submits first part immediately.

        Returns list of quantity splits.
        """
        splits = self._compute_splits(total_qty, self._risk_config.split_count)
        # Submit first part immediately
        self._order_manager.submit_order(
            code, OrderSide.SELL, splits[0], price, hoga_gb
        )
        logger.info(
            f"Split sell: {code} total={total_qty} -> {splits}, "
            f"first part submitted"
        )
        return splits

    def _compute_splits(self, total_qty: int, count: int) -> list[int]:
        """Divide total_qty into `count` parts. Last part gets remainder.

        E.g., 100 / 3 -> [33, 33, 34]
        """
        base = total_qty // count
        splits = [base] * (count - 1)
        splits.append(total_qty - base * (count - 1))
        return splits

    def reset_daily(self) -> None:
        """Clear daily buy block. Called at start of each trading day."""
        self._daily_buy_blocked = False
        logger.info("RiskManager daily state reset")
