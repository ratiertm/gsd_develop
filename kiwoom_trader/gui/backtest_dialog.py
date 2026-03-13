"""BacktestDialog: QDialog displaying backtest results with summary table and charts.

Displays:
- Summary metrics table (11 rows: return, MDD, win rate, etc.)
- 4 chart tabs: Equity Curve, Drawdown, Price + Trades, Monthly Returns
- Close button

Uses pyqtgraph for all chart rendering. Reuses CandlestickItem from Phase 4.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

try:
    import pyqtgraph as pg
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

    _HAS_PYQT5 = True
except ImportError:
    _HAS_PYQT5 = False
    QDialog = object  # type: ignore[misc,assignment]

if TYPE_CHECKING:
    from kiwoom_trader.core.models import BacktestResult, Candle


# ------------------------------------------------------------------ #
# Number formatting helpers
# ------------------------------------------------------------------ #

def _fmt_pct(value: float) -> str:
    """Format as percentage: XX.XX%."""
    return f"{value:.2f}%"


def _fmt_ratio(value: float) -> str:
    """Format ratio: X.XX (or 'inf')."""
    if value == float("inf"):
        return "inf"
    return f"{value:.2f}"


def _fmt_krw(value: float) -> str:
    """Format as KRW with comma separators."""
    return f"{int(value):,}"


def _fmt_days(value: float) -> str:
    """Format holding period in days."""
    return f"{value:.1f} days"


def _fmt_int(value: int) -> str:
    """Format integer."""
    return str(value)


# ------------------------------------------------------------------ #
# Summary table row definitions
# ------------------------------------------------------------------ #

SUMMARY_ROWS = [
    ("Total Return", lambda r: _fmt_pct(r.total_return_pct)),
    ("Max Drawdown (MDD)", lambda r: _fmt_pct(r.max_drawdown_pct)),
    ("Win Rate", lambda r: _fmt_pct(r.win_rate_pct)),
    ("Profit Factor", lambda r: _fmt_ratio(r.profit_factor)),
    ("Sharpe Ratio", lambda r: _fmt_ratio(r.sharpe_ratio)),
    ("Total Trades", lambda r: _fmt_int(r.total_trades)),
    ("Avg P&L", lambda r: _fmt_krw(r.avg_pnl)),
    ("Max Consecutive Losses", lambda r: _fmt_int(r.max_consecutive_losses)),
    ("Avg Holding Period", lambda r: _fmt_days(r.avg_holding_periods)),
    ("Initial Capital", lambda r: _fmt_krw(r.initial_capital)),
    ("Final Capital", lambda r: _fmt_krw(r.final_capital)),
]


class BacktestDialog(QDialog if _HAS_PYQT5 else object):  # type: ignore[misc]
    """Dialog displaying backtest results: summary table + 4 chart tabs.

    Args:
        result: BacktestResult with computed metrics.
        candles: Historical candles used in the backtest (for price chart).
        parent: Optional parent widget.
    """

    def __init__(
        self,
        result: BacktestResult,
        candles: list[Candle],
        parent=None,
    ) -> None:
        if _HAS_PYQT5:
            super().__init__(parent)
        self._result = result
        self._candles = candles

        if _HAS_PYQT5:
            self._setup_ui()

    def _setup_ui(self) -> None:
        """Build dialog layout: summary table + chart tabs + close button."""
        self.setWindowTitle("Backtest Results")
        self.resize(1200, 800)

        layout = QVBoxLayout(self)

        # Top: Summary table
        self._summary_table = self._create_summary_table()
        layout.addWidget(self._summary_table, stretch=2)

        # Middle: Chart tabs
        charts = QTabWidget()
        charts.addTab(self._create_equity_chart(), "Equity Curve")
        charts.addTab(self._create_drawdown_chart(), "Drawdown")
        charts.addTab(self._create_price_chart(), "Price + Trades")
        charts.addTab(self._create_monthly_chart(), "Monthly Returns")
        layout.addWidget(charts, stretch=6)

        # Bottom: Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------ #
    # Summary table
    # ------------------------------------------------------------------ #

    def _create_summary_table(self) -> QTableWidget:
        """Create 2-column summary table with metric name/value rows."""
        table = QTableWidget(len(SUMMARY_ROWS), 2)
        table.setHorizontalHeaderLabels(["Metric", "Value"])
        table.verticalHeader().setVisible(False)

        for row_idx, (metric_name, formatter) in enumerate(SUMMARY_ROWS):
            name_item = QTableWidgetItem(metric_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            value_item = QTableWidgetItem(formatter(self._result))
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row_idx, 0, name_item)
            table.setItem(row_idx, 1, value_item)

        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 250)
        return table

    # ------------------------------------------------------------------ #
    # Chart: Equity Curve
    # ------------------------------------------------------------------ #

    def _create_equity_chart(self) -> QWidget:
        """Line chart of equity over time."""
        widget = pg.PlotWidget(title="Equity Curve")
        widget.setLabel("left", "Equity (KRW)")
        widget.setLabel("bottom", "Time")
        widget.showGrid(x=True, y=True, alpha=0.3)

        ec = self._result.equity_curve
        if ec:
            x = list(range(len(ec)))
            y = [eq for _, eq in ec]
            widget.plot(x, y, pen=pg.mkPen("#26A69A", width=2))

        return widget

    # ------------------------------------------------------------------ #
    # Chart: Drawdown
    # ------------------------------------------------------------------ #

    def _create_drawdown_chart(self) -> QWidget:
        """Drawdown percentage chart with filled area."""
        widget = pg.PlotWidget(title="Drawdown")
        widget.setLabel("left", "Drawdown (%)")
        widget.setLabel("bottom", "Time")
        widget.showGrid(x=True, y=True, alpha=0.3)

        ec = self._result.equity_curve
        if len(ec) >= 2:
            dd_values = []
            peak = ec[0][1]
            for _, equity in ec:
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
                dd_values.append(-dd)  # Negative for visual downward direction

            x = list(range(len(dd_values)))
            curve = widget.plot(x, dd_values, pen=pg.mkPen("#EF5350", width=1))
            fill = pg.FillBetweenItem(
                curve,
                widget.plot(x, [0] * len(x), pen=pg.mkPen(None)),
                brush=pg.mkBrush(239, 83, 80, 80),
            )
            widget.addItem(fill)

        return widget

    # ------------------------------------------------------------------ #
    # Chart: Price + Trades
    # ------------------------------------------------------------------ #

    def _create_price_chart(self) -> QWidget:
        """Candlestick chart with BUY/SELL trade markers."""
        widget = pg.PlotWidget(title="Price + Trades")
        widget.setLabel("left", "Price (KRW)")
        widget.setLabel("bottom", "Candle Index")
        widget.showGrid(x=True, y=True, alpha=0.3)

        if self._candles:
            # Prepare candlestick data: (index, open, close, low, high)
            candle_data = [
                (i, c.open, c.close, c.low, c.high)
                for i, c in enumerate(self._candles)
            ]

            from kiwoom_trader.gui.widgets.candlestick_item import CandlestickItem

            candle_item = CandlestickItem(data=candle_data, max_visible=len(candle_data))
            widget.addItem(candle_item)

            # Build timestamp -> index map for trade markers
            ts_to_idx = {}
            for i, c in enumerate(self._candles):
                ts_to_idx[c.timestamp] = i

            # BUY markers (green triangle up)
            buy_trades = [t for t in self._result.trades if t.side == "BUY"]
            if buy_trades:
                buy_x = []
                buy_y = []
                for t in buy_trades:
                    idx = ts_to_idx.get(t.timestamp)
                    if idx is not None:
                        buy_x.append(idx)
                        buy_y.append(t.price)
                if buy_x:
                    widget.plot(
                        buy_x,
                        buy_y,
                        pen=None,
                        symbol="t",  # triangle up
                        symbolBrush="#26A69A",
                        symbolPen="#26A69A",
                        symbolSize=12,
                    )

            # SELL markers (red triangle down)
            sell_trades = [t for t in self._result.trades if t.side == "SELL"]
            if sell_trades:
                sell_x = []
                sell_y = []
                for t in sell_trades:
                    idx = ts_to_idx.get(t.timestamp)
                    if idx is not None:
                        sell_x.append(idx)
                        sell_y.append(t.price)
                if sell_x:
                    widget.plot(
                        sell_x,
                        sell_y,
                        pen=None,
                        symbol="t1",  # triangle down
                        symbolBrush="#EF5350",
                        symbolPen="#EF5350",
                        symbolSize=12,
                    )

        return widget

    # ------------------------------------------------------------------ #
    # Chart: Monthly Returns
    # ------------------------------------------------------------------ #

    def _create_monthly_chart(self) -> QWidget:
        """Bar chart of monthly aggregated returns."""
        widget = pg.PlotWidget(title="Monthly Returns")
        widget.setLabel("left", "Return (%)")
        widget.setLabel("bottom", "Month")
        widget.showGrid(x=True, y=True, alpha=0.3)

        ec = self._result.equity_curve
        if len(ec) >= 2:
            # Group equity by month, compute monthly returns
            monthly: dict[str, list[float]] = defaultdict(list)
            for ts, equity in ec:
                key = ts.strftime("%Y-%m")
                monthly[key].append(equity)

            sorted_months = sorted(monthly.keys())
            returns = []
            for i, month in enumerate(sorted_months):
                values = monthly[month]
                first_val = values[0]
                last_val = values[-1]
                if first_val > 0:
                    ret = (last_val - first_val) / first_val * 100
                else:
                    ret = 0.0
                returns.append(ret)

            if returns:
                x = list(range(len(returns)))
                colors = [
                    pg.mkBrush("#26A69A") if r >= 0 else pg.mkBrush("#EF5350")
                    for r in returns
                ]
                bar = pg.BarGraphItem(x=x, height=returns, width=0.6, brushes=colors)
                widget.addItem(bar)

                # X-axis labels
                ticks = [(i, m) for i, m in enumerate(sorted_months)]
                widget.getAxis("bottom").setTicks([ticks])

        return widget
