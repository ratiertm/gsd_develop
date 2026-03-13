"""Core business logic: order management, risk management, position tracking, market hours."""

try:
    from kiwoom_trader.core.models import (
        Order,
        OrderSide,
        OrderState,
        Position,
        RiskConfig,
        VALID_TRANSITIONS,
    )
    from kiwoom_trader.core.order_manager import OrderManager
    from kiwoom_trader.core.position_tracker import PositionTracker
    from kiwoom_trader.core.market_hours import MarketHoursManager
    from kiwoom_trader.core.risk_manager import RiskManager
except ImportError:
    # Cross-platform fallback: PyQt5 not available on macOS/Linux dev
    Order = None
    OrderSide = None
    OrderState = None
    Position = None
    RiskConfig = None
    VALID_TRANSITIONS = None
    OrderManager = None
    PositionTracker = None
    MarketHoursManager = None
    RiskManager = None
