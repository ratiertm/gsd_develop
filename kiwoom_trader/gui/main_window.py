"""MainWindow with QTabWidget skeleton (3 tabs) and toast notification support."""

from PyQt5.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QStatusBar,
    QVBoxLayout,
)

from kiwoom_trader.config.settings import Settings


class MainWindow(QMainWindow):
    """Primary application window with tabbed interface.

    Tabs:
        - Dashboard: positions, orders, P&L, system status (Plan 02)
        - Chart: candlestick chart with indicator overlays (Plan 03)
        - Strategy: strategy editor, watchlist management (Plan 04)
    """

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._active_toasts: list = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("KiwoomDayTrader")
        self.setMinimumSize(1200, 800)

        # Central tab widget
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # Placeholder tabs -- replaced by Plans 02-04
        self._dashboard_tab = QWidget()
        self._chart_tab = QWidget()
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
