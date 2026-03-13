---
phase: 04-monitoring-operations
plan: 03
subsystem: ui
tags: [pyqtgraph, candlestick, chart, indicators, watchlist, trade-markers]

# Dependency graph
requires:
  - phase: 04-monitoring-operations
    provides: MainWindow with QTabWidget, GUI widgets package, PyQt5 fallback pattern
  - phase: 03-strategy-engine
    provides: CandleAggregator, indicators (SMA, EMA, RSI, MACD, Bollinger, VWAP, OBV), Candle dataclass
provides:
  - CandlestickItem GraphicsObject with set_data for live chart updates
  - ChartTab with price plot, indicator toggles, watchlist panel, trade markers
  - IndicatorSubChart helpers for RSI/MACD/OBV sub-plots
  - 120-candle sliding window buffer per stock code
affects: [04-04-strategy-tab]

# Tech tracking
tech-stack:
  added: []
  patterns: [candlestick-qpicture-prerender, sliding-window-buffer, indicator-toggle-visibility, trade-marker-scatter]

key-files:
  created:
    - kiwoom_trader/gui/widgets/candlestick_item.py
    - kiwoom_trader/gui/widgets/indicator_chart.py
    - kiwoom_trader/gui/chart_tab.py
    - tests/test_chart_widgets.py
  modified: []

key-decisions:
  - "CandlestickItem uses QPicture pre-rendering for paint performance"
  - "Sliding window of 120 candles (~2 hours of 1-min data) for memory/render efficiency"
  - "Sub-chart visibility toggle via setMaximumHeight(0) hide / 100px show"
  - "VWAPIndicator uses update_candle(h,l,c,v) not update(cum_pv, cum_vol) per actual implementation"

patterns-established:
  - "Candlestick color convention: #26A69A (green up), #EF5350 (red down), #FFFFFF (wick)"
  - "Trade markers: ScatterPlotItem with symbol='t' (buy up) and 't1' (sell down)"
  - "Per-code data buffers: defaultdict(list) pattern for multi-stock chart data"

requirements-completed: [GUI-02]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 4 Plan 03: Chart Tab Summary

**Real-time candlestick chart with pyqtgraph CandlestickItem, indicator overlays (SMA/EMA/Bollinger/VWAP/RSI/MACD/OBV), watchlist navigation, and trade markers**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T18:17:05Z
- **Completed:** 2026-03-13T18:20:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- CandlestickItem with QPicture pre-rendering, green/red color coding, and 120-candle sliding window
- ChartTab with price chart, indicator checkbox toolbar, watchlist panel, and trade marker scatter
- IndicatorSubChart helpers creating linked RSI/MACD/OBV sub-plots with reference lines
- 8 tests verifying data conversion, sliding window, toggles, markers, watchlist, and candle buffer management

## Task Commits

Each task was committed atomically:

1. **Task 1: CandlestickItem + IndicatorSubChart widgets** - `9854092` (feat)
2. **Task 2 RED: Failing tests for ChartTab data logic** - `8afd30a` (test)
3. **Task 2 GREEN: ChartTab implementation** - `0b9924b` (feat)

## Files Created/Modified
- `kiwoom_trader/gui/widgets/candlestick_item.py` - CandlestickItem GraphicsObject with QPicture pre-rendering and sliding window
- `kiwoom_trader/gui/widgets/indicator_chart.py` - Helper functions for RSI/MACD/OBV sub-chart creation
- `kiwoom_trader/gui/chart_tab.py` - ChartTab widget with price chart, overlays, sub-charts, watchlist, trade markers
- `tests/test_chart_widgets.py` - 8 tests for chart data logic (TDD)

## Decisions Made
- CandlestickItem uses QPicture pre-rendering (draw once, paint fast) per pyqtgraph RESEARCH pattern
- 120-candle sliding window balances ~2 hours of 1-min data visibility with render performance
- Sub-chart toggle uses setMaximumHeight(0) for hide, 100px for show (no remove/re-add)
- Test isolation via sys.modules blocking (set to None) instead of MagicMock to avoid staticmethod inheritance issues

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test mock strategy for PyQt5-less environments**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** MagicMock as QWidget base class broke staticmethod resolution on ChartTab
- **Fix:** Changed test setup from sys.modules MagicMock to sys.modules None (forces ImportError, uses object fallback)
- **Files modified:** tests/test_chart_widgets.py
- **Verification:** All 8 tests pass
- **Committed in:** 0b9924b (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test infrastructure fix necessary for correct test execution. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. pyqtgraph renders in the existing PyQt5 MainWindow.

## Next Phase Readiness
- ChartTab ready to be integrated into MainWindow tab index 1 (Chart tab)
- CandleAggregator.register_callback(chart_tab.on_new_candle) for live updates
- Trade markers ready for integration with order execution signals

---
*Phase: 04-monitoring-operations*
*Completed: 2026-03-14*
