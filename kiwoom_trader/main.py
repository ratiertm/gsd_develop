"""Application entry point for KiwoomDayTrader.

Wires all core components together and starts the Qt event loop:
- Phase 1: KiwoomAPI, EventHandlerRegistry, TRRequestQueue, SessionManager, RealDataManager
- Phase 2: OrderManager, RiskManager, PositionTracker, MarketHoursManager
- Phase 3: CandleAggregator, ConditionEngine, StrategyManager, PaperTrader
- Phase 4: MainWindow (Dashboard, Chart, Strategy tabs), Notifier, signal wiring
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
    from kiwoom_trader.config.constants import MarketState
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

# Phase 4 imports: GUI and notification (may fail without PyQt5)
try:
    from kiwoom_trader.gui import MainWindow
    from kiwoom_trader.gui.notification.notifier import Notifier

    _HAS_GUI = True
except (ImportError, TypeError):
    _HAS_GUI = False

# Phase 5 imports: Backtest (may fail without PyQt5)
try:
    from kiwoom_trader.backtest import (
        BacktestEngine,
        BacktestWorker,
        CostConfig,
        KiwoomDataSource,
    )
    from kiwoom_trader.backtest.performance import compute_all_metrics
    from kiwoom_trader.gui.backtest_dialog import BacktestDialog

    _HAS_BACKTEST = True
except (ImportError, TypeError):
    _HAS_BACKTEST = False


def main():
    """Initialize all components, wire event routing, and start Qt event loop."""
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer

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
    position_tracker = None
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
    candle_aggregator = None
    strategy_manager = None
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

        # Wire daily resets via MarketHoursManager state transition detection
        if market_hours is not None:
            def _on_market_state_changed(old_state, new_state):
                """Reset VWAP and cooldowns when trading day starts."""
                if new_state == MarketState.TRADING:
                    strategy_manager.reset_vwap()
                    strategy_manager.reset_daily()
                    logger.info(
                        f"Trading day started ({old_state.value} -> {new_state.value}): "
                        "VWAP and cooldowns reset"
                    )

            market_hours.register_state_callback(_on_market_state_changed)

            # Poll market state transitions every 10 seconds
            market_state_timer = QTimer()
            market_state_timer.timeout.connect(market_hours.check_state_transition)
            market_state_timer.start(10_000)

        logger.info(
            f"Phase 3 components wired: CandleAggregator, ConditionEngine, "
            f"StrategyManager, mode={mode}"
        )
    else:
        logger.warning(
            "Phase 3 strategy imports unavailable. "
            "Skipping data pipeline/strategy wiring."
        )

    # === Phase 4: Monitoring & Operations ===
    if _HAS_GUI and MainWindow is not None:
        # Strategy reload callback for hot-swap
        def _reload_strategies():
            """Re-create StrategyManager with updated config (hot-swap)."""
            nonlocal strategy_manager
            if not (_HAS_STRATEGY and ConditionEngine is not None):
                return
            new_config = settings.strategy_config
            new_engine = ConditionEngine()
            strategy_manager = StrategyManager(
                condition_engine=new_engine,
                risk_manager=risk_manager,
                order_manager=order_manager,
                config=new_config,
            )
            # Re-wire candle callback to new strategy manager
            if candle_aggregator is not None:
                candle_aggregator._callbacks.clear()
                candle_aggregator.register_callback(strategy_manager.on_candle_complete)
            logger.info("StrategyManager hot-swapped with updated config")

        # Create MainWindow with real tabs
        main_window = MainWindow(
            settings,
            on_strategy_reload=_reload_strategies,
        )
        main_window.show()

        # Get tab references for signal wiring
        dashboard = main_window._dashboard_tab
        chart_tab = main_window._chart_tab
        strategy_tab = main_window._strategy_tab

        # Create Notifier with GUI toast support
        notifier = Notifier(
            config=settings.notification_config,
            main_window=main_window,
        )

        # --- Wire Dashboard signals ---

        # 1. QTimer (1s interval) to poll PositionTracker and update dashboard
        if position_tracker is not None:
            dashboard_timer = QTimer()

            def _update_dashboard():
                """Poll position/P&L data and push to dashboard."""
                positions = position_tracker.positions
                total_invested = sum(
                    p.avg_price * p.qty for p in positions.values()
                )
                unrealized = sum(p.unrealized_pnl for p in positions.values())
                dashboard.update_positions(positions, total_invested)
                dashboard.update_pnl(
                    daily_pnl=position_tracker.daily_realized_pnl,
                    unrealized_pnl=unrealized,
                    total_invested=total_invested,
                )

            dashboard_timer.timeout.connect(_update_dashboard)
            dashboard_timer.start(1000)

        # 2. order_filled -> dashboard: bridge signal impedance mismatch
        #    OrderManager.order_filled emits (order_no, code, qty, price)
        #    DashboardTab.update_orders() expects list[Order]
        if order_manager is not None:
            order_manager.order_filled.connect(
                lambda order_no, code, qty, price: dashboard.update_orders(
                    order_manager.get_active_orders()
                )
            )

            # Also notify on fills
            order_manager.order_filled.connect(
                lambda order_no, code, qty, price: notifier.notify(
                    "trade",
                    f"Order Filled: {code}",
                    f"#{order_no} {code} x{qty} @{price:,}",
                    {"code": code, "price": price, "qty": qty, "side": "FILL"},
                )
            )

        # 3. MarketHoursManager state change -> dashboard update_status
        if market_hours is not None:
            def _on_market_state_for_dashboard(old_state, new_state):
                """Update dashboard status on market state change."""
                strategy_count = (
                    len(strategy_manager.strategies)
                    if strategy_manager is not None
                    else 0
                )
                dashboard.update_status(
                    connected=True,
                    market_state=new_state.value,
                    strategy_count=strategy_count,
                    mode=settings._config.get("mode", "paper"),
                )

            market_hours.register_state_callback(_on_market_state_for_dashboard)

        # --- Wire Chart signals ---

        # CandleAggregator -> ChartTab.on_new_candle
        if candle_aggregator is not None and hasattr(chart_tab, "on_new_candle"):
            candle_aggregator.register_callback(chart_tab.on_new_candle)

        # order_filled -> chart trade marker (bridge for buy/sell side detection)
        if order_manager is not None and hasattr(chart_tab, "add_trade_marker"):
            def _on_filled_for_chart(order_no, code, qty, price):
                """Add trade marker to chart on order fill."""
                try:
                    order = order_manager.get_order(order_no)
                    from kiwoom_trader.core.models import OrderSide
                    side = "BUY" if order and order.side == OrderSide.BUY else "SELL"
                    chart_tab.add_trade_marker(code, -1, price, side)
                except Exception:
                    pass  # Fire-and-forget

            order_manager.order_filled.connect(_on_filled_for_chart)

        # --- Wire Log panel ---
        # Add loguru sink that calls dashboard.append_log for real-time display
        if hasattr(dashboard, "append_log"):
            logger.add(
                dashboard.append_log,
                format="{time:HH:mm:ss} | {level} | {message}",
                level="INFO",
            )

        # --- Wire Notifier to strategy/risk signals ---
        # (Strategy signals are routed through StrategyManager._execute_signal,
        #  risk events through RiskManager. Notifier receives via order_filled above.)

        # === Phase 5: Backtest Wiring ===
        if _HAS_BACKTEST and _HAS_STRATEGY:
            from PyQt5.QtWidgets import QProgressDialog, QMessageBox

            def _on_backtest_requested(code, start_date, end_date, capital):
                """Handle backtest request from StrategyTab."""
                # Build configs
                cost_config = settings.backtest_config
                risk_config = settings.risk_config
                strategy_configs = settings._config.get("strategies", [])

                # Create engine
                engine = BacktestEngine(
                    strategy_configs=strategy_configs,
                    risk_config=risk_config,
                    cost_config=cost_config,
                    initial_capital=capital,
                )

                # Create data source
                data_source = KiwoomDataSource(api, tr_queue)

                # Create worker
                worker = BacktestWorker(
                    data_source=data_source,
                    engine=engine,
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                )

                # Progress dialog
                progress_dlg = QProgressDialog(
                    "Starting backtest...", "Cancel", 0, 100, main_window
                )
                progress_dlg.setWindowTitle("Backtest Running")
                progress_dlg.setMinimumDuration(0)

                def _on_progress(current, total, phase_name):
                    if total > 0:
                        progress_dlg.setMaximum(total)
                        progress_dlg.setValue(current)
                    progress_dlg.setLabelText(f"{phase_name}... ({current}/{total})")

                def _on_finished(result):
                    progress_dlg.close()
                    candles = getattr(result, "_candles", [])
                    dlg = BacktestDialog(result, candles, parent=main_window)
                    dlg.exec_()

                def _on_error(msg):
                    progress_dlg.close()
                    QMessageBox.warning(
                        main_window, "Backtest Error", f"Backtest failed:\n{msg}"
                    )

                worker.progress.connect(_on_progress)
                worker.finished.connect(_on_finished)
                worker.error.connect(_on_error)
                progress_dlg.canceled.connect(worker.terminate)

                # Store ref to prevent GC
                main_window._backtest_worker = worker
                worker.start()

            # Wire callback to StrategyTab
            strategy_tab._on_backtest_requested = _on_backtest_requested
            logger.info("Phase 5 backtest wiring complete")
        else:
            logger.warning(
                "Phase 5 backtest imports unavailable. "
                "Skipping backtest wiring."
            )

        logger.info(
            "Phase 4 components wired: MainWindow, DashboardTab, ChartTab, "
            "StrategyTab, Notifier, signal connections"
        )
    else:
        logger.warning(
            "Phase 4 GUI imports unavailable. "
            "Skipping monitoring/operations wiring."
        )

    # Open login dialog
    api.comm_connect()
    logger.info("Login dialog opened, waiting for user...")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
