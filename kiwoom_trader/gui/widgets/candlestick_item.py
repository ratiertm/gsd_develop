"""CandlestickItem: pyqtgraph GraphicsObject for OHLCV candlestick rendering.

Renders candlesticks with green (up) and red (down) color coding.
Uses QPicture pre-rendering for performance and sliding window
to limit visible candles (default 120 = ~2 hours of 1-min data).
"""

from __future__ import annotations

try:
    import pyqtgraph as pg
    from PyQt5.QtCore import QPointF, QRectF
    from PyQt5.QtGui import QPainter, QPen, QColor, QPicture

    _HAS_PG = True
except ImportError:
    _HAS_PG = False


# Colors matching standard candlestick conventions
COLOR_UP = "#26A69A"  # Green -- close >= open
COLOR_DOWN = "#EF5350"  # Red -- close < open
COLOR_WICK = "#FFFFFF"  # White wicks

# Default sliding window size (~2 hours of 1-min candles)
DEFAULT_MAX_VISIBLE = 120


if _HAS_PG:

    class CandlestickItem(pg.GraphicsObject):
        """Custom graphics item for rendering OHLCV candlestick charts.

        Data format: list of (time_index, open, close, low, high) tuples.
        Uses QPicture pre-rendering for fast paint operations.

        Args:
            data: Initial candle data (list of tuples).
            max_visible: Maximum number of candles to render (sliding window).
        """

        def __init__(
            self,
            data: list[tuple] | None = None,
            max_visible: int = DEFAULT_MAX_VISIBLE,
        ) -> None:
            super().__init__()
            self._data: list[tuple] = data or []
            self._max_visible = max_visible
            self._picture = QPicture()
            if self._data:
                self._generate_picture()

        def set_data(self, data: list[tuple]) -> None:
            """Update candle data and re-render.

            Applies sliding window to keep only last max_visible candles.

            Args:
                data: List of (time_index, open, close, low, high) tuples.
            """
            self._data = data[-self._max_visible :]
            self._generate_picture()
            self.informViewBoundsChanged()
            self.update()

        def _generate_picture(self) -> None:
            """Pre-render all candles into a QPicture for fast paint."""
            self._picture = QPicture()
            painter = QPainter(self._picture)

            wick_pen = QPen(QColor(COLOR_WICK))
            wick_pen.setWidthF(0.5)

            body_width = 0.6

            for time_idx, open_price, close_price, low, high in self._data:
                if close_price >= open_price:
                    color = QColor(COLOR_UP)
                else:
                    color = QColor(COLOR_DOWN)

                # Draw wick (high-low line)
                painter.setPen(wick_pen)
                painter.drawLine(
                    QPointF(time_idx, low),
                    QPointF(time_idx, high),
                )

                # Draw body (open-close rectangle)
                body_pen = QPen(color)
                body_pen.setWidthF(0.3)
                painter.setPen(body_pen)
                painter.setBrush(color)

                body_top = max(open_price, close_price)
                body_bottom = min(open_price, close_price)
                body_height = body_top - body_bottom

                # Minimum body height for doji candles
                if body_height == 0:
                    body_height = 1

                painter.drawRect(
                    QPointF(time_idx - body_width / 2, body_bottom).x(),
                    QPointF(time_idx - body_width / 2, body_bottom).y(),
                    body_width,
                    body_height,
                )

            painter.end()

        def paint(self, painter: QPainter, *args) -> None:
            """Paint pre-rendered picture."""
            painter.drawPicture(0, 0, self._picture)

        def boundingRect(self) -> QRectF:
            """Return bounding rectangle of the pre-rendered picture."""
            return QRectF(self._picture.boundingRect())

else:
    # Stub class for environments without pyqtgraph/PyQt5
    class CandlestickItem:
        """Stub CandlestickItem for environments without pyqtgraph."""

        def __init__(
            self,
            data: list[tuple] | None = None,
            max_visible: int = DEFAULT_MAX_VISIBLE,
        ) -> None:
            self._data: list[tuple] = data or []
            self._max_visible = max_visible

        def set_data(self, data: list[tuple]) -> None:
            """Update candle data (stub)."""
            self._data = data[-self._max_visible :]

        def boundingRect(self):
            """Return a placeholder bounding rect."""
            if not self._data:
                return (0, 0, 0, 0)
            times = [d[0] for d in self._data]
            lows = [d[3] for d in self._data]
            highs = [d[4] for d in self._data]
            return (min(times), min(lows), max(times) - min(times), max(highs) - min(lows))
