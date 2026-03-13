"""Indicator sub-chart helper functions for pyqtgraph-based chart layout.

Provides factory functions to create linked sub-plots for RSI, MACD, and OBV
indicators below the main price chart. Each sub-chart is X-linked to the
price chart for synchronized panning/zooming.
"""

from __future__ import annotations

try:
    import pyqtgraph as pg
    from PyQt5.QtGui import QPen, QColor

    _HAS_PG = True
except ImportError:
    _HAS_PG = False


# Sub-chart height in pixels
SUB_CHART_HEIGHT = 100


def create_rsi_plot(parent_layout, row: int, price_plot):
    """Create an RSI sub-chart linked to the price plot's X axis.

    Adds horizontal reference lines at RSI 30 (oversold) and 70 (overbought).

    Args:
        parent_layout: pg.GraphicsLayoutWidget to add the plot to.
        row: Row index in the layout.
        price_plot: Main price PlotItem to link X axis with.

    Returns:
        PlotItem for the RSI sub-chart, or None if pyqtgraph unavailable.
    """
    if not _HAS_PG:
        return None

    parent_layout.nextRow()
    rsi_plot = parent_layout.addPlot(row=row, col=0)
    rsi_plot.setMaximumHeight(SUB_CHART_HEIGHT)
    rsi_plot.setXLink(price_plot)
    rsi_plot.showGrid(y=True, alpha=0.3)
    rsi_plot.setLabel("left", "RSI")
    rsi_plot.setYRange(0, 100, padding=0.05)

    # Overbought/oversold reference lines
    pen_ref = QPen(QColor("#888888"))
    pen_ref.setStyle(2)  # DashLine
    rsi_plot.addLine(y=70, pen=pen_ref)
    rsi_plot.addLine(y=30, pen=pen_ref)

    return rsi_plot


def create_macd_plot(parent_layout, row: int, price_plot):
    """Create a MACD sub-chart with histogram, MACD line, and signal line.

    Args:
        parent_layout: pg.GraphicsLayoutWidget to add the plot to.
        row: Row index in the layout.
        price_plot: Main price PlotItem to link X axis with.

    Returns:
        PlotItem for the MACD sub-chart, or None if pyqtgraph unavailable.
    """
    if not _HAS_PG:
        return None

    parent_layout.nextRow()
    macd_plot = parent_layout.addPlot(row=row, col=0)
    macd_plot.setMaximumHeight(SUB_CHART_HEIGHT)
    macd_plot.setXLink(price_plot)
    macd_plot.showGrid(y=True, alpha=0.3)
    macd_plot.setLabel("left", "MACD")

    # Zero reference line
    pen_zero = QPen(QColor("#888888"))
    pen_zero.setStyle(2)
    macd_plot.addLine(y=0, pen=pen_zero)

    return macd_plot


def create_obv_plot(parent_layout, row: int, price_plot):
    """Create an OBV (On-Balance Volume) sub-chart.

    Args:
        parent_layout: pg.GraphicsLayoutWidget to add the plot to.
        row: Row index in the layout.
        price_plot: Main price PlotItem to link X axis with.

    Returns:
        PlotItem for the OBV sub-chart, or None if pyqtgraph unavailable.
    """
    if not _HAS_PG:
        return None

    parent_layout.nextRow()
    obv_plot = parent_layout.addPlot(row=row, col=0)
    obv_plot.setMaximumHeight(SUB_CHART_HEIGHT)
    obv_plot.setXLink(price_plot)
    obv_plot.showGrid(y=True, alpha=0.3)
    obv_plot.setLabel("left", "OBV")

    return obv_plot
