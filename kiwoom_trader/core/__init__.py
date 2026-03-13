"""Core business logic: order management, risk management, position tracking, market hours, strategy engine."""

try:
    from kiwoom_trader.core.models import (
        Order,
        OrderSide,
        OrderState,
        Position,
        RiskConfig,
        VALID_TRANSITIONS,
        Candle,
        Condition,
        CompositeRule,
        Signal,
        StrategyConfig,
        TradeRecord,
    )
    from kiwoom_trader.core.order_manager import OrderManager
    from kiwoom_trader.core.position_tracker import PositionTracker
    from kiwoom_trader.core.market_hours import MarketHoursManager
    from kiwoom_trader.core.risk_manager import RiskManager
    from kiwoom_trader.core.candle_aggregator import CandleAggregator
    from kiwoom_trader.core.condition_engine import ConditionEngine
    from kiwoom_trader.core.strategy_manager import StrategyManager
    from kiwoom_trader.core.paper_trader import PaperTrader
    from kiwoom_trader.core.indicators import (
        SMAIndicator,
        EMAIndicator,
        RSIIndicator,
        MACDIndicator,
        BollingerBandsIndicator,
        VWAPIndicator,
        OBVIndicator,
    )
except ImportError:
    # Cross-platform fallback: PyQt5 not available on macOS/Linux dev
    Order = None
    OrderSide = None
    OrderState = None
    Position = None
    RiskConfig = None
    VALID_TRANSITIONS = None
    Candle = None
    Condition = None
    CompositeRule = None
    Signal = None
    StrategyConfig = None
    TradeRecord = None
    OrderManager = None
    PositionTracker = None
    MarketHoursManager = None
    RiskManager = None
    CandleAggregator = None
    ConditionEngine = None
    StrategyManager = None
    PaperTrader = None
    SMAIndicator = None
    EMAIndicator = None
    RSIIndicator = None
    MACDIndicator = None
    BollingerBandsIndicator = None
    VWAPIndicator = None
    OBVIndicator = None
