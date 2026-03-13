---
phase: 05-backtest-validation
plan: 03
subsystem: gui
tags: [backtest, pyqtgraph, qthread, dialog, strategy-tab]

requires:
  - phase: 05-backtest-validation/01
    provides: BacktestEngine, DataSource, CostConfig
  - phase: 05-backtest-validation/02
    provides: compute_all_metrics, PerformanceCalculator
  - phase: 04-monitoring-operations
    provides: CandlestickItem, StrategyTab, MainWindow

provides:
  - BacktestDialog with summary table and 4 chart tabs
  - BacktestWorker QThread for non-blocking execution
  - StrategyTab backtest button with input dialog
  - main.py Phase 5 wiring (button -> worker -> dialog)

affects: []

tech-stack:
  added: []
  patterns: [QThread worker with progress/finished/error signals, QProgressDialog modal]

key-files:
  created:
    - kiwoom_trader/gui/backtest_dialog.py
    - kiwoom_trader/backtest/backtest_worker.py
    - tests/test_backtest_dialog.py
  modified:
    - kiwoom_trader/gui/strategy_tab.py
    - kiwoom_trader/main.py
    - kiwoom_trader/backtest/__init__.py

key-decisions:
  - "BacktestWorker attaches candles to result._candles for chart rendering"
  - "QProgressDialog with cancel -> worker.terminate() for user abort"
  - "Backtest callback wired at runtime in main.py rather than passed through MainWindow"

patterns-established:
  - "QThread worker pattern: progress/finished/error signals for long-running operations"

requirements-completed: [BACK-03]

duration: 8min
completed: 2026-03-14
---

# Plan 05-03: Backtest Visualization & Wiring Summary

**BacktestDialog with equity/drawdown/price charts, BacktestWorker QThread, StrategyTab backtest button with full main.py wiring**

## Performance

- **Duration:** 8 min
- **Completed:** 2026-03-14
- **Tasks:** 2 (Task 3 human-verify pending)
- **Files modified:** 6

## Accomplishments
- BacktestWorker QThread with download/simulation phases, progress/finished/error signals
- BacktestDialog QDialog with summary metrics table (11 rows) and 4 chart tabs (equity curve, drawdown, price+trades, monthly returns)
- StrategyTab backtest button with input dialog (code, date range, capital)
- main.py wiring: button -> BacktestWorker -> QProgressDialog -> BacktestDialog

## Task Commits

1. **Task 1: BacktestWorker, BacktestDialog, smoke test** - `e6ab253` (feat)
2. **Task 2: StrategyTab button, input dialog, main.py wiring** - `f427ad2` (feat)

## Files Created/Modified
- `kiwoom_trader/backtest/backtest_worker.py` - BacktestWorker QThread
- `kiwoom_trader/gui/backtest_dialog.py` - BacktestDialog with summary + 4 chart tabs
- `kiwoom_trader/gui/strategy_tab.py` - Added Backtest button + input dialog
- `kiwoom_trader/main.py` - Phase 5 backtest wiring
- `kiwoom_trader/backtest/__init__.py` - Updated exports
- `tests/test_backtest_dialog.py` - Smoke tests (skip on no PyQt5)

## Decisions Made
- BacktestWorker attaches candles to result._candles for downstream chart rendering
- Backtest callback wired at runtime in main.py (not passed through MainWindow constructor)
- QProgressDialog modal with cancel support via worker.terminate()

## Deviations from Plan
None - plan executed as specified.

## Issues Encountered
- Executor agent hit bash permission limits; Task 2 completed manually.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Task 3 (human visual verification) pending
- All Phase 5 code complete: engine + metrics + visualization

---
*Phase: 05-backtest-validation*
*Completed: 2026-03-14*
