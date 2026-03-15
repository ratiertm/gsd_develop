"""Shared fixtures for PyAutoGUI-based GUI tests.

Launches the mock GUI in a subprocess, waits for the window to appear,
and provides pyautogui + pygetwindow helpers for tests.
"""

import os
import subprocess
import sys
import time

import pytest

pyautogui = pytest.importorskip("pyautogui")
pygetwindow = pytest.importorskip("pygetwindow")

# Safety: prevent pyautogui from moving to corners (failsafe)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3  # 300ms pause between actions

WINDOW_TITLE = "KiwoomDayTrader [TEST MODE]"
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")


@pytest.fixture(scope="session")
def gui_app():
    """Launch the mock GUI app and return the subprocess handle.

    Yields the subprocess. Terminates it after the test session.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.Popen(
        [sys.executable, "-m", "tests.gui_runner"],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for window to appear (max 15 seconds)
    deadline = time.time() + 15
    window = None
    while time.time() < deadline:
        windows = pygetwindow.getWindowsWithTitle(WINDOW_TITLE)
        if windows:
            window = windows[0]
            break
        time.sleep(0.5)

    if window is None:
        proc.terminate()
        stdout = proc.stdout.read().decode(errors="replace")
        stderr = proc.stderr.read().decode(errors="replace")
        pytest.fail(
            f"GUI window '{WINDOW_TITLE}' did not appear within 15s.\n"
            f"stdout: {stdout}\nstderr: {stderr}"
        )

    # Bring window to foreground
    try:
        window.activate()
    except Exception:
        pass
    time.sleep(1)

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def app_window(gui_app):
    """Return the pygetwindow.Window object for the test app."""
    windows = pygetwindow.getWindowsWithTitle(WINDOW_TITLE)
    assert windows, f"Window '{WINDOW_TITLE}' not found"
    win = windows[0]
    try:
        win.activate()
    except Exception:
        pass
    time.sleep(0.3)
    return win


def take_screenshot(name: str) -> str:
    """Take a screenshot and save to tests/screenshots/. Returns the path."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    pyautogui.screenshot(path)
    return path


def find_and_click(text: str, window=None, confidence=0.8):
    """Try to find text/image on screen and click it.

    For text-based finding, uses pyautogui.locateOnScreen with an image.
    For simple cases, use tab coordinates instead.
    """
    # This is a placeholder - actual implementation depends on approach
    pass
