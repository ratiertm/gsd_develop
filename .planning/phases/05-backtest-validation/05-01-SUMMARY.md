---
phase: 05-backtest-validation
plan: 01
subsystem: backtest
tags: [backtest, datasource, cost-model, replay-engine, kiwoom-api]

requires:
  - phase: 01-api-foundation
    provides: TRRequestQueue for throttled TR requests
  - phase: 03-data-pipeline-strategy-engine
    provides: StrategyManager, ConditionEngine, indicators, Candle dataclass
  - phase: 02-order-execution-risk-management
    provides: RiskConfig dataclass for risk parameters

provides:
  - DataSource ABC with get_candles contract
  - KiwoomDataSource parsing opt10081 daily candle data
  - CostConfig + calc_buy_cost/calc_sell_proceeds for Korean market costs
  - BacktestEngine replay loop reusing StrategyManager
  - BacktestResult dataclass for downstream consumers

affects: [05-02, 05-03]

tech-stack:
  added: []
  patterns: [DataSource ABC abstraction, candle-by-candle replay, fresh StrategyManager per run]

key-files:
  created:
    - kiwoom_trader/backtest/__init__.py
    - kiwoom_trader/backtest/data_source.py
    - kiwoom_trader/backtest/cost_model.py
    - kiwoom_trader/backtest/backtest_engine.py
    - tests/test_cost_model.py
    - tests/test_data_source.py
    - tests/test_backtest_engine.py
  modified:
    - kiwoom_trader/core/models.py
    - kiwoom_trader/config/settings.py

key-decisions:
  - "Fresh StrategyManager + ConditionEngine created per run() call to avoid stale indicator state"
  - "BacktestEngine handles execution itself — does NOT pass risk_manager/paper_trader to StrategyManager"
  - "Trailing stop only active when price above avg_price to prevent premature triggers"
  - "Korean market cost model: buy = commission + slippage; sell = commission + tax (0.18%) + slippage"

patterns-established:
  - "DataSource ABC: abstract get_candles(code, start_date, end_date, on_progress) for extensible data providers"
  - "Candle-by-candle replay: feed historical Candle objects directly to StrategyManager.on_candle_complete()"

requirements-completed: [BACK-01]

duration: 12min
completed: 2026-03-14
---

# Plan 05-01: BacktestEngine Core Summary

**DataSource ABC + CostModel (Korean market) + BacktestEngine candle-by-candle replay with SL/TP/trailing stop risk checks**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-03-14
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- DataSource ABC with KiwoomDataSource parsing opt10081 daily candle data with pagination
- CostConfig with Korean market specifics: buy/sell commission, sell-side tax 0.18%, configurable slippage
- BacktestEngine replay loop with fresh StrategyManager per run, risk checks (SL/TP/trailing stop), position limits, daily loss enforcement
- BacktestResult dataclass carrying trades, equity curve, and metric fields
- Settings.backtest_config property for config.json integration

## Task Commits

1. **Task 1: Data models, cost model, and DataSource with tests** - `43ddad2` (feat)
2. **Task 2: BacktestEngine replay loop with risk checks** - `90d5e34` (feat)

## Files Created/Modified
- `kiwoom_trader/backtest/__init__.py` - Module exports
- `kiwoom_trader/backtest/data_source.py` - DataSource ABC + KiwoomDataSource
- `kiwoom_trader/backtest/cost_model.py` - CostConfig, calc_buy_cost, calc_sell_proceeds
- `kiwoom_trader/backtest/backtest_engine.py` - BacktestEngine replay orchestrator
- `kiwoom_trader/core/models.py` - Added BacktestResult dataclass
- `kiwoom_trader/config/settings.py` - Added backtest config section + backtest_config property
- `tests/test_cost_model.py` - 11 cost model tests
- `tests/test_data_source.py` - 8 data source tests
- `tests/test_backtest_engine.py` - 11 BacktestEngine tests

## Decisions Made
- Fresh StrategyManager created per run to avoid stale indicator state between backtest runs
- Trailing stop only activates when price exceeds avg_price (prevents premature trigger on flat positions)
- BacktestEngine does not use RiskManager directly (QObject coupling); reimplements SL/TP/trailing stop with same RiskConfig values

## Deviations from Plan
None - plan executed as specified.

## Issues Encountered
- Test assertion mismatch: reason string used space ("stop loss") vs underscore ("stop_loss") — fixed test to match implementation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- BacktestEngine + DataSource + CostConfig ready for Plan 05-03 (UI wiring)
- BacktestResult ready for Plan 05-02 (PerformanceCalculator)

---
*Phase: 05-backtest-validation*
*Completed: 2026-03-14*
