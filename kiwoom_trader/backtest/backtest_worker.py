"""BacktestWorker: QThread wrapper for non-blocking backtest execution.

Runs data download (Phase 1) and simulation (Phase 2) in a background thread,
emitting progress/finished/error signals to keep the UI responsive.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

try:
    from PyQt5.QtCore import QThread, pyqtSignal

    _HAS_PYQT5 = True
except ImportError:
    _HAS_PYQT5 = False

    class _QThreadStub:
        """Minimal stub so the class definition doesn't fail without PyQt5."""
        pass

    QThread = _QThreadStub  # type: ignore[misc,assignment]

if TYPE_CHECKING:
    from kiwoom_trader.backtest.backtest_engine import BacktestEngine
    from kiwoom_trader.backtest.data_source import DataSource


class BacktestWorker(QThread if _HAS_PYQT5 else object):  # type: ignore[misc]
    """Runs backtest in a QThread with progress reporting.

    Signals:
        progress(current, total, phase_name): Emitted during download and simulation.
        finished(result): Emitted with BacktestResult on success.
            The result object also carries ``candles`` attribute for chart rendering.
        error(message): Emitted with error string on failure.

    Args:
        data_source: DataSource for fetching historical candles.
        engine: BacktestEngine configured with strategy/risk/cost.
        code: Stock code to backtest.
        start_date: Backtest start date.
        end_date: Backtest end date.
    """

    if _HAS_PYQT5:
        progress = pyqtSignal(int, int, str)   # current, total, phase_name
        finished = pyqtSignal(object)           # BacktestResult (with .candles)
        error = pyqtSignal(str)                 # error message

    def __init__(
        self,
        data_source: DataSource,
        engine: BacktestEngine,
        code: str,
        start_date: date,
        end_date: date,
    ) -> None:
        if _HAS_PYQT5:
            super().__init__()
        self._data_source = data_source
        self._engine = engine
        self._code = code
        self._start_date = start_date
        self._end_date = end_date
        self._candles = []

    def run(self) -> None:
        """Execute backtest: download data then simulate.

        Phase 1 - "Downloading": fetch candles via DataSource.
        Phase 2 - "Simulating": run BacktestEngine replay loop.
        Calls compute_all_metrics on the result before emitting finished.
        """
        try:
            # Phase 1: Download historical data
            candles = self._data_source.get_candles(
                self._code,
                self._start_date,
                self._end_date,
                on_progress=lambda cur, tot: self.progress.emit(cur, tot, "Downloading"),
            )

            if not candles:
                self.error.emit("No candle data retrieved for the specified period.")
                return

            self._candles = candles

            # Phase 2: Run simulation
            result = self._engine.run(
                candles,
                on_progress=lambda cur, tot: self.progress.emit(cur, tot, "Simulating"),
            )

            # Compute all performance metrics
            from kiwoom_trader.backtest.performance import compute_all_metrics

            compute_all_metrics(result)

            # Attach candles to result for chart rendering
            result._candles = candles  # type: ignore[attr-defined]

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))
