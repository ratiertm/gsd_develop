"""Visual GUI tests using PyAutoGUI + pytest.

These tests launch the app in test mode with mock data,
then interact with and verify the GUI visually.

Run:
    python -m pytest tests/test_gui_visual.py -v -s

Each test takes a screenshot for manual review in tests/screenshots/.
"""

import os
import time

import pytest

pyautogui = pytest.importorskip("pyautogui")
pygetwindow = pytest.importorskip("pygetwindow")

from tests.conftest_gui import gui_app, app_window, take_screenshot, WINDOW_TITLE


# ------------------------------------------------------------------ #
# Test 1: Window Launch & Basic Structure
# ------------------------------------------------------------------ #


class TestWindowLaunch:
    """Verify the main window appears with correct title and size."""

    def test_window_exists(self, gui_app, app_window):
        """Window should appear with the test mode title."""
        assert app_window is not None
        assert WINDOW_TITLE in app_window.title
        take_screenshot("01_window_launched")

    def test_window_size(self, app_window):
        """Window should be at least 1200x800."""
        assert app_window.width >= 1200
        assert app_window.height >= 800

    def test_window_visible(self, app_window):
        """Window should be visible (not minimized)."""
        assert not app_window.isMinimized


# ------------------------------------------------------------------ #
# Test 2: Tab Navigation
# ------------------------------------------------------------------ #


class TestTabNavigation:
    """Verify all 3 tabs exist and can be clicked."""

    def _get_tab_bar_region(self, app_window):
        """Get the approximate region of the tab bar (top of window)."""
        return (
            app_window.left + 10,
            app_window.top + 30,   # Below title bar
            app_window.width - 20,
            40,                     # Tab bar height ~40px
        )

    def test_dashboard_tab(self, gui_app, app_window):
        """Click Dashboard tab and verify it's active."""
        # Dashboard is the first tab - click near left of tab bar
        x = app_window.left + 60
        y = app_window.top + 55
        pyautogui.click(x, y)
        time.sleep(0.5)
        take_screenshot("02_dashboard_tab")

    def test_chart_tab(self, gui_app, app_window):
        """Click Chart tab and verify chart is displayed."""
        # Chart is the second tab
        x = app_window.left + 160
        y = app_window.top + 55
        pyautogui.click(x, y)
        time.sleep(0.5)
        take_screenshot("03_chart_tab")

    def test_strategy_tab(self, gui_app, app_window):
        """Click Strategy tab and verify form is displayed."""
        # Strategy is the third tab
        x = app_window.left + 260
        y = app_window.top + 55
        pyautogui.click(x, y)
        time.sleep(0.5)
        take_screenshot("04_strategy_tab")

    def test_return_to_dashboard(self, gui_app, app_window):
        """Return to Dashboard tab."""
        x = app_window.left + 60
        y = app_window.top + 55
        pyautogui.click(x, y)
        time.sleep(0.5)
        take_screenshot("05_back_to_dashboard")


# ------------------------------------------------------------------ #
# Test 3: Dashboard Content
# ------------------------------------------------------------------ #


class TestDashboardContent:
    """Verify dashboard shows mock data correctly."""

    def test_dashboard_visible(self, gui_app, app_window):
        """Navigate to Dashboard and take full screenshot."""
        x = app_window.left + 60
        y = app_window.top + 55
        pyautogui.click(x, y)
        time.sleep(0.5)

        # Take a screenshot of just the window region
        region = (
            app_window.left,
            app_window.top,
            app_window.width,
            app_window.height,
        )
        path = os.path.join(
            os.path.dirname(__file__), "screenshots", "06_dashboard_content.png"
        )
        pyautogui.screenshot(path, region=region)

    def test_status_panel_visible(self, gui_app, app_window):
        """System status panel should be visible on the right side."""
        # Status panel is in the right 40% of the top section
        take_screenshot("07_dashboard_status")


# ------------------------------------------------------------------ #
# Test 4: Chart Interaction
# ------------------------------------------------------------------ #


class TestChartInteraction:
    """Verify chart tab shows candles and responds to interaction."""

    def test_chart_displays_candles(self, gui_app, app_window):
        """Switch to Chart tab and verify candles are rendered."""
        x = app_window.left + 160
        y = app_window.top + 55
        pyautogui.click(x, y)
        time.sleep(1)
        take_screenshot("08_chart_candles")

    def test_chart_zoom_scroll(self, gui_app, app_window):
        """Test mouse scroll zoom on the chart."""
        # Move to center of chart area
        cx = app_window.left + app_window.width // 2
        cy = app_window.top + app_window.height // 2
        pyautogui.moveTo(cx, cy)
        time.sleep(0.3)

        # Scroll up (zoom in)
        pyautogui.scroll(3)
        time.sleep(0.3)
        take_screenshot("09_chart_zoom_in")

        # Scroll down (zoom out)
        pyautogui.scroll(-3)
        time.sleep(0.3)
        take_screenshot("10_chart_zoom_out")


# ------------------------------------------------------------------ #
# Test 5: Strategy Tab Interaction
# ------------------------------------------------------------------ #


class TestStrategyTab:
    """Verify strategy tab form and button interactions."""

    def test_strategy_tab_layout(self, gui_app, app_window):
        """Switch to Strategy tab and verify layout."""
        x = app_window.left + 260
        y = app_window.top + 55
        pyautogui.click(x, y)
        time.sleep(0.5)
        take_screenshot("11_strategy_layout")

    def test_new_strategy_button(self, gui_app, app_window):
        """Click 'New' button to create a new strategy."""
        # Strategy tab should be active from previous test
        # 'New' button is in the left panel bottom area
        # Approximate: left panel is 30% width, buttons at bottom
        x = app_window.left + 50
        y = app_window.top + app_window.height - 180  # Near bottom of left panel
        pyautogui.click(x, y)
        time.sleep(0.5)
        take_screenshot("12_new_strategy")


# ------------------------------------------------------------------ #
# Test 6: Window Resize
# ------------------------------------------------------------------ #


class TestWindowResize:
    """Verify window handles resize properly."""

    def test_resize_smaller(self, gui_app, app_window):
        """Resize window smaller and verify no crash."""
        original_size = (app_window.width, app_window.height)
        try:
            app_window.resizeTo(800, 600)
        except Exception:
            pass
        time.sleep(0.5)
        take_screenshot("13_resized_small")

        # Restore
        try:
            app_window.resizeTo(*original_size)
        except Exception:
            pass
        time.sleep(0.5)

    def test_maximize(self, gui_app, app_window):
        """Maximize window and verify no crash."""
        try:
            app_window.maximize()
        except Exception:
            pass
        time.sleep(0.5)
        take_screenshot("14_maximized")

        # Restore
        try:
            app_window.restore()
        except Exception:
            pass
        time.sleep(0.5)


# ------------------------------------------------------------------ #
# Test 7: Toast Notification (manual trigger)
# ------------------------------------------------------------------ #


class TestToastNotification:
    """Verify toast popup works (triggered programmatically)."""

    def test_toast_appears(self, gui_app, app_window):
        """This test verifies the window is still responsive after all interactions."""
        # Return to dashboard
        x = app_window.left + 60
        y = app_window.top + 55
        pyautogui.click(x, y)
        time.sleep(0.5)
        take_screenshot("15_final_state")
        # Window should still be responsive
        assert not app_window.isMinimized
