"""ToastWidget: self-dismissing overlay notification with fade animation."""

from PyQt5.QtCore import QPropertyAnimation, QTimer, Qt
from PyQt5.QtWidgets import QLabel, QGraphicsOpacityEffect


# Border colors by event type
_BORDER_COLORS = {
    "trade": "#26A69A",   # green
    "signal": "#42A5F5",  # blue
    "error": "#EF5350",   # red
}


class ToastWidget(QLabel):
    """Bottom-right toast notification with fade-in/out animation.

    Args:
        parent: Parent widget (MainWindow).
        title: Bold header text.
        message: Body text.
        event_type: "trade", "signal", or "error" -- determines border color.
        duration_ms: How long the toast stays visible before fading out.
        on_dismiss: Callback invoked when the toast is fully dismissed.
    """

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        event_type: str = "trade",
        duration_ms: int = 4000,
        on_dismiss=None,
    ):
        super().__init__(parent)
        self._on_dismiss = on_dismiss

        # Content
        self.setText(f"<b>{title}</b><br>{message}")
        self.setTextFormat(Qt.RichText)
        self.setWordWrap(True)

        # Style with event-type border color
        border_color = _BORDER_COLORS.get(event_type, "#757575")
        self.setStyleSheet(
            f"background: #323232; color: white; padding: 12px; "
            f"border-left: 4px solid {border_color}; "
            f"border-radius: 8px; font-size: 13px;"
        )
        self.setFixedWidth(320)
        self.adjustSize()

        # Opacity effect for fade animation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)

        # Fade in (300ms)
        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in.setDuration(300)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start()

        # Auto-dismiss timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out_and_close)
        self._timer.start(duration_ms)

    def _fade_out_and_close(self):
        """Fade out over 300ms, then destroy and notify parent."""
        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out.setDuration(300)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.finished.connect(self._dismiss)
        self._fade_out.start()

    def _dismiss(self):
        """Clean up and invoke on_dismiss callback."""
        if self._on_dismiss:
            try:
                self._on_dismiss()
            except Exception:
                pass
        self.deleteLater()
