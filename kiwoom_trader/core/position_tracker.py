"""Position tracking with real-time P&L calculation and limit enforcement."""

from kiwoom_trader.core.models import Position, RiskConfig


class PositionTracker:
    """Tracks held positions, computes P&L, and enforces position limits.

    Single source of truth for what the system holds. Used by RiskManager
    for daily loss calculation and by OrderManager for pre-order checks.
    """

    def __init__(self, risk_config: RiskConfig) -> None:
        self._risk_config = risk_config
        self._positions: dict[str, Position] = {}
        self._daily_realized_pnl: float = 0.0

    def add_position(self, code: str, qty: int, avg_price: int) -> Position:
        """Create and store a new position with risk prices from config."""
        stop_loss_price = int(avg_price * (1 + self._risk_config.stop_loss_pct / 100))
        take_profit_price = int(avg_price * (1 + self._risk_config.take_profit_pct / 100))
        trailing_stop_price = int(
            avg_price * (1 - self._risk_config.trailing_stop_pct / 100)
        )

        position = Position(
            code=code,
            qty=qty,
            avg_price=avg_price,
            high_water_mark=avg_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            trailing_stop_price=trailing_stop_price,
        )
        self._positions[code] = position
        return position

    def update_position(self, code: str, qty: int, avg_price: int) -> None:
        """Update existing position. Removes position if qty == 0."""
        if qty == 0:
            self._positions.pop(code, None)
            return
        if code in self._positions:
            pos = self._positions[code]
            pos.qty = qty
            pos.avg_price = avg_price

    def update_from_chejan(
        self, code: str, holding_qty: int, buy_price: int, current_price: int
    ) -> None:
        """Update position from chejan (balance notification) data.

        If holding_qty > 0: add or update position with computed unrealized P&L.
        If holding_qty == 0: remove position (fully sold).
        """
        if holding_qty == 0:
            self._positions.pop(code, None)
            return

        if code not in self._positions:
            self.add_position(code, holding_qty, buy_price)

        pos = self._positions[code]
        pos.qty = holding_qty
        pos.avg_price = buy_price
        pos.unrealized_pnl = (current_price - buy_price) * holding_qty

    def get_position(self, code: str) -> Position | None:
        """Return Position for code, or None if not held."""
        return self._positions.get(code)

    def get_all_positions(self) -> dict[str, Position]:
        """Return dict of all held positions."""
        return dict(self._positions)

    def update_price(self, code: str, current_price: int) -> None:
        """Recalculate unrealized P&L for a position based on current price."""
        pos = self._positions.get(code)
        if pos is not None:
            pos.unrealized_pnl = (current_price - pos.avg_price) * pos.qty

    def get_unrealized_pnl(self) -> int:
        """Sum of all positions' unrealized P&L."""
        return sum(pos.unrealized_pnl for pos in self._positions.values())

    def get_daily_pnl(self) -> float:
        """Daily P&L = realized + unrealized (key metric for daily loss limit)."""
        return self._daily_realized_pnl + self.get_unrealized_pnl()

    def get_total_invested(self) -> int:
        """Sum of (avg_price * qty) for all positions."""
        return sum(pos.avg_price * pos.qty for pos in self._positions.values())

    def check_symbol_weight(
        self, code: str, order_amount: int, total_capital: int
    ) -> bool:
        """Check if position + order stays within max_symbol_weight_pct.

        Returns True if OK (within limit).
        """
        existing_value = 0
        pos = self._positions.get(code)
        if pos is not None:
            existing_value = pos.avg_price * pos.qty

        max_allowed = total_capital * self._risk_config.max_symbol_weight_pct / 100
        return (existing_value + order_amount) <= max_allowed

    def check_max_positions(self, code: str) -> bool:
        """Check if adding code would exceed max_positions.

        Returns True if OK. Always True if code already has a position.
        """
        if code in self._positions:
            return True
        return len(self._positions) < self._risk_config.max_positions

    def record_realized_pnl(self, amount: int) -> None:
        """Accumulate daily realized P&L."""
        self._daily_realized_pnl += amount

    def reset_daily(self) -> None:
        """Clear daily realized P&L for new trading day."""
        self._daily_realized_pnl = 0.0
