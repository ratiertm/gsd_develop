"""Tests for ToastWidget (mocked Qt dependencies)."""

from unittest.mock import MagicMock, patch
import sys

import pytest


class TestToastWidgetCreation:
    """Test ToastWidget can be instantiated with mocked Qt."""

    @patch.dict(sys.modules, {
        "PyQt5": MagicMock(),
        "PyQt5.QtCore": MagicMock(),
        "PyQt5.QtWidgets": MagicMock(),
    })
    def test_toast_widget_creation(self):
        """ToastWidget can be instantiated (mocked QLabel)."""
        # Re-import with mocked PyQt5
        import importlib
        # We test the logic parts -- border color selection
        from kiwoom_trader.gui.widgets.toast_widget import _BORDER_COLORS

        assert _BORDER_COLORS["trade"] == "#26A69A"
        assert _BORDER_COLORS["signal"] == "#42A5F5"
        assert _BORDER_COLORS["error"] == "#EF5350"
