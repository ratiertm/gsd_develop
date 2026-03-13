---
phase: 05-backtest-validation
verified: 2026-03-14T00:00:00Z
status: gaps_found
score: 2/3 success criteria verified
re_verification: false
gaps:
  - truth: "The backtest engine replays historical OHLCV data through the same Strategy Engine and Risk Manager used in live trading, via the abstract DataSource interface"
    status: partial
    reason: "BacktestEngine core replay loop is fully implemented and tested. However main.py passes a raw list (settings._config.get('strategies', [])) as strategy_configs to BacktestEngine, but StrategyManager expects a dict with 'strategies', 'mode', 'watchlist_strategies' keys and calls config.get(). At runtime this raises AttributeError: 'list' object has no attribute 'get' when a backtest is triggered from the UI."
    artifacts:
      - path: "kiwoom_trader/main.py"
        issue: "Line 386: strategy_configs = settings._config.get('strategies', []) passes a list, but BacktestEngine/StrategyManager requires a dict with 'strategies' key"
    missing:
      - "Change line 386 in main.py to pass the full strategy config dict: strategy_configs = settings.strategy_config (which already returns the correctly-shaped dict with mode, strategies, watchlist_strategies)"
human_verification:
  - test: "Run full backtest workflow via UI"
    expected: "Strategy tab shows Backtest button; clicking opens input dialog; submitting triggers QProgressDialog; on completion BacktestDialog shows equity curve, drawdown, price+trades, and monthly returns chart tabs"
    why_human: "Visual rendering of charts, dialog layout, and chart correctness cannot be verified programmatically without a display server"
---

# Phase 5: Backtest & Validation Verification Report

**Phase Goal:** Users can test strategies against historical data before risking real capital, with realistic cost modeling and comprehensive performance metrics
**Verified:** 2026-03-14
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The backtest engine replays historical OHLCV data through the same Strategy Engine and Risk Manager used in live trading, via the abstract DataSource interface | PARTIAL | BacktestEngine.run() feeds candles to fresh StrategyManager.on_candle_complete(); DataSource ABC and KiwoomDataSource exist; but main.py passes a list as strategy_configs (wiring bug — see gaps) |
| 2 | Performance statistics (total return, MDD, win rate, profit factor, Sharpe ratio) are computed and displayed after each backtest run | VERIFIED | performance.py implements all 5 core metrics + 4 additional; compute_all_metrics fills BacktestResult; BacktestDialog shows 11-row summary table; 45 test cases all pass |
| 3 | Backtest results are visualized with equity curves, drawdown charts, and trade markers on price charts | VERIFIED (automated) / HUMAN NEEDED (visual) | BacktestDialog has 4 chart tabs: Equity Curve, Drawdown, Price+Trades (with CandlestickItem + BUY/SELL scatter markers), Monthly Returns; smoke tests skipped (no PyQt5 on macOS) |

