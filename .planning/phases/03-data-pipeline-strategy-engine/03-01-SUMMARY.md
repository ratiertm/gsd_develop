---
phase: 03-data-pipeline-strategy-engine
plan: 01
subsystem: data-pipeline
tags: [candle, ohlcv, sma, ema, rsi, macd, bollinger, vwap, obv, incremental, tdd]

# Dependency graph
requires:
  - phase: 01-api-foundation
    provides: "FID constants, RealDataManager subscriber callback pattern"
  - phase: 02-order-execution-risk
    provides: "models.py (Order, Position, RiskConfig dataclasses)"
provides:
  - "Candle dataclass for OHLCV representation"
  - "CandleAggregator: tick-to-candle conversion with minute boundary detection"
  - "7 incremental indicator classes (SMA, EMA, RSI, MACD, Bollinger, VWAP, OBV)"
affects: [03-02-condition-engine, 03-03-strategy-manager, 05-backtest]

# Tech tracking
tech-stack:
  added: []
  patterns: ["incremental O(1) indicator update", "deque sliding window", "callback-based candle emission"]

key-files:
  created:
    - "kiwoom_trader/core/candle_aggregator.py"
    - "kiwoom_trader/core/indicators.py"
    - "tests/test_candle_aggregator.py"
    - "tests/test_indicators.py"
  modified:
    - "kiwoom_trader/core/models.py"

key-decisions:
  - "Pure Python indicators with collections.deque -- no TA-Lib or pandas-ta dependency"
  - "EMA seeded with first value, returns None until period count reached"
  - "RSI div-by-zero: 100.0 for all-gains, 0.0 for all-losses, 50.0 for no-change"
  - "CandleAggregator tracks cum_price_volume/cum_volume for downstream VWAP calculation"

patterns-established:
  - "Indicator update(value) -> result | None pattern for warmup handling"
  - "CandleAggregator register_callback pattern for downstream consumers"
  - "abs() at tick entry point for Kiwoom price sign convention"

requirements-completed: [TRAD-01]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 3 Plan 01: Data Pipeline Foundation Summary

**Candle dataclass, CandleAggregator (tick-to-OHLCV at minute boundaries), and 7 pure-Python incremental indicators (SMA, EMA, RSI, MACD, Bollinger, VWAP, OBV) with TDD**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T16:20:45Z
- **Completed:** 2026-03-13T16:24:24Z
- **Tasks:** 2 (TDD: 4 commits -- 2 RED + 2 GREEN)
- **Files modified:** 5

## Accomplishments
- Candle dataclass added to models.py with OHLCV + VWAP cumulative fields
- CandleAggregator converts FID-keyed tick dicts into completed Candle objects at configurable minute boundaries
- All 7 indicators implemented with incremental update and warmup-returns-None pattern
- RSI handles division-by-zero edge cases (all gains / all losses)
- VWAP supports daily reset for intraday calculation
- 32 new tests (9 candle + 23 indicator), all passing alongside 163 existing tests (195 total)

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Data models + CandleAggregator with tests**
   - `aa67e89` (test: failing tests for CandleAggregator - RED)
   - `97871a9` (feat: implement Candle dataclass and CandleAggregator - GREEN)

2. **Task 2: Seven incremental indicators with tests**
   - `2c577c1` (test: failing tests for 7 indicators - RED)
   - `96ed084` (feat: implement 7 incremental indicators - GREEN)

## Files Created/Modified
- `kiwoom_trader/core/models.py` - Added Candle dataclass (code, OHLCV, timestamp, cum_price_volume, cum_volume)
- `kiwoom_trader/core/candle_aggregator.py` - CandleAggregator with on_tick/register_callback, minute slot calculation, abs() for Kiwoom prices
- `kiwoom_trader/core/indicators.py` - SMAIndicator, EMAIndicator, RSIIndicator, MACDIndicator, BollingerBandsIndicator, VWAPIndicator, OBVIndicator
- `tests/test_candle_aggregator.py` - 9 tests for tick-to-candle conversion
- `tests/test_indicators.py` - 23 tests for all 7 indicators including warmup and edge cases

## Decisions Made
- Pure Python indicators with `collections.deque` -- no external indicator library needed for 7 indicators
- EMA seeded with first value (not SMA seed), returns None until period values processed
- RSI division-by-zero: returns 100.0 for all-gains, 0.0 for all-losses, 50.0 for zero-change edge case
- CandleAggregator tracks cumulative price*volume and cumulative volume per candle for downstream VWAP
- Bollinger Bands uses population stddev (N divisor, not N-1) per standard Bollinger specification

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Candle and indicator foundation ready for Plan 02 (ConditionEngine) to consume
- CandleAggregator.register_callback provides the hook for IndicatorEngine wiring
- All indicator classes follow uniform update() -> result | None interface for easy composition

---
*Phase: 03-data-pipeline-strategy-engine*
*Completed: 2026-03-14*
