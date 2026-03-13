"""Application entry point for KiwoomDayTrader.

Wires all core components together and starts the Qt event loop:
- Phase 1: KiwoomAPI, EventHandlerRegistry, TRRequestQueue, SessionManager, RealDataManager
- Phase 2: OrderManager, RiskManager, PositionTracker, MarketHoursManager
- Phase 3: CandleAggregator, ConditionEngine, StrategyManager, PaperTrader
"""

import sys

from loguru import logger

from kiwoom_trader.api import (
    EventHandlerRegistry,
    KiwoomAPI,
    RealDataManager,
    SessionManager,
    TRRequestQueue,
)
from kiwoom_trader.config.settings import Settings
from kiwoom_trader.utils.logger import setup_logging

# Phase 2 imports (may fail on macOS dev without PyQt5)
try:
    from kiwoom_trader.core import (
        MarketHoursManager,
        OrderManager,
        PositionTracker,
        RiskManager,
    )

    _HAS_CORE = True
except (ImportError, TypeError):
    _HAS_CORE = False

# Phase 3 imports (may fail on macOS dev without PyQt5)
try:
    from kiwoom_trader.core import (
        CandleAggregator,
        ConditionEngine,
        PaperTrader,
        StrategyManager,
    )

    _HAS_STRATEGY = True
except (ImportError, TypeError):
    _HAS_STRATEGY = False


def main():
    """Initialize all components, wire event routing, and start Qt event loop."""
    from PyQt5.QtWidgets import QApplication

    setup_logging()
    logger.info("=== KiwoomDayTrader starting ===")

    app = QApplication(sys.argv)
    settings = Settings()

    # === Phase 1: API Foundation ===
    api = KiwoomAPI()
    event_registry = EventHandlerRegistry()
    tr_queue = TRRequestQueue(
        api, interval_ms=settings._config["tr_interval_ms"]
    )
    session_manager = SessionManager(api)
    real_data_manager = RealDataManager(api, session_manager=session_manager)

    # Wire event routing: TR data -> EventHandlerRegistry
    api.tr_data_received.connect(
        lambda *args: event_registry.handle_tr_data(args[1], *args)
    )

    # Wire event routing: real data -> RealDataManager
    api.real_data_received.connect(
        lambda code, real_type, data: real_data_manager.on_real_data(
            code, real_type, data
        )
    )

    # Wire session events
    session_manager.session_restored.connect(
        lambda: logger.info("Session restored")
    )
    session_manager.session_lost.connect(
        lambda: logger.warning("Session lost")
    )

    # === Phase 2: Order Execution & Risk Management ===
    if _HAS_CORE and OrderManager is not None:
        risk_config = settings.risk_config
        account_no = settings.account_no
        total_capital = settings._config.get("total_capital", 10_000_000)

        # Instantiate Phase 2 components
        position_tracker = PositionTracker(risk_config)
        market_hours = MarketHoursManager(risk_config)
        order_manager = OrderManager(api, account_no)
        risk_manager = RiskManager(
            order_manager=order_manager,
            position_tracker=position_tracker,
            market_hours=market_hours,
            risk_config=risk_config,
            total_capital=total_capital,
        )

        # Subscribe RiskManager to real-time price data
        real_data_manager.register_subscriber(
            "주식체결", risk_manager.on_price_update
        )

        # Wire chejan events: KiwoomAPI -> EventHandlerRegistry -> OrderManager
        api.chejan_data_received.connect(
            lambda gubun, item_cnt, fid_list: order_manager.handle_chejan_data(
                gubun, item_cnt, fid_list
            )
        )

        # Wire balance updates from OrderManager to PositionTracker
        order_manager.position_updated.connect(
            lambda code, qty, buy_price, current_price: (
                position_tracker.update_from_chejan(
                    code, qty, buy_price, current_price
                )
            )
        )

        logger.info(
            "Phase 2 components wired: "
            "OrderManager, RiskManager, PositionTracker, MarketHoursManager"
        )
    else:
        risk_manager = None
        order_manager = None
        market_hours = None
        logger.warning(
            "Phase 2 core imports unavailable (PyQt5 missing?). "
            "Skipping order/risk wiring."
        )

    # === Phase 3: Data Pipeline & Strategy Engine ===
    if _HAS_STRATEGY and CandleAggregator is not None:
        strategy_config = settings.strategy_config
        mode = strategy_config["mode"]

        # CandleAggregator: tick -> candle conversion
        candle_aggregator = CandleAggregator(
            interval_minutes=strategy_config["candle_interval_minutes"]
        )

        # ConditionEngine: composite rule evaluation
        condition_engine = ConditionEngine()

        # PaperTrader for paper mode
        paper_trader = None
        if mode == "paper":
            paper_trader = PaperTrader(
                csv_path="logs/trades.csv",
                initial_capital=strategy_config.get("total_capital", 10_000_000),
                max_symbol_weight_pct=settings.risk_config.max_symbol_weight_pct,
            )

        # StrategyManager: indicator management, condition evaluation, signal routing
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=risk_manager,
            order_manager=order_manager,
            config=strategy_config,
        )

        # Set paper trader reference if in paper mode
        if mode == "paper" and paper_trader is not None:
            strategy_manager.paper_trader = paper_trader

        # Wire: RealDataManager tick -> CandleAggregator
        real_data_manager.register_subscriber(
            "주식체결", candle_aggregator.on_tick
        )

        # Wire: CandleAggregator candle -> StrategyManager
        # Direct 2-arg match: callback(code, candle) -> on_candle_complete(code, candle)
        candle_aggregator.register_callback(strategy_manager.on_candle_complete)

        # Wire VWAP daily reset: when MarketHoursManager transitions to TRADING state
        # MarketHoursManager.get_market_state() is polled; reset_vwap is called
        # alongside daily resets at trading start
        if market_hours is not None:
            # VWAP reset is triggered at the start of each trading day
            # alongside other daily resets (cooldown, position P&L, etc.)
            pass

        # Wire daily reset: strategy cooldowns reset alongside existing daily resets
        # strategy_manager.reset_daily() should be called when new trading day starts
        # strategy_manager.reset_vwap() should be called on TRADING state transition

        logger.info(
            f"Phase 3 components wired: CandleAggregator, ConditionEngine, "
            f"StrategyManager, mode={mode}"
        )
    else:
        logger.warning(
            "Phase 3 strategy imports unavailable. "
            "Skipping data pipeline/strategy wiring."
        )

    # Open login dialog
    api.comm_connect()
    logger.info("Login dialog opened, waiting for user...")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
