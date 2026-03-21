"""MainWindow with real tabs (Dashboard, Chart, Strategy) and toast notification support."""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from PyQt5.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QStatusBar,
    QVBoxLayout,
)

from kiwoom_trader.config.settings import Settings

# Import real tab widgets with fallback to placeholders
try:
    from kiwoom_trader.gui.dashboard_tab import DashboardTab
except ImportError:
    DashboardTab = None

try:
    from kiwoom_trader.gui.chart_tab import ChartTab
except ImportError:
    ChartTab = None

try:
    from kiwoom_trader.gui.strategy_tab import StrategyTab
except ImportError:
    StrategyTab = None


class MainWindow(QMainWindow):
    """Primary application window with tabbed interface.

    Tabs:
        - Dashboard: positions, orders, P&L, system status
        - Chart: candlestick chart with indicator overlays
        - Strategy: strategy editor, watchlist management

    Args:
        settings: Application Settings instance.
        on_strategy_reload: Optional callback for StrategyManager hot-swap.
    """

    def __init__(
        self,
        settings: Settings,
        on_strategy_reload: Callable | None = None,
    ):
        super().__init__()
        self._settings = settings
        self._active_toasts: list = []
        self._on_strategy_reload = on_strategy_reload
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("KiwoomDayTrader")
        self.setMinimumSize(1200, 800)
        self._apply_dark_theme()

    def _apply_dark_theme(self):
        """Apply cohesive dark trading terminal theme."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1A1A1A;
                color: #E0E0E0;
            }
            QTabWidget::pane {
                border: 1px solid #3A3A3A;
            }
            QTabBar::tab {
                background-color: #2A2A2A;
                color: #E0E0E0;
                padding: 6px 20px;
                border: 1px solid #3A3A3A;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #404040;
                border-bottom: 2px solid #26A69A;
            }
            QTableWidget {
                background-color: #1F1F1F;
                alternate-background-color: #2A2A2A;
                gridline-color: #3A3A3A;
                color: #E0E0E0;
                border: 1px solid #3A3A3A;
                font-family: "Courier New";
                font-size: 11pt;
            }
            QHeaderView::section {
                background-color: #2A2A2A;
                color: #E0E0E0;
                padding: 4px;
                border: 1px solid #3A3A3A;
                font-weight: bold;
            }
            QGroupBox {
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 10px;
                color: #E0E0E0;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QDateEdit {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #3A3A3A;
                padding: 4px;
                border-radius: 3px;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus, QDateEdit:focus {
                border: 1px solid #26A69A;
            }
            QComboBox QAbstractItemView {
                background-color: #2A2A2A;
                color: #E0E0E0;
                selection-background-color: #26A69A;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
                background-color: #3A3A3A;
                color: #E0E0E0;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QLabel {
                color: #E0E0E0;
            }
            QStatusBar {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border-top: 1px solid #3A3A3A;
            }
            QListWidget {
                background-color: #1F1F1F;
                color: #E0E0E0;
                border: 1px solid #3A3A3A;
            }
            QListWidget::item:selected {
                background-color: #26A69A;
            }
            QTextEdit {
                background-color: #1F1F1F;
                color: #E0E0E0;
                border: 1px solid #3A3A3A;
                font-family: "Courier New";
                font-size: 9pt;
            }
            QCheckBox {
                color: #E0E0E0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QSplitter::handle {
                background-color: #3A3A3A;
            }
            QScrollBar:vertical {
                background-color: #1A1A1A;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #3A3A3A;
                border-radius: 5px;
            }
            QProgressDialog {
                background-color: #2A2A2A;
            }
            QDialog {
                background-color: #1A1A1A;
                color: #E0E0E0;
            }
        """)

        # Central tab widget
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # Real tabs (with fallback to placeholders if import failed)
        if DashboardTab is not None:
            self._dashboard_tab = DashboardTab()
        else:
            self._dashboard_tab = QWidget()

        if ChartTab is not None:
            self._chart_tab = ChartTab(self._settings)
        else:
            self._chart_tab = QWidget()

        if StrategyTab is not None:
            self._strategy_tab = StrategyTab(
                self._settings,
                on_strategy_reload=self._on_strategy_reload,
            )
        else:
            self._strategy_tab = QWidget()

        self._tabs.addTab(self._dashboard_tab, "Dashboard")
        self._tabs.addTab(self._chart_tab, "Chart")
        self._tabs.addTab(self._strategy_tab, "Strategy")

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

    def show_toast(self, title: str, message: str, event_type: str):
        """Show a toast notification positioned bottom-right of the main window.

        Args:
            title: Short notification title.
            message: Notification body text.
            event_type: One of "trade", "signal", "error" -- determines border color.
        """
        from kiwoom_trader.gui.widgets.toast_widget import ToastWidget

        # Calculate Y offset for stacking active toasts
        y_offset = 0
        for toast in self._active_toasts:
            y_offset += toast.height() + 8

        toast = ToastWidget(
            parent=self,
            title=title,
            message=message,
            event_type=event_type,
            duration_ms=4000,
            on_dismiss=lambda t=None: self._remove_toast(t),
        )

        # Position bottom-right of main window
        margin = 16
        x = self.width() - toast.width() - margin
        y = self.height() - toast.height() - margin - y_offset
        toast.move(x, y)
        toast.show()

        # Track for stacking
        self._active_toasts.append(toast)
        # Bind dismiss callback with the actual toast reference
        toast._on_dismiss = lambda: self._remove_toast(toast)

    def _remove_toast(self, toast):
        """Remove a toast from the active list and reposition remaining."""
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
            self._reposition_toasts()

    def _reposition_toasts(self):
        """Reposition all active toasts after one is dismissed."""
        margin = 16
        y_offset = 0
        for toast in self._active_toasts:
            x = self.width() - toast.width() - margin
            y = self.height() - toast.height() - margin - y_offset
            toast.move(x, y)
            y_offset += toast.height() + 8
