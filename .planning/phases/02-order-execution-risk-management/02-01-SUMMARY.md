---
phase: 02-order-execution-risk-management
plan: 01
subsystem: core
tags: [dataclass, enum, kiwoom-api, risk-config, order-model, chejan-fid]

# Dependency graph
requires:
  - phase: 01-api-foundation
    provides: "Settings class, constants.py (FID/SCREEN/LOGIN_ERROR), config.json, conftest.py fixtures"
provides:
  - "Order, Position, RiskConfig dataclasses for order lifecycle tracking"
  - "OrderState enum with VALID_TRANSITIONS state machine map"
  - "CHEJAN_FID constants (35 FIDs) for GetChejanData parsing"
  - "OrderType, HogaGb, ORDER_ERROR, MarketState, MarketOperation constants"
  - "Settings.risk_config property returning RiskConfig from config.json"
  - "Settings.account_no property reading KIWOOM_ACCOUNT_NO env var"
  - "mock_risk_config, mock_position_tracker test fixtures"
affects: [02-02-order-manager, 02-03-position-tracker, 02-04-risk-manager]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Enum-based order state machine with explicit transition map", "Dataclass DTOs for order/position/risk config", "Config-driven risk parameters with user-locked defaults"]

key-files:
  created:
    - kiwoom_trader/core/__init__.py
    - kiwoom_trader/core/models.py
    - tests/test_models.py
    - tests/test_config_risk.py
  modified:
    - kiwoom_trader/config/constants.py
    - kiwoom_trader/config/settings.py
    - config.json
    - tests/conftest.py

key-decisions:
  - "OrderState uses stdlib Enum with auto() values; VALID_TRANSITIONS is a plain dict mapping state to set of legal next states"
  - "CHEJAN_FID as plain class (not Enum) since FID values overlap between gubun=0 and gubun=1 contexts"
  - "RiskConfig dataclass defaults match user-locked parameters from CONTEXT.md exactly"
  - "Settings.risk_config uses **dict unpacking for config.json values with RiskConfig() fallback"

patterns-established:
  - "State machine pattern: Enum states + dict transition map (no library dependency)"
  - "Risk config pattern: config.json -> Settings property -> typed dataclass"
  - "Test fixture pattern: mock_risk_config and mock_position_tracker for Phase 2 tests"

requirements-completed: [TRAD-03, TRAD-04, RISK-01, RISK-02, RISK-04]

# Metrics
duration: 5min
completed: 2026-03-13
---

# Phase 2 Plan 1: Data Models & Constants Summary

**Order/Position/RiskConfig dataclasses with 8-state OrderState machine, 35 CHEJAN_FID constants, and config.json-driven risk parameters**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-13T14:28:52Z
- **Completed:** 2026-03-13T14:33:29Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- OrderState enum (8 states) with VALID_TRANSITIONS map enforcing legal state changes; terminal states (FILLED, CANCELLED, REJECTED) have no outgoing transitions
- Order, Position, RiskConfig dataclasses with user-locked defaults from CONTEXT.md (stop_loss=-2%, take_profit=+3%, trailing_stop=1.5%, etc.)
- 35 CHEJAN_FID constants for GetChejanData parsing covering both order/execution (gubun=0) and balance (gubun=1) fields
- OrderType, HogaGb, ORDER_ERROR (28 error codes), MarketState (6 states), MarketOperation (FID 215 values) constants
- Settings.risk_config property loading config.json risk section into typed RiskConfig dataclass
- 42 tests passing (26 model/constant tests + 7 config/risk tests + existing Phase 1 suite)

## Task Commits

Each task was committed atomically:

1. **Task 1: Core data models and constants** (TDD)
   - RED: `7a31519` (test) - 26 failing tests for models and constants
   - GREEN: `1f3fbfb` (feat) - Implementation passes all 26 tests

2. **Task 2: Config.json and Settings risk extension** (TDD)
   - RED: `a6708e4` (test) - 7 failing tests for risk config
   - GREEN: `624ff1f` (feat) - Implementation passes all 7 tests

## Files Created/Modified
- `kiwoom_trader/core/__init__.py` - Empty init for new core module
- `kiwoom_trader/core/models.py` - OrderState, OrderSide, VALID_TRANSITIONS, Order, Position, RiskConfig
- `kiwoom_trader/config/constants.py` - Extended with CHEJAN_FID, OrderType, HogaGb, ORDER_ERROR, MarketState, MarketOperation, SCREEN.ORDER_BASE
- `kiwoom_trader/config/settings.py` - Extended with risk_config property, account_no property, risk defaults
- `config.json` - Added risk section with 14 user-configurable parameters
- `tests/test_models.py` - 26 tests for all models and constants
- `tests/test_config_risk.py` - 7 tests for risk config and settings
- `tests/conftest.py` - Added mock_risk_config, mock_position_tracker fixtures; updated tmp_config_file

## Decisions Made
- OrderState uses stdlib Enum with auto() values; VALID_TRANSITIONS is a plain dict mapping state to set of legal next states (simpler than `transitions` library for 8 states)
- CHEJAN_FID as plain class (not Enum) since FID values overlap between gubun=0 and gubun=1 contexts (e.g., CURRENT_PRICE=10 used in both)
- RiskConfig dataclass defaults match user-locked parameters from CONTEXT.md exactly (no deviation)
- split_interval_sec=45 as recommended by RESEARCH.md open question resolution

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Python venv needed to be created (.venv) since no virtual environment existed; installed pytest, python-dotenv, loguru into it

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All type contracts (Order, Position, RiskConfig) ready for OrderManager (02-02)
- CHEJAN_FID constants ready for ChejanData parsing in event handler extension (02-02)
- MarketState enum ready for MarketHoursManager (02-03)
- RiskConfig loading ready for RiskManager (02-04)
- mock_risk_config and mock_position_tracker fixtures ready for Phase 2 test suites

---
*Phase: 02-order-execution-risk-management*
*Completed: 2026-03-13*
