"""GUI package: MainWindow, widgets, notification system."""

try:
    from kiwoom_trader.gui.main_window import MainWindow
except ImportError:
    # Cross-platform fallback: PyQt5 not available on macOS/Linux dev
    MainWindow = None