**Score:** 2/3 truths fully verified (third is partial — code exists but has a runtime wiring bug)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kiwoom_trader/backtest/data_source.py` | DataSource ABC + KiwoomDataSource | VERIFIED | DataSource ABC with abstract get_candles; KiwoomDataSource parses opt10081, paginates, filters, sorts ascending |
| `kiwoom_trader/backtest/cost_model.py` | CostConfig dataclass + cost functions | VERIFIED | CostConfig with Korean defaults; calc_buy_cost and calc_sell_proceeds both implemented with slippage/tax/commission |
| `kiwoom_trader/backtest/backtest_engine.py` | BacktestEngine replay orchestrator | VERIFIED | Full replay loop, SL/TP/trailing-stop risk checks, position limits, daily loss cap, forced close at end, fresh StrategyManager per run |
| `kiwoom_trader/backtest/performance.py` | Pure function performance calculators | VERIFIED | 11 pure functions + compute_all_metrics aggregator; stdlib only; all edge cases handled |
| `kiwoom_trader/backtest/backtest_worker.py` | BacktestWorker QThread | VERIFIED | QThread with progress/finished/error signals; two-phase (Downloading/Simulating); compute_all_metrics called before emitting finished |
| `kiwoom_trader/gui/backtest_dialog.py` | BacktestDialog QDialog with summary table and chart tabs | VERIFIED | QDialog with 11-row summary table and 4 chart tabs (Equity Curve, Drawdown, Price+Trades, Monthly Returns); CandlestickItem reused |
| `kiwoom_trader/gui/strategy_tab.py` | StrategyTab with Backtest button | VERIFIED | Backtest QPushButton present; _on_backtest_clicked shows input dialog with code, dates, capital; callback invoked on OK |
| `kiwoom_trader/core/models.py` | BacktestResult dataclass | VERIFIED | BacktestResult dataclass with trades, equity_curve, initial_capital, final_capital, and all 9 metric fields |
| `kiwoom_trader/config/settings.py` | backtest config section in Settings | VERIFIED | _default_config has backtest section; Settings.backtest_config property returns CostConfig |
| `kiwoom_trader/main.py` | Phase 5 wiring | PARTIAL | Imports correct; worker/dialog wiring present; but strategy_configs passed as list instead of dict (runtime bug) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backtest_engine.py` | `strategy_manager.py` | `StrategyManager.on_candle_complete(code, candle)` | WIRED | Line 100: `signals = strategy_manager.on_candle_complete(candle.code, candle)` |
| `backtest_engine.py` | `cost_model.py` | `calc_buy_cost / calc_sell_proceeds` | WIRED | Both imported and used in _execute_buy and _execute_sell |
| `data_source.py` | `tr_request_queue.py` | `TRRequestQueue.enqueue for opt10081` | WIRED | Line 99: `self._tr_queue.enqueue(tr_code="opt10081", ...)` |
| `strategy_tab.py` | `backtest_worker.py` | `BacktestWorker instantiation on button click` | WIRED (indirect) | StrategyTab calls `_on_backtest_requested` callback; main.py creates BacktestWorker in that callback |
| `backtest_worker.py` | `backtest_engine.py` | `BacktestEngine.run()` in QThread.run() | WIRED | Line 92: `result = self._engine.run(candles, on_progress=...)` |
| `backtest_worker.py` | `performance.py` | `compute_all_metrics on BacktestResult` | WIRED | Lines 98-100: imports and calls `compute_all_metrics(result)` |
| `backtest_dialog.py` | `candlestick_item.py` | `CandlestickItem reuse for price chart` | WIRED | Line 233: `from kiwoom_trader.gui.widgets.candlestick_item import CandlestickItem` used in _create_price_chart |
| `main.py` | `strategy_tab._on_backtest_requested` | Callback assignment | PARTIAL | Line 443 sets attribute directly after tab creation; functional but strategy_configs passed as list (bug) |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BACK-01 | 05-01 | DataSource ABC, KiwoomDataSource, BacktestEngine replay | PARTIAL | All code exists; runtime bug in main.py wiring prevents full end-to-end activation |
| BACK-02 | 05-02 | Performance analytics: total return, MDD, win rate, profit factor, Sharpe | SATISFIED | performance.py + compute_all_metrics; 45 test cases pass |
| BACK-03 | 05-03 | Visualization: equity curve, drawdown, price+trades charts | SATISFIED (pending human visual check) | BacktestDialog with 4 chart tabs; smoke tests skip without PyQt5 on macOS |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `kiwoom_trader/main.py` | 386 | `settings._config.get("strategies", [])` passed as `strategy_configs` to `BacktestEngine` which requires a `dict` with `strategies` key | Blocker | BacktestEngine passes this directly to StrategyManager which calls `.get("strategies", [])` on it — `list.get()` raises `AttributeError` at runtime when user clicks Backtest |

No TODO/FIXME/PLACEHOLDER comments found in any Phase 5 files.
No stub implementations (empty returns, console-only handlers) found.

---

## Human Verification Required

### 1. Full Backtest UI Workflow

**Test:** Run `python -m kiwoom_trader.main` (after fixing the strategy_configs bug), navigate to Strategy tab, click "Backtest", enter stock code "005930", set date range to last 3 months, click OK.
**Expected:** QProgressDialog appears showing "Downloading..." then "Simulating..." progress, followed by BacktestDialog opening with a summary metrics table (11 rows) and 4 chart tabs rendering correctly.
**Why human:** Chart rendering quality, layout correctness, and dialog visual appearance require a display server and human judgment.

### 2. Chart Content Verification

**Test:** With BacktestDialog open after a completed backtest, inspect each chart tab.
**Expected:**
- "Equity Curve" tab: line chart of capital over time starting at initial capital
- "Drawdown" tab: inverted area chart showing percentage drawdown with red fill
- "Price + Trades" tab: candlestick chart with green up-triangle markers at BUY positions and red down-triangle markers at SELL positions
- "Monthly Returns" tab: bar chart with green bars for positive months, red for negative
**Why human:** Correctness of chart data binding and visual marker positioning cannot be verified without rendering.

---

## Gaps Summary

One blocker gap prevents full goal achievement: the wiring in `main.py` passes a list of strategy dicts directly as `strategy_configs` to `BacktestEngine`, but `BacktestEngine` passes it to `StrategyManager` which expects a `dict` with `strategies`, `mode`, and `watchlist_strategies` keys. Calling `.get()` on a list raises `AttributeError` at runtime.

The fix is a one-line change: replace `settings._config.get("strategies", [])` with `settings.strategy_config` on line 386 of `main.py`. The `settings.strategy_config` property already returns the correctly-shaped dict.

All other Phase 5 code is substantive, correctly wired, and fully tested (90 tests pass, 7 skipped due to headless macOS environment — all 7 are PyQt5 smoke tests that correctly skip without a display).

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
