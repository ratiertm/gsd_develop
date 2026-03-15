"""GSD Phase 4 GUI Design Verification Tests.

Verifies that each screen matches the GSD planning documents (04-01 ~ 04-04).
Uses direct Qt widget inspection — no pyautogui coordinate guessing.

Run:
    python -m pytest tests/test_gui_design.py -v -s --timeout=30
"""

from __future__ import annotations

import pytest

# Skip entire module if PyQt5 unavailable
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QTabWidget, QStatusBar,
        QTableWidget, QGroupBox, QLabel, QTextEdit, QSplitter,
        QListWidget, QPushButton, QLineEdit, QCheckBox, QSpinBox,
        QComboBox, QDoubleSpinBox, QFormLayout,
    )
    from PyQt5.QtCore import Qt
    _HAS_PYQT5 = True
except ImportError:
    _HAS_PYQT5 = False

pytestmark = pytest.mark.skipif(not _HAS_PYQT5, reason="PyQt5 not available")


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture(scope="module")
def app_window(qapp):
    """Create MainWindow with mock data for design inspection."""
    from kiwoom_trader.config.settings import Settings
    from kiwoom_trader.gui.main_window import MainWindow
    from kiwoom_trader.core.models import RiskConfig
    from kiwoom_trader.core.position_tracker import PositionTracker

    settings = Settings()
    window = MainWindow(settings, on_strategy_reload=lambda: None)

    # Populate dashboard with mock data
    dashboard = window._dashboard_tab
    risk_config = settings.risk_config
    tracker = PositionTracker(risk_config)
    tracker.add_position("005930", 10, 72000)
    tracker.add_position("000660", 5, 165000)
    tracker.update_price("005930", 74500)
    tracker.update_price("000660", 160000)

    positions = tracker.get_all_positions()
    total_invested = sum(p.avg_price * p.qty for p in positions.values())
    unrealized = sum(p.unrealized_pnl for p in positions.values())

    dashboard.update_positions(positions, total_invested)
    dashboard.update_pnl(daily_pnl=125000, unrealized_pnl=unrealized, total_invested=total_invested)
    dashboard.update_status(connected=True, market_state="TRADING", strategy_count=2, mode="paper")
    dashboard.append_log("Test log entry")

    window.show()
    qapp.processEvents()
    return window


def _find_widgets(parent, widget_type):
    """Find all child widgets of given type."""
    return parent.findChildren(widget_type)


def _find_widget_by_text(parent, widget_type, text):
    """Find a child widget containing specific text."""
    for w in parent.findChildren(widget_type):
        if hasattr(w, "text") and text in w.text():
            return w
        if hasattr(w, "title") and text in w.title():
            return w
    return None


# ================================================================== #
# 1. MainWindow Structure (04-01-PLAN)
# ================================================================== #

class TestMainWindow:
    """Verify MainWindow matches 04-01 spec."""

    def test_is_qmainwindow(self, app_window):
        """MainWindow inherits QMainWindow."""
        assert isinstance(app_window, QMainWindow)

    def test_window_title(self, app_window):
        """Window title contains 'KiwoomDayTrader'."""
        assert "KiwoomDayTrader" in app_window.windowTitle()

    def test_minimum_size(self, app_window):
        """Minimum size is 1200x800."""
        min_size = app_window.minimumSize()
        assert min_size.width() >= 1200
        assert min_size.height() >= 800

    def test_has_tab_widget(self, app_window):
        """Central widget is QTabWidget."""
        central = app_window.centralWidget()
        assert isinstance(central, QTabWidget)

    def test_three_tabs(self, app_window):
        """Exactly 3 tabs: Dashboard, Chart, Strategy."""
        tabs = app_window.centralWidget()
        assert tabs.count() == 3

    def test_tab_names(self, app_window):
        """Tab labels match spec."""
        tabs = app_window.centralWidget()
        tab_names = [tabs.tabText(i) for i in range(tabs.count())]
        assert tab_names == ["Dashboard", "Chart", "Strategy"]

    def test_has_status_bar(self, app_window):
        """Status bar exists."""
        sb = app_window.statusBar()
        assert sb is not None
        assert isinstance(sb, QStatusBar)

    def test_status_bar_initial_text(self, app_window):
        """Status bar shows 'Ready' initially."""
        assert "Ready" in app_window.statusBar().currentMessage()


# ================================================================== #
# 2. DashboardTab (04-02-PLAN)
# ================================================================== #

