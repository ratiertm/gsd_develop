"""Application entry point for KiwoomDayTrader.

Wires all core components together and starts the Qt event loop:
- KiwoomAPI (COM wrapper)
- EventHandlerRegistry (event routing)
- TRRequestQueue (rate-limited TR dispatch)
- SessionManager (auto-reconnect + subscription restore)
- RealDataManager (real-time data subscription + dispatch)
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


def main():
    """Initialize all components, wire event routing, and start Qt event loop."""
    from PyQt5.QtWidgets import QApplication

    setup_logging()
    logger.info("=== KiwoomDayTrader starting ===")

    app = QApplication(sys.argv)
    settings = Settings()

    # Initialize core components
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

    # Open login dialog
    api.comm_connect()
    logger.info("Login dialog opened, waiting for user...")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
