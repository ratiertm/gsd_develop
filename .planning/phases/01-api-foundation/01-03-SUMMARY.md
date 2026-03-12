---
phase: 01-api-foundation
plan: 03
subsystem: api
tags: [qtimer, rate-limiting, real-time-data, fifo-queue, observer-pattern, pyqt-signal]

# Dependency graph
requires:
  - phase: 01-api-foundation/01-02
    provides: KiwoomAPI, EventHandlerRegistry, SessionManager
provides:
  - TRRequestQueue for rate-limited TR dispatching (4s intervals, FIFO)
  - RealDataManager for real-time data subscription and FID dispatch
  - main.py wiring all Phase 1 components into runnable application
  - api/__init__.py exporting all 5 core classes
affects: [02-order-execution, all-future-plans]

# Tech tracking
tech-stack:
  added: []
  patterns: [QTimer rate-limited FIFO queue, observer pattern for real-time FID dispatch, auto-incrementing screen number management, PyQt5 conditional import for cross-platform]

key-files:
  created:
    - kiwoom_trader/api/tr_request_queue.py
    - kiwoom_trader/api/real_data.py
    - kiwoom_trader/main.py
  modified:
    - kiwoom_trader/api/__init__.py
    - tests/test_tr_queue.py
    - tests/test_real_data.py

key-decisions:
  - "api/__init__.py uses try/except for KiwoomAPI import (PyQt5 fallback) so other components remain importable on non-Windows"
  - "RealDataManager extracts 6 standard FIDs (CURRENT_PRICE, VOLUME, EXEC_VOLUME, OPEN_PRICE, HIGH_PRICE, LOW_PRICE) within event context"
  - "TRRequestQueue uses PyQt5 import fallback pattern (same as session_manager.py) for cross-platform testing"

patterns-established:
  - "Rate-limited queue: QTimer interval + deque FIFO + immediate first dispatch + timer stop on empty"
  - "Real-time dispatch: subscribe -> track -> on_real_data extracts FIDs -> dispatch dict to observers"
  - "Screen number auto-generation: counter from SCREEN.REAL_BASE, formatted as 4-digit string"

requirements-completed: [CONN-02, CONN-03]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 1 Plan 03: TR Queue, Real-time Data, and Main Entry Point Summary

**QTimer rate-limited TR queue at 4s intervals, real-time FID extraction with observer dispatch, and main.py wiring all 5 Phase 1 components**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-12T20:43:33Z
- **Completed:** 2026-03-12T20:46:50Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- TRRequestQueue enforces 4-second minimum interval between TR dispatches in FIFO order with queue_empty signal
- RealDataManager handles SetRealReg subscription lifecycle with auto screen numbers, extracts 6 standard FIDs within event context, dispatches to observers
- main.py wires KiwoomAPI, EventHandlerRegistry, TRRequestQueue, SessionManager, RealDataManager with full event routing
- Full test suite 32/32 green (10 new tests: 5 TR queue + 5 real data)
- Phase 1 requirements CONN-01, CONN-02, CONN-03 all addressed

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TRRequestQueue and RealDataManager (TDD)**
   - `0c604d9` (test) - RED: failing tests for TRRequestQueue and RealDataManager
   - `477364e` (feat) - GREEN: TRRequestQueue and RealDataManager implementation

2. **Task 2: Create main.py entry point wiring all components**
   - `5ccdf79` (feat) - main.py and api/__init__.py exports

_Note: TDD Task 1 has two commits (test then feat)_

## Files Created/Modified
- `kiwoom_trader/api/tr_request_queue.py` - Rate-limited TR request dispatcher with QTimer and deque FIFO
- `kiwoom_trader/api/real_data.py` - Real-time data subscription, FID extraction, and observer dispatch
- `kiwoom_trader/main.py` - Application entry point wiring all 5 core components
- `kiwoom_trader/api/__init__.py` - Package exports for all 5 API classes
- `tests/test_tr_queue.py` - 5 tests for enqueue, FIFO, timer stop, pending count, interval
- `tests/test_real_data.py` - 5 tests for subscribe, auto screen, dispatch, unsubscribe, tracking

## Decisions Made
- api/__init__.py uses try/except for KiwoomAPI import so other components remain importable on macOS without PyQt5
- RealDataManager extracts 6 standard FIDs (CURRENT_PRICE, VOLUME, EXEC_VOLUME, OPEN_PRICE, HIGH_PRICE, LOW_PRICE) in every on_real_data call
- TRRequestQueue follows same PyQt5 import fallback pattern established in session_manager.py

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PyQt5 import fallback in api/__init__.py**
- **Found during:** Task 2 (main.py verification)
- **Issue:** api/__init__.py importing KiwoomAPI caused PyQt5 ImportError on macOS, breaking all test collection
- **Fix:** Wrapped KiwoomAPI import in try/except, set to None on ImportError
- **Files modified:** kiwoom_trader/api/__init__.py
- **Verification:** Full test suite 32/32 green on macOS without PyQt5
- **Committed in:** 5ccdf79 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for cross-platform testing. Production behavior unchanged when PyQt5 is available.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 1 components complete: KiwoomAPI, EventHandlerRegistry, TRRequestQueue, SessionManager, RealDataManager
- main.py wires everything and starts Qt event loop
- Phase 2 (Order Execution) can build on top of these components
- CONN-01, CONN-02, CONN-03 requirements all addressed
- Full test suite: 32 tests green

---
## Self-Check: PASSED

All 7 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 01-api-foundation*
*Completed: 2026-03-13*