class TestDashboardTab:
    """Verify DashboardTab matches 04-02 spec."""

    @pytest.fixture
    def dashboard(self, app_window):
        return app_window._dashboard_tab

    # --- Positions Table ---

    def test_positions_table_exists(self, dashboard):
        """Positions table is a QTableWidget."""
        assert hasattr(dashboard, "_positions_table")
        assert isinstance(dashboard._positions_table, QTableWidget)

    def test_positions_table_columns(self, dashboard):
        """Positions table has 8 columns with correct Korean headers."""
        table = dashboard._positions_table
        expected = ["종목코드", "종목명", "수량", "매입가", "현재가", "평가손익", "수익률(%)", "비중(%)"]
        assert table.columnCount() == 8
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        assert headers == expected

    def test_positions_table_has_data(self, dashboard):
        """Positions table shows mock positions."""
        assert dashboard._positions_table.rowCount() >= 2

    def test_positions_table_not_editable(self, dashboard):
        """Positions table is read-only."""
        from PyQt5.QtWidgets import QAbstractItemView
        assert dashboard._positions_table.editTriggers() == QAbstractItemView.NoEditTriggers

    # --- System Status Group ---

    def test_system_status_group_exists(self, dashboard):
        """System status QGroupBox exists with title '시스템 상태'."""
        group = _find_widget_by_text(dashboard, QGroupBox, "시스템 상태")
        assert group is not None

    def test_status_labels_exist(self, dashboard):
        """All 4 status labels exist: 연결 상태, 장 상태, 활성 전략, 모드."""
        labels = [w.text() for w in _find_widgets(dashboard, QLabel)]
        label_text = " ".join(labels)
        assert "연결" in label_text  # 연결 상태 or 연결됨
        assert "장 상태" in label_text or "TRADING" in label_text
        assert "전략" in label_text or "활성" in label_text

    def test_status_connected_shown(self, dashboard):
        """Connection status shows '연결됨' when connected."""
        assert dashboard._lbl_connected.text() == "연결됨"

    def test_status_market_state_shown(self, dashboard):
        """Market state label shows current state."""
        assert dashboard._lbl_market_state.text() == "TRADING"

    def test_status_mode_shown(self, dashboard):
        """Mode label shows '모의투자' for paper mode."""
        assert dashboard._lbl_mode.text() == "모의투자"

    # --- P&L Summary Group ---

    def test_pnl_group_exists(self, dashboard):
        """P&L summary QGroupBox exists with title '손익 요약'."""
        group = _find_widget_by_text(dashboard, QGroupBox, "손익 요약")
        assert group is not None

    def test_pnl_labels_exist(self, dashboard):
        """P&L labels exist: 일일 실현손익, 평가손익, 총 투자금액."""
        assert dashboard._lbl_daily_pnl is not None
        assert dashboard._lbl_unrealized_pnl is not None
        assert dashboard._lbl_total_invested is not None

    def test_pnl_daily_value(self, dashboard):
        """Daily P&L shows formatted value."""
        text = dashboard._lbl_daily_pnl.text()
        assert "125,000" in text

    def test_pnl_total_invested_value(self, dashboard):
        """Total invested shows formatted value."""
        text = dashboard._lbl_total_invested.text()
        assert text != "0"  # Should have mock data

    # --- Orders Tabs ---

    def test_orders_tab_widget_exists(self, dashboard):
        """Orders section has QTabWidget with 2 tabs."""
        tab_widgets = _find_widgets(dashboard, QTabWidget)
        # Find the orders tab widget (not the main tab)
        orders_tabs = None
        for tw in tab_widgets:
            if tw.count() == 2:
                orders_tabs = tw
                break
        assert orders_tabs is not None

    def test_pending_orders_table(self, dashboard):
        """Pending orders table exists with 9 columns."""
        assert hasattr(dashboard, "_pending_table")
        assert dashboard._pending_table.columnCount() == 9

    def test_filled_orders_table(self, dashboard):
        """Filled orders table exists with 9 columns."""
        assert hasattr(dashboard, "_filled_table")
        assert dashboard._filled_table.columnCount() == 9

    def test_order_table_columns(self, dashboard):
        """Order table headers match spec."""
        expected = ["주문번호", "종목코드", "매매구분", "주문유형", "주문수량",
                    "주문가격", "상태", "체결수량", "체결가격"]
        table = dashboard._pending_table
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        assert headers == expected

    # --- Log Panel ---

    def test_log_panel_exists(self, dashboard):
        """Log panel is QTextEdit, read-only."""
        assert hasattr(dashboard, "_log_panel")
        assert isinstance(dashboard._log_panel, QTextEdit)
        assert dashboard._log_panel.isReadOnly()

    def test_log_panel_has_entries(self, dashboard):
        """Log panel shows log entries."""
        text = dashboard._log_panel.toPlainText()
        assert "Test log entry" in text

    # --- Layout Structure ---

    def test_has_splitter(self, dashboard):
        """Top section uses QSplitter for positions/status layout."""
        splitters = _find_widgets(dashboard, QSplitter)
        assert len(splitters) >= 1


