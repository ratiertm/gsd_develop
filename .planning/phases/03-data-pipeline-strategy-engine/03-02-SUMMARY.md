---
phase: 03-data-pipeline-strategy-engine
plan: 02
subsystem: strategy-engine
tags: [condition-engine, strategy-manager, paper-trading, signal, cooldown, priority, csv, tdd]

# Dependency graph
requires:
  - phase: 03-data-pipeline-strategy-engine
    provides: "Candle dataclass, 7 incremental indicators (SMA, EMA, RSI, MACD, Bollinger, VWAP, OBV)"
  - phase: 02-order-execution-risk
    provides: "RiskManager.validate_order, OrderManager.submit_order, models.py"
provides:
  - "ConditionEngine: AND/OR composite rule evaluation with 6 operators"
  - "StrategyManager: strategy lifecycle, indicator management, signal routing, cooldown, priority resolution"
  - "PaperTrader: virtual trade execution with CSV logging and P&L tracking"
  - "Signal, Condition, CompositeRule, StrategyConfig, TradeRecord dataclasses"
  - "Two preset strategies: RSI reversal and MA crossover"
affects: [03-03-integration-wiring, 05-backtest]

# Tech tracking
tech-stack:
  added: []
  patterns: ["composite rule tree evaluation", "per-stock per-strategy indicator instances", "EMA difference for cross detection", "cooldown with daily reset"]

key-files:
  created:
    - "kiwoom_trader/core/condition_engine.py"
    - "kiwoom_trader/core/strategy_manager.py"
    - "kiwoom_trader/core/paper_trader.py"
    - "tests/test_condition_engine.py"
    - "tests/test_strategy_manager.py"
    - "tests/test_paper_trader.py"
  modified:
    - "kiwoom_trader/core/models.py"

key-decisions:
  - "MA crossover uses EMA difference (short-long) with cross_above/cross_below on value=0 for clean cross detection"
  - "ConditionEngine returns False for missing indicator keys (graceful warmup handling)"
  - "PaperTrader qty calculation: int(capital * weight_pct / 100 / price) -- zero qty skips trade"
  - "Signal conflict resolution: highest priority wins per (code, side) pair"

patterns-established:
  - "Config-driven strategy loading: dict -> StrategyConfig with CompositeRule trees"
  - "Lazy indicator instance creation per (stock_code, strategy_name) pair"
  - "Previous value tracking per (code, strategy, indicator) for cross detection"
  - "CSV trade logging with TradeRecord dataclass"

requirements-completed: [TRAD-02]

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 3 Plan 02: Condition Engine & Strategy Manager Summary

**AND/OR composite condition engine, StrategyManager with 2 preset strategies (RSI reversal + MA crossover), priority/cooldown signal management, and PaperTrader with CSV P&L logging**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-13T16:26:44Z
- **Completed:** 2026-03-13T16:32:06Z
- **Tasks:** 2 (TDD: 4 commits -- 2 RED + 2 GREEN)
- **Files modified:** 7

## Accomplishments
- ConditionEngine evaluates AND/OR/nested CompositeRule trees with 6 operators (gt/lt/gte/lte/cross_above/cross_below)
- StrategyManager with 2-arg on_candle_complete(code, candle) matching CandleAggregator callback contract
- Internal indicator instance management per stock per strategy, with previous value tracking for cross detection
- Two preset strategies: RSI reversal (RSI<30 buy, RSI>70 sell, priority=10) and MA crossover (EMA cross, priority=20)
- Priority-based conflict resolution, time-based cooldown with daily reset, VWAP reset delegation
- PaperTrader logs virtual trades to CSV with position tracking and P&L calculation
- 43 new tests (22 condition engine + 15 strategy manager + 6 paper trader), all passing alongside 195 existing tests (238 total)

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Signal/Strategy models + ConditionEngine with tests**
   - `65ae134` (test: failing tests for ConditionEngine - RED)
   - `2c38da1` (feat: implement Signal/Strategy models and ConditionEngine - GREEN)

2. **Task 2: StrategyManager + PaperTrader with tests**
   - `787004d` (test: failing tests for StrategyManager and PaperTrader - RED)
   - `294d2c6` (feat: implement StrategyManager and PaperTrader - GREEN)

## Files Created/Modified
- `kiwoom_trader/core/models.py` - Added Condition, CompositeRule, Signal, StrategyConfig, TradeRecord dataclasses
- `kiwoom_trader/core/condition_engine.py` - ConditionEngine with recursive AND/OR evaluation, 6 operators, graceful missing key handling
- `kiwoom_trader/core/strategy_manager.py` - StrategyManager with strategy loading, indicator management, signal evaluation, conflict resolution, cooldown, routing
- `kiwoom_trader/core/paper_trader.py` - PaperTrader with virtual buy/sell execution, CSV logging, position tracking, P&L, summary stats
- `tests/test_condition_engine.py` - 22 tests for all operators, composite rules, nesting, missing keys
- `tests/test_strategy_manager.py` - 15 tests for loading, indicators, RSI/MA signals, priority, cooldown, routing, VWAP reset
- `tests/test_paper_trader.py` - 6 tests for buy/sell execution, CSV logging, P&L, summary

## Decisions Made
- MA crossover cross detection: compute EMA difference (short - long) and use cross_above/cross_below on value=0, avoiding fixed threshold comparison
- ConditionEngine returns False for missing indicator keys instead of raising -- allows graceful warmup period
- PaperTrader quantity calculation uses int(capital * weight_pct / 100 / price); zero qty skips trade silently
- Signal conflict resolution keeps highest priority per (code, side) pair; BUY and SELL resolved independently

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ConditionEngine + StrategyManager + PaperTrader ready for Plan 03 integration wiring
- StrategyManager.on_candle_complete matches CandleAggregator.register_callback contract
- Signal routing to RiskManager->OrderManager ready for live mode
- Paper mode enables safe strategy validation before live deployment

## Self-Check: PASSED

All 7 files verified on disk. All 4 commit hashes verified in git log.

---
*Phase: 03-data-pipeline-strategy-engine*
*Completed: 2026-03-14*
