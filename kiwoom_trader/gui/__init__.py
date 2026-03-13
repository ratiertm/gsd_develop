"""GUI package: MainWindow, DashboardTab, ChartTab, StrategyTab, notification system."""

try:
    from kiwoom_trader.gui.main_window import MainWindow
except ImportError:
    MainWindow = None

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
