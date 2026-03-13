"""Application entry point for KiwoomDayTrader.

Wires all core components together and starts the Qt event loop:
- Phase 1: KiwoomAPI, EventHandlerRegistry, TRRequestQueue, SessionManager, RealDataManager
- Phase 2: OrderManager, RiskManager, PositionTracker, MarketHoursManager
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
        logger.warning(
            "Phase 2 core imports unavailable (PyQt5 missing?). "
            "Skipping order/risk wiring."
        )

    # Open login dialog
    api.comm_connect()
    logger.info("Login dialog opened, waiting for user...")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
