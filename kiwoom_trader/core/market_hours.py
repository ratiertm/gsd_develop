"""Market hours management with time-based trading permission control."""

from datetime import datetime, time
from typing import Callable

from kiwoom_trader.config.constants import MarketState
from kiwoom_trader.core.models import RiskConfig


class MarketHoursManager:
    """Determines market state and controls trading permission based on time.

    Uses injected time_func for deterministic testing. All time boundaries
    are parsed from RiskConfig strings (not hardcoded).

    Market states (KRX regular session):
        CLOSED             -> before 08:30 or after 15:30
        PRE_MARKET_AUCTION -> 08:30 ~ 09:00 (simultaneous call auction)
        MARKET_OPEN_BUFFER -> 09:00 ~ 09:05 (stabilization wait)
        TRADING            -> 09:05 ~ 15:15 (regular trading)
        CLOSING            -> 15:15 ~ 15:20 (new buys blocked, liquidation only)
        CLOSING_AUCTION    -> 15:20 ~ 15:30 (closing call auction)
        CLOSED             -> 15:30 ~
    """

    def __init__(
        self,
        risk_config: RiskConfig,
        time_func: Callable[[], time] | None = None,
    ) -> None:
        self._risk_config = risk_config
        self._time_func = time_func or (lambda: datetime.now().time())

        # State transition tracking
        self._previous_state: MarketState | None = None
        self._state_callbacks: list[Callable[[MarketState, MarketState], None]] = []

        # Parse time strings from RiskConfig into datetime.time objects
        self._auction_start_am = self._parse_time(risk_config.auction_start_am)
        self._auction_end_am = self._parse_time(risk_config.auction_end_am)
        self._trading_start = self._parse_time(risk_config.trading_start)
        self._trading_end_new_buy = self._parse_time(risk_config.trading_end_new_buy)
        self._auction_start_pm = self._parse_time(risk_config.auction_start_pm)
        self._auction_end_pm = self._parse_time(risk_config.auction_end_pm)

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse 'HH:MM' string to datetime.time."""
        return datetime.strptime(time_str, "%H:%M").time()

    def get_market_state(self) -> MarketState:
        """Determine current market state from time boundaries."""
        now = self._time_func()

        if now < self._auction_start_am:
            return MarketState.CLOSED
        if now < self._auction_end_am:
            return MarketState.PRE_MARKET_AUCTION
        if now < self._trading_start:
            return MarketState.MARKET_OPEN_BUFFER
        if now < self._trading_end_new_buy:
            return MarketState.TRADING
        if now < self._auction_start_pm:
            return MarketState.CLOSING
        if now < self._auction_end_pm:
            return MarketState.CLOSING_AUCTION
        return MarketState.CLOSED

    def is_trading_allowed(self) -> bool:
        """True only during TRADING state (09:05-15:15)."""
        return self.get_market_state() == MarketState.TRADING

    def is_new_buy_allowed(self) -> bool:
        """True only during TRADING state. CLOSING allows sell only."""
        return self.get_market_state() == MarketState.TRADING

    def is_order_blocked(self) -> bool:
        """True during auction periods, buffer, and closed -- no orders allowed."""
        return self.get_market_state() in {
            MarketState.PRE_MARKET_AUCTION,
            MarketState.CLOSING_AUCTION,
            MarketState.MARKET_OPEN_BUFFER,
            MarketState.CLOSED,
        }

    def is_closing_time(self) -> bool:
        """True during CLOSING state (15:15-15:20) -- liquidation only."""
        return self.get_market_state() == MarketState.CLOSING

    def register_state_callback(
        self, callback: Callable[[MarketState, MarketState], None]
    ) -> None:
        """Register a callback to fire on state transitions.

        Args:
            callback: Called with (old_state, new_state) when market state changes.
        """
        self._state_callbacks.append(callback)

    def check_state_transition(self) -> tuple[MarketState, MarketState] | None:
        """Check for market state change and fire callbacks if detected.

        Designed to be called periodically (e.g., from a QTimer).

        Returns:
            (old_state, new_state) tuple if a transition occurred, None otherwise.
            First call always returns None (initializes previous state).
        """
        current = self.get_market_state()

        if self._previous_state is None:
            # First call: initialize, no transition
            self._previous_state = current
            return None

        if current == self._previous_state:
            return None

        old_state = self._previous_state
        self._previous_state = current

        # Fire all registered callbacks
        for callback in self._state_callbacks:
            callback(old_state, current)

        return (old_state, current)