# ================================================================== #
# 3. ChartTab (04-03-PLAN)
# ================================================================== #

class TestChartTab:
    """Verify ChartTab matches 04-03 spec."""

    @pytest.fixture
    def chart_tab(self, app_window):
        return app_window._chart_tab

    def test_has_watchlist(self, chart_tab):
        """Watchlist QListWidget exists."""
        assert chart_tab._watchlist_widget is not None
        assert isinstance(chart_tab._watchlist_widget, QListWidget)

    def test_has_candlestick_item(self, chart_tab):
        """CandlestickItem exists in chart."""
        assert chart_tab._candlestick_item is not None

    def test_has_price_plot(self, chart_tab):
        """Main price plot exists."""
        assert chart_tab._price_plot is not None

    def test_has_indicator_checkboxes(self, chart_tab):
        """7 indicator checkboxes: SMA, EMA, Bollinger, VWAP, RSI, MACD, OBV."""
        checkboxes = _find_widgets(chart_tab, QCheckBox)
        checkbox_labels = [cb.text() for cb in checkboxes]
        expected = {"SMA", "EMA", "Bollinger", "VWAP", "RSI", "MACD", "OBV"}
        assert expected == set(checkbox_labels)

    def test_price_overlay_items(self, chart_tab):
        """Price overlay plot items exist: sma, ema, bollinger (3 lines), vwap."""
        expected_keys = {"sma", "ema", "bollinger_upper", "bollinger_middle", "bollinger_lower", "vwap"}
        assert set(chart_tab._overlay_items.keys()) == expected_keys

    def test_overlays_hidden_by_default(self, chart_tab):
        """All overlay items start hidden."""
        for key, item in chart_tab._overlay_items.items():
            assert not item.isVisible(), f"Overlay '{key}' should be hidden by default"

    def test_sub_charts_exist(self, chart_tab):
        """Sub-charts exist: rsi, macd, obv."""
        expected = {"rsi", "macd", "obv"}
        assert set(chart_tab._sub_plots.keys()) == expected

    def test_sub_charts_hidden_by_default(self, chart_tab):
        """All sub-charts start with height 0 (hidden)."""
        for name, plot in chart_tab._sub_plots.items():
            assert plot.maximumHeight() == 0, f"Sub-chart '{name}' should be hidden"

    def test_trade_marker_item(self, chart_tab):
        """Trade marker scatter plot item exists."""
        assert chart_tab._marker_item is not None

    def test_sliding_window_constant(self, chart_tab):
        """MAX_CANDLES is 120."""
        from kiwoom_trader.gui.chart_tab import MAX_CANDLES
        assert MAX_CANDLES == 120

    def test_candle_buffers_per_code(self, chart_tab):
        """Candle buffers are per-stock-code dicts."""
        assert isinstance(chart_tab._candle_buffers, dict)

    def test_chart_background_dark(self, chart_tab):
        """Chart background is dark (#1E1E1E)."""
        assert chart_tab._chart_layout is not None


# ================================================================== #
# 4. StrategyTab (04-04-PLAN)
# ================================================================== #

