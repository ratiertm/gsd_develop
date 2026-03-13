---
phase: 04-monitoring-operations
plan: 04
subsystem: ui
tags: [pyqt5, strategy-editor, watchlist, gui-wiring, hot-swap, notification]

# Dependency graph
requires:
  - phase: 04-monitoring-operations/04-01
    provides: Settings.save(), notification config, MainWindow skeleton, ToastWidget
  - phase: 04-monitoring-operations/04-02
    provides: DashboardTab with positions, orders, P&L, status, log panel
  - phase: 04-monitoring-operations/04-03
    provides: ChartTab with candlestick chart, indicators, trade markers
provides:
  - StrategyTab with full CRUD for strategies (create, edit, copy, delete)
  - Watchlist management (add/remove stock codes, assign strategies)
  - Strategy validation and serialization pure functions
  - MainWindow with real DashboardTab, ChartTab, StrategyTab (not placeholders)
  - main.py Phase 4 wiring: dashboard polling, chart candle feed, strategy hot-swap, notifications, log panel
  - order_filled signal bridging: dashboard gets list[Order] via get_active_orders(), chart gets trade markers
affects: [05-backtest]

# Tech tracking
tech-stack:
  added: []
  patterns: [pure-function-extraction, signal-impedance-bridging, strategy-hot-swap, fire-and-forget-notification]

key-files:
  created:
    - kiwoom_trader/gui/strategy_tab.py
    - tests/test_strategy_tab.py
  modified:
    - kiwoom_trader/gui/main_window.py
    - kiwoom_trader/gui/__init__.py
    - kiwoom_trader/main.py

key-decisions:
  - "OPERATORS defined locally in strategy_tab.py (not imported from condition_engine which lacks the constant)"
  - "StrategyManager hot-swap clears candle_aggregator callbacks and re-registers new instance"
  - "order_filled bridging via get_active_orders() for dashboard and get_order() for chart trade markers"

patterns-established:
  - "Pure function extraction: validate_strategy, form_to_strategy_dict, strategy_dict_to_form_data for testability"
  - "Signal impedance bridging: lambda/slot adapters convert signal args to method-expected types"
  - "Strategy hot-swap: on_strategy_reload callback re-creates StrategyManager and re-wires candle callback"

requirements-completed: [GUI-03]

# Metrics
duration: 4min
completed: 2026-03-14
---

# Phase 4 Plan 4: Strategy Tab & Phase 4 Wiring Summary

**StrategyTab with CRUD editor, watchlist manager, and full Phase 4 wiring connecting all GUI tabs to live data sources**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-13T18:22:21Z
- **Completed:** 2026-03-13T18:26:44Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- StrategyTab with form editor for strategy CRUD, validation, and serialization
- Watchlist management: add/remove stock codes, assign strategies per stock
- MainWindow replaced all 3 placeholder tabs with real DashboardTab, ChartTab, StrategyTab
- main.py Phase 4 section wires dashboard polling, chart candle feed, strategy hot-swap, Notifier, log panel sink
- order_filled signal properly bridged to dashboard (via get_active_orders) and chart (via get_order for side detection)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: StrategyTab failing tests** - `3cd9918` (test)
2. **Task 1 GREEN: StrategyTab implementation** - `14f1f32` (feat)
3. **Task 2: Wire Phase 4 components** - `72e8623` (feat)

## Files Created/Modified
- `kiwoom_trader/gui/strategy_tab.py` - StrategyTab widget with CRUD, validation, serialization, watchlist operations
- `tests/test_strategy_tab.py` - 15 tests for validation, serialization, copy, watchlist operations
- `kiwoom_trader/gui/main_window.py` - Real tabs (DashboardTab, ChartTab, StrategyTab) with fallback
- `kiwoom_trader/gui/__init__.py` - Exports MainWindow, DashboardTab, ChartTab, StrategyTab
- `kiwoom_trader/main.py` - Phase 4 wiring: MainWindow, Notifier, signal connections, dashboard polling

## Decisions Made
- OPERATORS set defined locally in strategy_tab.py since condition_engine.py does not export it as a module-level constant
- StrategyManager hot-swap clears candle_aggregator._callbacks and re-registers the new instance's on_candle_complete
- order_filled bridging: dashboard gets full list[Order] via get_active_orders() on each fill event, chart determines buy/sell via get_order() for trade markers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] OPERATORS constant not in condition_engine.py**
- **Found during:** Task 1 (StrategyTab implementation)
- **Issue:** Plan referenced `from kiwoom_trader.core.condition_engine import OPERATORS` but the constant does not exist in condition_engine.py
- **Fix:** Defined OPERATORS set locally in strategy_tab.py matching the operators supported by ConditionEngine._eval_condition
- **Files modified:** kiwoom_trader/gui/strategy_tab.py
- **Verification:** All tests pass, validation correctly uses the operator set
- **Committed in:** 14f1f32

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor -- local constant definition matches existing operator support. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 (Monitoring & Operations) is now complete with all 4 plans executed
- All GUI tabs operational with real data wiring
- Ready for Phase 5 (Backtest) which depends on Phase 3 strategy engine, not Phase 4

## Self-Check: PASSED

All 5 files verified present. All 3 task commits verified in git log.

---
*Phase: 04-monitoring-operations*
*Completed: 2026-03-14*
