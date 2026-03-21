"""Application entry point for KiwoomDayTrader.

Wires all core components together and starts the Qt event loop:
- Phase 1: KiwoomAPI, EventHandlerRegistry, TRRequestQueue, SessionManager, RealDataManager
- Phase 2: OrderManager, RiskManager, PositionTracker, MarketHoursManager
- Phase 3: CandleAggregator, ConditionEngine, StrategyManager, PaperTrader
- Phase 4: MainWindow (Dashboard, Chart, Strategy tabs), Notifier, signal wiring

Replay mode (--replay):
  python -m kiwoom_trader.main --replay data/realtime_20260320.db
  Loads historical tick data into UI without Kiwoom API login.
"""

import argparse
import os
import sys

from loguru import logger

from kiwoom_trader.api import (
    EventHandlerRegistry,
    KiwoomAPI,
    RealDataManager,
    SessionManager,
    TRRequestQueue,
)
from kiwoom_trader.api.balance_query import BalanceQuery
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

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="KiwoomDayTrader")
    parser.add_argument("--sim", action="store_true", help="Simulation mode (no Kiwoom login, use Dashboard to start)")
    args, remaining = parser.parse_known_args()

    setup_logging()

    replay_mode = args.sim
    if replay_mode:
        logger.info("=== KiwoomDayTrader SIMULATION MODE ===")
    else:
        logger.info("=== KiwoomDayTrader starting ===")

    app = QApplication(remaining or sys.argv[:1])
    settings = Settings()

    # === Phase 1: API Foundation ===
    api = None
    event_registry = None
    tr_queue = None
    session_manager = None
    real_data_manager = None

    if not replay_mode:
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
        def _on_session_restored():
            """Reload balance on reconnect to sync PositionTracker with broker."""
            logger.info("Session restored")
            account_no = os.environ.get("KIWOOM_ACCOUNT_NO", "")
            if account_no:
                _select_account(account_no)

        session_manager.session_restored.connect(_on_session_restored)
        session_manager.session_lost.connect(
            lambda: logger.warning("Session lost")
        )
    else:
        logger.info("Replay mode: skipping Phase 1 (API)")

    # === Phase 2: Order Execution & Risk Management ===
    position_tracker = None
    if replay_mode:
        risk_manager = None
        order_manager = None
        market_hours = None
        logger.info("Replay mode: skipping Phase 2 (Order/Risk)")
    elif _HAS_CORE and OrderManager is not None:
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
    paper_trader = None
    market_state_timer = None  # Keep ref to prevent GC
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

        # Wire: RealDataManager tick -> CandleAggregator (live mode only)
        if real_data_manager is not None:
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
        dashboard._settings = settings  # for stock name lookup + watchlist
        dashboard._on_strategy_reload = _reload_strategies  # hot-swap on watchlist change
        chart_tab = main_window._chart_tab
        strategy_tab = main_window._strategy_tab

        # Load stock names into shared settings cache
        if replay_mode:
            from pathlib import Path
            import sqlite3
            data_dir = Path(__file__).resolve().parent.parent / "data"
            for db_file in sorted(data_dir.glob("realtime_*.db"), reverse=True):
                try:
                    conn = sqlite3.connect(str(db_file))
                    rows = conn.execute(
                        "SELECT DISTINCT code, name FROM 체결 WHERE name != ''"
                    ).fetchall()
                    conn.close()
                    for code, name in rows:
                        if code not in settings.stock_names and name:
                            settings.stock_names[code] = name
                except Exception:
                    pass
            logger.info(f"Stock names loaded from DB: {len(settings.stock_names)} codes")
            # Refresh UI with names
            if hasattr(chart_tab, 'refresh_watchlist_names'):
                chart_tab.refresh_watchlist_names()
            if hasattr(dashboard, 'load_watchlist'):
                dashboard.load_watchlist()
        elif api is not None:
            # Live mode: resolver that queries API and caches
            def _resolve_name(code):
                if code not in settings.stock_names:
                    name = api.get_master_code_name(code)
                    if name:
                        settings.stock_names[code] = name
                return settings.stock_names.get(code, "")
            strategy_tab._stock_name_resolver = _resolve_name

        # Create Notifier with GUI toast support
        notifier = Notifier(
            config=settings.notification_config,
            main_window=main_window,
        )

        # --- Wire mode toggle ---
        def _on_mode_change(new_mode: str):
            """Switch between paper and live mode, updating StrategyManager and config."""
            nonlocal paper_trader

            # 1. Update config and persist
            settings._config["mode"] = new_mode
            settings.save()

            if strategy_manager is None:
                logger.info(f"모드 전환: {new_mode} (StrategyManager 없음)")
                return

            # 2. Update StrategyManager mode
            strategy_manager._mode = new_mode

            # 3. PaperTrader lifecycle
            if new_mode == "paper":
                # Create PaperTrader if not exists
                if strategy_manager.paper_trader is None and _HAS_STRATEGY:
                    strategy_cfg = settings.strategy_config
                    paper_trader = PaperTrader(
                        csv_path="logs/trades.csv",
                        initial_capital=strategy_cfg.get(
                            "total_capital", 10_000_000
                        ),
                        max_symbol_weight_pct=settings.risk_config.max_symbol_weight_pct,
                    )
                    strategy_manager.paper_trader = paper_trader
                    logger.info("PaperTrader 생성 및 연결")
            else:
                # Live mode: detach PaperTrader (keep instance for later reuse)
                if strategy_manager.paper_trader is not None:
                    logger.info("PaperTrader 비활성화 (실전모드)")

            # 4. 잔고 재조회 (모드 전환 시 계좌 상태 동기화)
            account_no = os.environ.get("KIWOOM_ACCOUNT_NO", "")
            if account_no:
                _select_account(account_no)

            logger.info(f"모드 전환: {new_mode}")

        dashboard._on_mode_change = _on_mode_change

        # --- Wire simulation button ---
        def _on_sim_requested(date_str, interval, speed, day_strategy=None):
            """Handle simulation request from Dashboard button."""
            from pathlib import Path
            data_dir = Path(__file__).resolve().parent.parent / "data"
            replay_db = data_dir / f"realtime_{date_str}.db"
            if not replay_db.exists():
                from PyQt5.QtWidgets import QMessageBox
                available = [f.stem.replace("realtime_", "") for f in data_dir.glob("realtime_*.db")]
                QMessageBox.warning(
                    main_window, "데이터 없음",
                    f"해당 날짜의 데이터가 없습니다:\n{replay_db}\n\n사용 가능한 날짜: {', '.join(available)}",
                )
                return

            # Find best prev-day DB
            prev_day_db = None
            for candidate in sorted(data_dir.glob("minute_1m_*.db"), reverse=True):
                if candidate.name < f"minute_1m_{date_str}.db":
                    prev_day_db = candidate
                    break
            if not prev_day_db:
                same = data_dir / f"minute_1m_{date_str}.db"
                if same.exists():
                    prev_day_db = same

            strat_label = day_strategy or "config"
            dashboard.update_status(
                connected=True, market_state="SIMULATION",
                strategy_count=len(strategy_manager.strategies) if strategy_manager else 0,
                mode="replay",
            )
            main_window._status_bar.showMessage(
                f"SIMULATION | {date_str} | {interval}분봉 | {strat_label}"
            )

            _launch_simulation(
                str(replay_db), str(prev_day_db) if prev_day_db else None,
                interval, speed, slippage=0,
                title=f"시뮬레이션: {date_str} ({strat_label})",
                day_strategy=day_strategy,
            )

        dashboard._on_sim_requested = _on_sim_requested

        # --- Wire manual order panel ---
        def _on_manual_order(code, side, qty, price):
            """Handle manual order from Dashboard panel."""
            if order_manager is None:
                logger.warning("OrderManager not available for manual order")
                return
            from kiwoom_trader.core.models import OrderSide
            from kiwoom_trader.config.constants import HogaGb
            order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
            hoga = HogaGb.MARKET if price == 0 else HogaGb.LIMIT
            order_manager.submit_order(code, order_side, qty, price, hoga)
            logger.info(f"수동 주문: {side} {code} x{qty} @{price:,}")

        dashboard._on_order_requested = _on_manual_order

        # --- Wire Dashboard signals ---

        # 1. QTimer (1s interval) to poll PositionTracker and update dashboard
        if position_tracker is not None:
            dashboard_timer = QTimer()

            def _update_dashboard():
                """Poll position/P&L data and push to dashboard."""
                positions = position_tracker.get_all_positions()
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
            main_window._dashboard_timer = dashboard_timer  # prevent GC

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

        # StrategyManager signal -> chart signal markers
        if strategy_manager is not None and hasattr(chart_tab, "add_signal_marker"):
            _original_on_candle = strategy_manager.on_candle_complete

            def _on_candle_with_chart_signals(code, candle):
                signals = _original_on_candle(code, candle)
                for sig in signals:
                    chart_tab.add_signal_marker(code, sig)
                return signals

            # Replace the callback in CandleAggregator
            if candle_aggregator is not None:
                candle_aggregator._callbacks = [
                    cb for cb in candle_aggregator._callbacks
                    if cb != _original_on_candle
                ]
                candle_aggregator.register_callback(_on_candle_with_chart_signals)

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
                enqueue=True,  # Thread-safe: queue messages for main thread
            )

        # --- Wire Notifier to risk signals ---
        if risk_manager is not None:
            risk_manager.trigger_stop_loss.connect(
                lambda code, price: notifier.notify(
                    "risk", f"손절 발동: {code}",
                    f"{code} @ {price:,} — 포지션 청산",
                    {"code": code, "price": price, "event": "STOP_LOSS"},
                )
            )
            risk_manager.trigger_take_profit.connect(
                lambda code, price: notifier.notify(
                    "risk", f"익절 발동: {code}",
                    f"{code} @ {price:,} — 포지션 청산",
                    {"code": code, "price": price, "event": "TAKE_PROFIT"},
                )
            )
            risk_manager.trigger_trailing_stop.connect(
                lambda code, price: notifier.notify(
                    "risk", f"트레일링 스탑: {code}",
                    f"{code} @ {price:,} — 포지션 청산",
                    {"code": code, "price": price, "event": "TRAILING_STOP"},
                )
            )
            risk_manager.daily_loss_limit_hit.connect(
                lambda: notifier.notify(
                    "error", "일일 손실 한도 도달",
                    "전 포지션 청산 — 금일 매수 중단",
                    {"event": "DAILY_LOSS_LIMIT"},
                )
            )
            risk_manager.position_liquidated.connect(
                lambda code: notifier.notify(
                    "risk", f"포지션 청산: {code}",
                    f"{code} — 일일 손실 한도 청산",
                    {"code": code, "event": "POSITION_LIQUIDATED"},
                )
            )

        # === Phase 5: Backtest Wiring ===
        if _HAS_BACKTEST and _HAS_STRATEGY:
            from PyQt5.QtWidgets import QProgressDialog, QMessageBox

            def _on_backtest_requested(code, start_date, end_date, capital):
                """Handle backtest request from StrategyTab."""
                # Build configs
                cost_config = settings.backtest_config
                risk_config = settings.risk_config
                strategy_configs = settings.strategy_config

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

    # === Phase 6: Login & Connection ===

    # Balance load callback (shared by initial login and account switch)
    def _on_balance_loaded(positions_list):
        """잔고 조회 완료 후 PositionTracker에 반영."""
        if position_tracker is None:
            return
        position_tracker.clear_all()
        for pos in positions_list:
            position_tracker.update_from_chejan(
                code=pos["code"],
                holding_qty=pos["qty"],
                buy_price=pos["buy_price"],
                current_price=pos["current_price"],
            )
        logger.info(
            f"PositionTracker 동기화 완료: {len(positions_list)}종목"
        )

    def _select_account(account_no: str):
        """Update the active account and reload balance."""
        if not account_no or not account_no.strip():
            logger.warning("계좌번호가 비어있습니다. 계좌 전환 무시.")
            return
        os.environ["KIWOOM_ACCOUNT_NO"] = account_no
        if order_manager is not None:
            order_manager._account_no = account_no

        # 잔고 재조회
        bq = BalanceQuery(api, tr_queue, event_registry)
        bq.query(account_no, on_complete=_on_balance_loaded)
        # GC 방지
        if _HAS_GUI and main_window is not None:
            main_window._balance_query = bq

        logger.info(f"활성 계좌 변경: {account_no}")

    def _on_login_success(err_code):
        """Handle login result: log account info and start monitoring."""
        if err_code != 0:
            logger.error(f"Login failed (err_code={err_code})")
            return

        # Query account info from API
        accounts = api.get_login_info("ACCNO")
        user_id = api.get_login_info("USER_ID")
        user_name = api.get_login_info("USER_NAME")
        server_type = api.get_login_info("GetServerGubun")

        server_label = "모의투자" if server_type == "1" else "실거래"
        account_list = [a for a in accounts.split(";") if a.strip()]

        logger.info(f"=== 로그인 성공 ===")
        logger.info(f"사용자: {user_name} ({user_id})")
        logger.info(f"서버: {server_label}")
        logger.info(f"계좌: {account_list}")

        # Auto-select first stock account (suffix 31) or first available
        selected = account_list[0] if account_list else ""
        for acc in account_list:
            if acc.endswith("31"):
                selected = acc
                break
        _select_account(selected)

        # Populate dashboard account selector
        if _HAS_GUI and hasattr(dashboard, "set_accounts"):
            dashboard.set_accounts(account_list, user_name, server_label)
            # Wire account change from combo box
            dashboard._cmb_account.currentIndexChanged.connect(
                lambda _: _select_account(dashboard.get_selected_account())
            )

        # Update status bar
        if _HAS_GUI and main_window is not None:
            main_window._status_bar.showMessage(
                f"{user_name} | {server_label} | {selected}"
            )

        # === Phase 7: Register watchlist for real-time data ===
        watchlist = settings._config.get("watchlist", [])
        # Also gather codes from watchlist_strategies mapping
        ws_codes = list(settings._config.get("watchlist_strategies", {}).keys())
        all_codes = list(dict.fromkeys(watchlist + ws_codes))  # dedupe, preserve order

        if all_codes:
            fid_config = settings._config.get("real_data_fids", {})
            stock_fids = fid_config.get(
                "stock_execution",
                "10;11;12;13;15;16;17;18;20;25;27;28",
            )
            code_str = ";".join(all_codes)
            real_data_manager.subscribe(code_str, stock_fids)
            logger.info(f"실시간 시세 등록: {all_codes}")
        else:
            logger.warning("watchlist가 비어있어 실시간 시세 등록 건너뜀")

        # Start session monitoring
        session_manager.start_monitoring()

    # === Shared simulation launcher (used by CLI --replay and Dashboard button) ===
    def _launch_simulation(replay_db_path, prev_day_path, interval, speed, slippage=0, title="Replay", day_strategy=None):
        """Launch a replay simulation with thread-safe UI updates."""
        from pathlib import Path
        from PyQt5.QtCore import pyqtSignal, QObject
        from PyQt5.QtWidgets import QProgressDialog
        from kiwoom_trader.backtest.replay_engine import ReplayEngine
        from kiwoom_trader.backtest.cost_model import CostConfig
        from kiwoom_trader.backtest.backtest_worker import BacktestWorker

        replay_db = Path(replay_db_path)

        # Build day trading strategies if requested
        day_strats = []
        if day_strategy:
            from kiwoom_trader.core.day_strategies import (
                ORBStrategy, VWAPBounceStrategy, PrevDayBreakoutStrategy,
                GapStrategy, OrderFlowStrategy,
            )
            DAY_MAP = {
                "ORB": ORBStrategy, "VWAP_BOUNCE": VWAPBounceStrategy,
                "PREV_DAY_BRK": PrevDayBreakoutStrategy,
                "GAP_TRADE": GapStrategy, "ORDER_FLOW": OrderFlowStrategy,
            }
            if day_strategy == "ALL":
                day_strats = [cls() for cls in DAY_MAP.values()]
            elif day_strategy in DAY_MAP:
                day_strats = [DAY_MAP[day_strategy]()]

        # When using day strategies, disable config-based strategies to avoid conflict
        strat_config = {**settings.strategy_config, "mode": "replay"}
        if day_strats:
            strat_config["strategies"] = []
            strat_config["watchlist_strategies"] = {}

        # Build engine
        sim_engine = ReplayEngine(
            strategy_configs=strat_config,
            risk_config=settings.risk_config,
            cost_config=CostConfig(slippage_bp=slippage),
            initial_capital=settings._config.get("total_capital", 10_000_000),
            candle_interval=interval,
            day_strategies=day_strats,
        )

        # Thread-safe bridge: worker stores data, main thread polls via QTimer
        class SimWorker(BacktestWorker):
            """QThread for replay — no direct UI calls."""
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.pending_candles = []
                self.pending_signals = []
                self.pending_trades = []
                self.sim_positions = {}
                self.sim_capital = 0.0
                self.sim_initial = 0
                self.sim_last_prices = {}  # code -> last close price

            def run(self):
                try:
                    self.sim_initial = sim_engine._initial_capital
                    self.progress.emit(0, 1, "Loading...")

                    def _on_candle(code, candle):
                        self.pending_candles.append((code, candle))
                        # Deep copy positions to avoid thread issues
                        import copy
                        self.sim_positions = copy.deepcopy(sim_engine._positions)
                        self.sim_capital = sim_engine._capital
                        self.sim_last_prices[code] = candle.close
                        # Check for new trades
                        if len(sim_engine._trades) > len(self.pending_trades):
                            for t in sim_engine._trades[len(self.pending_trades):]:
                                self.pending_trades.append(t)

                    def _on_signal(signal):
                        self.pending_signals.append(signal)

                    result = sim_engine.run(
                        db_path=str(replay_db),
                        prev_day_db=str(prev_day_path) if prev_day_path else None,
                        speed=speed,
                        on_candle=_on_candle,
                        on_signal=_on_signal,
                        on_progress=lambda c, t: self.progress.emit(c, t, "Simulating..."),
                    )
                    compute_all_metrics(result)
                    self.finished.emit(result)
                except Exception as e:
                    self.error.emit(str(e))

        worker = SimWorker(data_source=None, engine=None, code="", start_date="", end_date="")

        # No progress dialog — use status bar + log panel instead
        worker.progress.connect(lambda c, t, p: (
            main_window._status_bar.showMessage(
                f"{title} | {c:,}/{t:,} ticks ({c*100//max(t,1)}%)"
            ) if main_window else None
        ))

        # QTimer polls worker's pending data and pushes to UI (main thread)
        _trade_idx = [0]
        _candle_count = [0]
        poll_timer = QTimer()

        def _poll_worker():
            # Candles → Chart + log
            while worker.pending_candles:
                code, candle = worker.pending_candles.pop(0)
                if hasattr(chart_tab, "on_new_candle"):
                    chart_tab.on_new_candle(code, candle)
                _candle_count[0] += 1
                ts = candle.timestamp.strftime("%H:%M") if hasattr(candle.timestamp, "strftime") else ""
                # Track prev close & volume per code for change display
                prev_c_key = f"_prev_close_{code}"
                prev_v_key = f"_prev_vol_{code}"
                prev_close = getattr(worker, prev_c_key, candle.close)
                prev_vol = getattr(worker, prev_v_key, candle.volume)
                chg = candle.close - prev_close
                chg_str = f"+{chg:,}" if chg >= 0 else f"{chg:,}"
                vol_chg = candle.volume - prev_vol
                vol_chg_str = f"+{vol_chg:,}" if vol_chg >= 0 else f"{vol_chg:,}"
                setattr(worker, prev_c_key, candle.close)
                setattr(worker, prev_v_key, candle.volume)
                if hasattr(dashboard, "append_log"):
                    dashboard.append_log(
                        f"[{ts}] {code} {candle.close:,}({chg_str}) V={candle.volume:,}({vol_chg_str})"
                    )

            # Signals → Chart markers
            while worker.pending_signals:
                sig = worker.pending_signals.pop(0)
                if hasattr(chart_tab, "add_signal_marker"):
                    chart_tab.add_signal_marker(sig.code, sig)
                if hasattr(dashboard, "append_log"):
                    dashboard.append_log(
                        f"{'BUY' if sig.side == 'BUY' else 'SELL'} {sig.code} @{sig.price:,} | {sig.reason}"
                    )

            # Trades → Dashboard
            while _trade_idx[0] < len(worker.pending_trades):
                if hasattr(dashboard, "add_trade_record"):
                    dashboard.add_trade_record(worker.pending_trades[_trade_idx[0]])
                _trade_idx[0] += 1

            # Positions + P&L → Dashboard
            if hasattr(dashboard, "update_sim_positions"):
                dashboard.update_sim_positions(
                    worker.sim_positions, worker.sim_capital, worker.sim_initial,
                    last_prices=worker.sim_last_prices,
                )

        poll_timer.timeout.connect(_poll_worker)
        poll_timer.start(100)  # 100ms polling

        def _on_finished(result):
            poll_timer.stop()
            _poll_worker()  # flush remaining
            main_window._status_bar.showMessage(
                f"{title} 완료 | {result.total_trades}건, 수익률={result.total_return_pct:+.2f}%"
            )
            # Re-enable sim button
            if hasattr(dashboard, "_btn_sim_start"):
                dashboard._btn_sim_start.setEnabled(True)
                dashboard._btn_sim_start.setText("시뮬레이션 시작")
            logger.info(f"시뮬레이션 완료: {result.total_trades}건, 수익률={result.total_return_pct:+.2f}%")
            if _HAS_BACKTEST:
                BacktestDialog(result, [], parent=main_window).exec_()

        def _on_error(msg):
            poll_timer.stop()
            if hasattr(dashboard, "_btn_sim_start"):
                dashboard._btn_sim_start.setEnabled(True)
                dashboard._btn_sim_start.setText("시뮬레이션 시작")
            main_window._status_bar.showMessage(f"시뮬레이션 오류: {msg}")
            logger.error(f"시뮬레이션 오류: {msg}")

        worker.finished.connect(_on_finished)
        worker.error.connect(_on_error)

        # Switch button to "stop" mode while running
        def _stop_sim():
            poll_timer.stop()
            worker.terminate()
            worker.wait(2000)
            logger.info("시뮬레이션 취소됨")
            main_window._status_bar.showMessage(
                "SIMULATION MODE | 날짜를 선택하고 시뮬레이션 시작 버튼을 누르세요"
            )
            dashboard.update_status(
                connected=True, market_state="STANDBY",
                strategy_count=len(strategy_manager.strategies) if strategy_manager else 0,
                mode="replay",
            )
            if hasattr(dashboard, "_btn_sim_start"):
                dashboard._btn_sim_start.setText("시뮬레이션 시작")
                dashboard._btn_sim_start.setStyleSheet(
                    "QPushButton { background-color: #FF9800; color: white; "
                    "font-weight: bold; padding: 6px; border-radius: 4px; }"
                )
                try:
                    dashboard._btn_sim_start.clicked.disconnect()
                except (TypeError, RuntimeError):
                    pass
                dashboard._btn_sim_start.clicked.connect(dashboard._on_sim_start)

        if hasattr(dashboard, "_btn_sim_start"):
            dashboard._btn_sim_start.setText("시뮬레이션 중지")
            dashboard._btn_sim_start.setStyleSheet(
                "QPushButton { background-color: #EF5350; color: white; "
                "font-weight: bold; padding: 6px; border-radius: 4px; }"
            )
            try:
                dashboard._btn_sim_start.clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            dashboard._btn_sim_start.clicked.connect(_stop_sim)

        main_window._sim_worker = worker
        main_window._sim_poll_timer = poll_timer
        worker.start()

    if replay_mode:
        # === Replay Mode: UI only, simulation via Dashboard button ===
        if _HAS_GUI and main_window is not None:
            main_window._status_bar.showMessage(
                "SIMULATION MODE | 날짜를 선택하고 시뮬레이션 시작 버튼을 누르세요"
            )
            dashboard.update_status(
                connected=True, market_state="STANDBY",
                strategy_count=len(strategy_manager.strategies) if strategy_manager else 0,
                mode="replay",
            )
        logger.info("Simulation mode ready — use Dashboard panel to start")
    else:
        # === Live Mode: Kiwoom API login ===
        api.connected.connect(_on_login_success)
        api.comm_connect()
        logger.info("Login dialog opened, waiting for user...")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