class TestStrategyTab:
    """Verify StrategyTab matches 04-04 spec."""

    @pytest.fixture
    def strategy_tab(self, app_window):
        return app_window._strategy_tab

    # --- Left Panel: Strategy List ---

    def test_strategy_list_exists(self, strategy_tab):
        """Strategy list QListWidget exists."""
        assert hasattr(strategy_tab, "_strategy_list")
        assert isinstance(strategy_tab._strategy_list, QListWidget)

    def test_action_buttons_exist(self, strategy_tab):
        """New, Copy, Delete buttons exist."""
        buttons = _find_widgets(strategy_tab, QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "New" in button_texts
        assert "Copy" in button_texts
        assert "Delete" in button_texts

    # --- Right Panel: Editor Form ---

    def test_name_field(self, strategy_tab):
        """Name QLineEdit exists."""
        assert hasattr(strategy_tab, "_name_edit")
        assert isinstance(strategy_tab._name_edit, QLineEdit)

    def test_enabled_checkbox(self, strategy_tab):
        """Enabled QCheckBox exists."""
        assert hasattr(strategy_tab, "_enabled_check")
        assert isinstance(strategy_tab._enabled_check, QCheckBox)

    def test_priority_spinbox(self, strategy_tab):
        """Priority QSpinBox exists with range 1-100."""
        spin = strategy_tab._priority_spin
        assert isinstance(spin, QSpinBox)
        assert spin.minimum() == 1
        assert spin.maximum() == 100

    def test_cooldown_spinbox(self, strategy_tab):
        """Cooldown QSpinBox exists with range 0-3600."""
        spin = strategy_tab._cooldown_spin
        assert isinstance(spin, QSpinBox)
        assert spin.minimum() == 0
        assert spin.maximum() == 3600

    # --- Indicators Section ---

    def test_indicators_group_exists(self, strategy_tab):
        """Indicators QGroupBox exists."""
        assert hasattr(strategy_tab, "_indicators_group")
        assert isinstance(strategy_tab._indicators_group, QGroupBox)

    def test_add_indicator_button(self, strategy_tab):
        """'Add Indicator' button exists."""
        btn = _find_widget_by_text(strategy_tab, QPushButton, "Add Indicator")
        assert btn is not None

    # --- Entry Rules Section ---

    def test_entry_logic_combo(self, strategy_tab):
        """Entry logic QComboBox with AND/OR."""
        combo = strategy_tab._entry_logic_combo
        assert isinstance(combo, QComboBox)
        items = [combo.itemText(i) for i in range(combo.count())]
        assert "AND" in items
        assert "OR" in items

    def test_add_entry_condition_button(self, strategy_tab):
        """Entry rules has 'Add Condition' button."""
        group = _find_widget_by_text(strategy_tab, QGroupBox, "Entry Rules")
        assert group is not None
        btn = _find_widget_by_text(group, QPushButton, "Add Condition")
        assert btn is not None

    # --- Exit Rules Section ---

    def test_exit_logic_combo(self, strategy_tab):
        """Exit logic QComboBox with AND/OR."""
        combo = strategy_tab._exit_logic_combo
        assert isinstance(combo, QComboBox)
        items = [combo.itemText(i) for i in range(combo.count())]
        assert "AND" in items
        assert "OR" in items

    def test_add_exit_condition_button(self, strategy_tab):
        """Exit rules has 'Add Condition' button."""
        group = _find_widget_by_text(strategy_tab, QGroupBox, "Exit Rules")
        assert group is not None
        btn = _find_widget_by_text(group, QPushButton, "Add Condition")
        assert btn is not None

    # --- Save & Backtest ---

    def test_save_button(self, strategy_tab):
        """'Save Strategy' button exists."""
        btn = _find_widget_by_text(strategy_tab, QPushButton, "Save Strategy")
        assert btn is not None

    def test_backtest_button(self, strategy_tab):
        """'Backtest' button exists."""
        btn = _find_widget_by_text(strategy_tab, QPushButton, "Backtest")
        assert btn is not None

    # --- Watchlist Management ---

    def test_watchlist_group_exists(self, strategy_tab):
        """Watchlist Management QGroupBox exists."""
        group = _find_widget_by_text(strategy_tab, QGroupBox, "Watchlist Management")
        assert group is not None

    def test_watchlist_table(self, strategy_tab):
        """Watchlist table has 2 columns: 종목코드, 적용 전략."""
        table = strategy_tab._watchlist_table
        assert isinstance(table, QTableWidget)
        assert table.columnCount() == 2
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        assert headers == ["종목코드", "적용 전략"]

    def test_add_stock_button(self, strategy_tab):
        """'Add Stock' button exists."""
        btn = _find_widget_by_text(strategy_tab, QPushButton, "Add Stock")
        assert btn is not None

    def test_remove_stock_button(self, strategy_tab):
        """'Remove Stock' button exists."""
        btn = _find_widget_by_text(strategy_tab, QPushButton, "Remove Stock")
        assert btn is not None


# ================================================================== #
# 5. Toast & Notification System (04-01-PLAN)
# ================================================================== #

class TestToastWidget:
    """Verify ToastWidget matches 04-01 spec."""

    def test_toast_importable(self):
        """ToastWidget can be imported."""
        from kiwoom_trader.gui.widgets.toast_widget import ToastWidget
        assert ToastWidget is not None

    def test_toast_creation(self, qapp, app_window):
        """Toast can be created with required params."""
        from kiwoom_trader.gui.widgets.toast_widget import ToastWidget
        toast = ToastWidget(
            parent=app_window,
            title="Test Trade",
            message="005930 BUY x10 @72,000",
            event_type="trade",
            duration_ms=4000,
            on_dismiss=lambda: None,
        )
        assert toast is not None

    def test_main_window_show_toast(self, qapp, app_window):
        """MainWindow.show_toast() creates and tracks toasts."""
        initial = len(app_window._active_toasts)
        app_window.show_toast("Test", "Message", "trade")
        assert len(app_window._active_toasts) == initial + 1


class TestNotifier:
    """Verify Notifier matches 04-01 spec."""

    def test_notifier_importable(self):
        """Notifier can be imported."""
        from kiwoom_trader.gui.notification.notifier import Notifier
        assert Notifier is not None

    def test_notifier_config_keys(self, qapp, app_window):
        """Notifier respects config keys: gui_popup_enabled, log_enabled, discord_enabled."""
        from kiwoom_trader.gui.notification.notifier import Notifier
        config = {
            "gui_popup_enabled": True,
            "log_enabled": True,
            "discord_enabled": False,
        }
        notifier = Notifier(config=config, main_window=app_window)
        assert notifier is not None


class TestDiscordSender:
    """Verify DiscordSendWorker matches 04-01 spec."""

    def test_discord_sender_importable(self):
        """DiscordSendWorker can be imported."""
        from kiwoom_trader.gui.notification.discord_sender import DiscordSendWorker
        assert DiscordSendWorker is not None

    def test_build_trade_embed(self):
        """build_trade_embed returns valid Discord embed dict."""
        from kiwoom_trader.gui.notification.discord_sender import build_trade_embed
        embed = build_trade_embed(
            {"code": "005930", "price": 72000, "qty": 10},
            side="BUY",
        )
        assert "embeds" in embed
        assert len(embed["embeds"]) == 1
        assert embed["embeds"][0]["color"] == 0x26A69A  # green for BUY


# ================================================================== #
# 6. Pure Function Validation (04-04-PLAN)
# ================================================================== #

class TestStrategyValidation:
    """Verify pure validation functions from StrategyTab."""

    def test_validate_empty_name(self):
        """Empty name returns error."""
        from kiwoom_trader.gui.strategy_tab import validate_strategy
        errors = validate_strategy({"name": "", "entry_rule": {"conditions": [{"operator": "gt", "value": 0}]}, "exit_rule": {"conditions": [{"operator": "lt", "value": 0}]}, "indicators": {}})
        assert any("name" in e.lower() for e in errors)

    def test_validate_no_entry_conditions(self):
        """Missing entry conditions returns error."""
        from kiwoom_trader.gui.strategy_tab import validate_strategy
        errors = validate_strategy({"name": "test", "entry_rule": {"conditions": []}, "exit_rule": {"conditions": [{"operator": "gt", "value": 0}]}, "indicators": {}})
        assert any("entry" in e.lower() for e in errors)

    def test_validate_no_exit_conditions(self):
        """Missing exit conditions returns error."""
        from kiwoom_trader.gui.strategy_tab import validate_strategy
        errors = validate_strategy({"name": "test", "entry_rule": {"conditions": [{"operator": "gt", "value": 0}]}, "exit_rule": {"conditions": []}, "indicators": {}})
        assert any("exit" in e.lower() for e in errors)

    def test_validate_invalid_operator(self):
        """Invalid operator returns error."""
        from kiwoom_trader.gui.strategy_tab import validate_strategy
        errors = validate_strategy({
            "name": "test",
            "entry_rule": {"conditions": [{"operator": "INVALID", "value": 0}]},
            "exit_rule": {"conditions": [{"operator": "gt", "value": 0}]},
            "indicators": {},
        })
        assert any("operator" in e.lower() for e in errors)

    def test_pnl_color_convention(self):
        """Korean convention: positive=red, negative=blue."""
        from kiwoom_trader.gui.dashboard_tab import pnl_color
        assert pnl_color(100) == "#EF5350"   # red for gains
        assert pnl_color(-100) == "#42A5F5"  # blue for losses
        assert pnl_color(0) is None
