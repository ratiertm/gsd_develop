---
phase: 01-api-foundation
plan: 02
subsystem: api
tags: [pyqt5, qaxwidget, com-wrapper, event-routing, session-management, exponential-backoff, loguru]

# Dependency graph
requires:
  - phase: 01-api-foundation/01-01
    provides: Settings, constants, logging, pytest fixtures
provides:
  - KiwoomAPI QAxWidget COM wrapper with pyqtSignals
  - EventHandlerRegistry for TR/real-time event routing (observer pattern)
  - SessionManager with exponential backoff reconnection and subscription restore
affects: [01-03-PLAN, all-future-plans]

# Tech tracking
tech-stack:
  added: []
  patterns: [QAxWidget COM wrapper with pyqtSignal, observer pattern for real-time handlers, exponential backoff reconnection, PyQt5 import fallback for cross-platform testing]

key-files:
  created:
    - kiwoom_trader/api/kiwoom_api.py
    - kiwoom_trader/api/event_handler.py
    - kiwoom_trader/api/session_manager.py
  modified:
    - tests/test_event_handler.py
    - tests/test_session_manager.py

key-decisions:
  - "PyQt5 import fallback in session_manager.py enables testing on non-Windows (MagicMock as QObject/QTimer stand-in)"
  - "EventHandlerRegistry is standalone (no COM dependency) for pure Python unit testing"
  - "KiwoomAPI not unit-tested (requires Windows OCX); tested via mock_kiwoom_api fixture in dependent modules"

patterns-established:
  - "COM wrapper pattern: KiwoomAPI aggregates QAxWidget, emits pyqtSignals, all dynamicCall at DEBUG level"
  - "Event routing pattern: Dict[str, Callable] for TR (one per rq_name), Dict[str, list[Callable]] for real (observer)"
  - "Session lifecycle pattern: heartbeat timer + exponential backoff reconnect + subscription restore"

requirements-completed: [CONN-01]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 1 Plan 02: Kiwoom OCX Wrapper and Session Manager Summary

**QAxWidget COM wrapper with pyqtSignal event routing, observer-pattern real-time dispatch, and exponential backoff auto-reconnection with subscription restore**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-12T20:38:02Z
- **Completed:** 2026-03-12T20:41:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- KiwoomAPI wraps all Kiwoom COM calls (login, TR, real-time) via QAxWidget dynamicCall with pyqtSignals
- EventHandlerRegistry routes TR responses by rq_name and real-time data by real_type with observer pattern
- SessionManager implements heartbeat detection, exponential backoff reconnection (5s base, 60s cap, 5 max retries), and SetRealReg subscription restore
- 13 new tests (6 event handler + 7 session manager), full suite 24/24 green

## Task Commits

Each task was committed atomically:

1. **Task 1: Create KiwoomAPI wrapper and EventHandlerRegistry**
   - `c42224a` (test) - RED: failing tests for EventHandlerRegistry
   - `4fc23ad` (feat) - GREEN: KiwoomAPI and EventHandlerRegistry implementation

2. **Task 2: Create SessionManager with auto-reconnect and subscription restore**
   - `b41df2c` (test) - RED: failing tests for SessionManager
   - `68c8cbf` (feat) - GREEN: SessionManager implementation

_Note: TDD tasks have two commits each (test then feat)_

## Files Created/Modified
- `kiwoom_trader/api/kiwoom_api.py` - QAxWidget COM wrapper with pyqtSignals for all Kiwoom API calls
- `kiwoom_trader/api/event_handler.py` - Event routing registry for TR and real-time data
- `kiwoom_trader/api/session_manager.py` - Session lifecycle with heartbeat, reconnect, and subscription restore
- `tests/test_event_handler.py` - 6 tests for TR and real-time handler registration/dispatch
- `tests/test_session_manager.py` - 7 tests for login, backoff, heartbeat, and subscription restore

## Decisions Made
- PyQt5 import fallback with MagicMock in session_manager.py enables cross-platform testing (macOS dev without PyQt5)
- EventHandlerRegistry kept standalone (no COM imports) so all tests run as pure Python
- KiwoomAPI itself is not unit-tested (requires Windows + Kiwoom OCX); dependent modules use mock_kiwoom_api fixture

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added PyQt5 import fallback in session_manager.py**
- **Found during:** Task 2 (SessionManager GREEN phase)
- **Issue:** PyQt5 not available on macOS dev environment; module-level import prevented test collection
- **Fix:** Added try/except for PyQt5 imports with MagicMock fallback (QTimer, QObject, pyqtSignal)
- **Files modified:** kiwoom_trader/api/session_manager.py
- **Verification:** All 7 SessionManager tests pass on macOS without PyQt5
- **Committed in:** 68c8cbf (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for development/testing on non-Windows. Production code path unchanged when PyQt5 is available.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- KiwoomAPI, EventHandlerRegistry, and SessionManager ready for import by Plan 01-03
- Plan 01-03 can build TRRequestQueue and RealDataManager on top of these modules
- CONN-01 fully covered (login, session, auto-reconnect, subscription restore)

---
## Self-Check: PASSED

All 6 files verified present. All 4 commit hashes verified in git log.

---
*Phase: 01-api-foundation*
*Completed: 2026-03-13*
