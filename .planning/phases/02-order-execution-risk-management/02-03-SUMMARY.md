---
phase: 02-order-execution-risk-management
plan: 03
subsystem: core
tags: [position-tracker, market-hours, pnl, risk-limits, trading-control]

# Dependency graph
requires:
  - phase: 02-order-execution-risk-management
    provides: "Position, RiskConfig dataclasses, MarketState enum, mock_risk_config fixture"
provides:
  - "PositionTracker with position CRUD, real-time P&L, symbol weight and max position checks"
  - "MarketHoursManager with 6 market states and time-based trading permission"
affects: [02-04-risk-manager]

# Tech tracking
tech-stack:
  added: []
  patterns: ["time_func injection for deterministic time testing", "Config-driven time boundaries parsed from RiskConfig strings"]

key-files:
  created:
    - kiwoom_trader/core/position_tracker.py
    - kiwoom_trader/core/market_hours.py
    - tests/test_position_tracker.py
    - tests/test_market_hours.py
  modified: []

key-decisions:
  - "PositionTracker computes risk prices (stop_loss, take_profit, trailing_stop) from RiskConfig on add_position"
  - "MarketHoursManager uses time_func injection (not datetime.now mocking) for deterministic testing"
  - "Daily P&L includes both realized and unrealized per RESEARCH.md Pitfall 4 recommendation"

patterns-established:
  - "Time injection pattern: time_func callable for testable time-dependent code"
  - "Position lifecycle: add -> update_price/update_from_chejan -> remove on qty==0"

requirements-completed: [TRAD-04, RISK-04]

# Metrics
duration: 2min
completed: 2026-03-13
---

# Phase 2 Plan 3: Position Tracker & Market Hours Summary

**PositionTracker with real-time P&L (realized+unrealized) and position limits, plus MarketHoursManager with 6-state KRX time control blocking auctions and restricting new buys after 15:15**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-13T14:36:15Z
- **Completed:** 2026-03-13T14:38:35Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- PositionTracker tracks held positions with add/update/remove, computes unrealized P&L per tick, accumulates daily realized P&L, and enforces per-symbol weight (20%) and max concurrent positions (5) limits
- MarketHoursManager determines correct MarketState for any given time using 6 states parsed from RiskConfig time boundaries, blocking all orders during auction periods (08:30-09:00, 15:20-15:30) and restricting new buys after 15:15
- 52 new tests (25 position tracker + 27 market hours) all passing, full suite 117 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: PositionTracker with P&L and position limit checks** (TDD)
   - RED: `81064cc` (test) - 25 failing tests for position CRUD, P&L, limits
   - GREEN: `ac97c94` (feat) - Implementation passes all 25 tests

2. **Task 2: MarketHoursManager with time-based trading permission** (TDD)
   - RED: `50933f5` (test) - 27 failing tests for market states and permissions
   - GREEN: `18e9aec` (feat) - Implementation passes all 27 tests

## Files Created/Modified
- `kiwoom_trader/core/position_tracker.py` - PositionTracker class with position management, P&L calculation, and limit enforcement
- `kiwoom_trader/core/market_hours.py` - MarketHoursManager class with time-based market state determination and trading permission
- `tests/test_position_tracker.py` - 25 tests covering position CRUD, P&L, weight/position limits, daily reset
- `tests/test_market_hours.py` - 27 tests covering all 6 market states, boundary conditions, permissions, custom config

## Decisions Made
- PositionTracker computes stop_loss/take_profit/trailing_stop prices from RiskConfig percentages on add_position (not deferred to RiskManager) for immediate availability
- MarketHoursManager uses time_func injection pattern (callable returning datetime.time) instead of mocking datetime.now -- simpler, more explicit, zero mock overhead
- Daily P&L calculation includes both realized and unrealized per RESEARCH.md Pitfall 4 -- prevents false-safety when unrealized losses are ignored

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PositionTracker ready for RiskManager (02-04) daily loss limit calculation
- MarketHoursManager ready for RiskManager (02-04) pre-order time checks
- Both classes use RiskConfig consistently, enabling config-driven parameter changes

---
*Phase: 02-order-execution-risk-management*
*Completed: 2026-03-13*
