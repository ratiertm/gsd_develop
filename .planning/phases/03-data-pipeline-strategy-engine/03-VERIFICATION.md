---
phase: 03-data-pipeline-strategy-engine
verified: 2026-03-14T00:00:00Z
status: gaps_found
score: 4/6 must-haves verified
re_verification: false
gaps:
  - truth: "VWAP resets on MarketHoursManager state change to TRADING via strategy_manager.reset_vwap()"
    status: failed
    reason: "main.py lines 187-190 contain only a pass statement inside the if market_hours block. strategy_manager.reset_vwap() is documented in comments but never actually called."
    artifacts:
      - path: "kiwoom_trader/main.py"
        issue: "Lines 187-190: if market_hours is not None: pass — no actual reset_vwap() call"
    missing:
      - "Call strategy_manager.reset_vwap() inside the if market_hours is not None block in main.py"
      - "Needs a concrete trigger mechanism (event, daily hook, or timer) to call reset_vwap() at trading day start"
  - truth: "StrategyManager cooldown resets daily alongside other daily resets"
    status: failed
    reason: "strategy_manager.reset_daily() is mentioned only in a comment at line 193 of main.py. The method exists on StrategyManager but is never called from main.py."
    artifacts:
      - path: "kiwoom_trader/main.py"
        issue: "Line 193: comment says 'strategy_manager.reset_daily() should be called' but no actual call exists"
    missing:
      - "Call strategy_manager.reset_daily() from a daily-reset trigger (MarketHoursManager event, QTimer, or equivalent)"
---

# Phase 3: Data Pipeline & Strategy Engine Verification Report

**Phase Goal:** Technical indicators feed a condition engine that automatically generates buy/sell signals, completing the end-to-end automated trading loop.
**Verified:** 2026-03-14
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SMA, EMA, RSI, MACD, Bollinger Bands, VWAP, OBV compute correctly with incremental update and warmup | VERIFIED | `indicators.py`: all 7 classes present with `update()`/`update_candle()` returning None during warmup; deque-based O(1) SMA, EMAIndicator with count-based warmup, RSI with Wilder smoothing, MACD composing two EMAs + signal EMA, Bollinger with population stddev, VWAP cumulative, OBV directional |
| 2 | ConditionEngine evaluates composite AND/OR rules against indicator context and emits entry/exit signals | VERIFIED | `condition_engine.py`: recursive evaluate() with all 6 operators (gt, lt, gte, lte, cross_above, cross_below); missing keys return False gracefully. `strategy_manager.py` calls `self._condition_engine.evaluate(strategy.entry_rule, context)` and `evaluate(strategy.exit_rule, context)` |
| 3 | Complete automated trading loop runs in paper trading: data reception -> indicator calc -> condition eval -> risk validation -> order execution -> fill confirmation | VERIFIED | Pipeline wired in `main.py` lines 175-182: `real_data_manager.register_subscriber("주식체결", candle_aggregator.on_tick)` and `candle_aggregator.register_callback(strategy_manager.on_candle_complete)`. PaperTrader records trades to CSV with P&L. Integration test `test_rsi_buy_then_sell_with_csv` proves full flow. |
| 4 | Config.json strategies/watchlist sections load correctly through Settings | VERIFIED | `settings.py` `strategy_config` property returns mode, candle_interval_minutes, strategies list (2 presets: RSI_REVERSAL, MA_CROSSOVER), watchlist_strategies. Default config includes both presets with entry_rule/exit_rule keys matching StrategyManager parser. |
| 5 | VWAP resets on MarketHoursManager state change to TRADING via strategy_manager.reset_vwap() | FAILED | `main.py` lines 187-190: `if market_hours is not None: pass` — reset_vwap() is documented only in comments, never called. The method exists on StrategyManager (line 323-327 of strategy_manager.py) but has no caller in main.py. |
| 6 | StrategyManager cooldown resets daily alongside other daily resets | FAILED | `main.py` line 193: comment reads "strategy_manager.reset_daily() should be called when new trading day starts" but no actual call exists anywhere in main.py. Method exists on StrategyManager (line 319-321) but is never invoked. |

**Score:** 4/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kiwoom_trader/core/models.py` | Candle, Signal, Condition, CompositeRule, StrategyConfig, TradeRecord dataclasses | VERIFIED | All 8 Phase 3 dataclasses present at lines 107-181. Existing Phase 2 models intact. |
| `kiwoom_trader/core/candle_aggregator.py` | CandleAggregator with on_tick/register_callback | VERIFIED | Full implementation: 114 lines, tick-to-OHLCV with minute slot calculation, abs() for Kiwoom prices, multiple code tracking, callback emission |
| `kiwoom_trader/core/indicators.py` | 7 incremental indicator classes | VERIFIED | All 7 classes present (226 lines): SMA, EMA, RSI, MACD, Bollinger, VWAP, OBV — all incremental, all return None during warmup (except OBV which always returns int) |
| `kiwoom_trader/core/condition_engine.py` | AND/OR rule evaluation engine | VERIFIED | 74 lines, ConditionEngine.evaluate() with recursive AND/OR and all 6 operators. Imports Condition and CompositeRule from models. |
| `kiwoom_trader/core/strategy_manager.py` | Strategy lifecycle, indicator management, signal routing | VERIFIED | 329 lines: loads strategies, manages indicators per (code, strategy), builds context with prev values for cross detection, priority resolution, cooldown enforcement, live/paper routing |
| `kiwoom_trader/core/paper_trader.py` | Virtual execution with CSV logging | VERIFIED | 190 lines: BUY/SELL execution, position tracking, P&L calculation on close, CSV append via csv.writer, get_summary() with win rate |
| `kiwoom_trader/config/settings.py` | strategy_config property with 2 presets | VERIFIED | Lines 127-135: strategy_config property present. Default config includes RSI_REVERSAL and MA_CROSSOVER presets with correct entry_rule/exit_rule keys. |
| `kiwoom_trader/core/__init__.py` | Phase 3 module exports | VERIFIED | Exports CandleAggregator, ConditionEngine, StrategyManager, PaperTrader, and all 7 indicator classes with try/except ImportError fallback. |
| `kiwoom_trader/main.py` | Full pipeline wiring, contains candle_aggregator | VERIFIED (partial) | Pipeline wired (lines 141-198). CandleAggregator created and connected. BUT: VWAP reset and daily reset calls are stubs (pass + comments only). |
| `tests/test_strategy_integration.py` | End-to-end pipeline integration test | VERIFIED | 348 lines, 6 integration tests using real instances: TestFullPipelinePaperMode, TestMACrossoverSignal, TestCooldownPreventsRapidSignals, TestDisabledStrategyNoSignal, TestMultipleStrategiesPriority, TestCandleAggregatorStrategyManagerWiring |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `candle_aggregator.py` | `models.py` | imports Candle dataclass | WIRED | Line 13: `from kiwoom_trader.core.models import Candle` |
| `candle_aggregator.py` | `config/constants.py` | FID.CURRENT_PRICE, FID.EXEC_VOLUME, FID.EXEC_TIME | WIRED | Line 12: `from kiwoom_trader.config.constants import FID`; used in on_tick() |
| `strategy_manager.py` | `condition_engine.py` | evaluates rules per strategy | WIRED | Lines 235, 248: `self._condition_engine.evaluate(strategy.entry_rule, context)` and `evaluate(strategy.exit_rule, context)` |
| `strategy_manager.py` | `indicators.py` | creates and updates indicator instances | WIRED | Lines 17-25: imports all 7 indicator classes; INDICATOR_CLASSES dict at lines 40-48; `_init_indicators()` creates instances; `_update_indicator()` calls update() |
| `strategy_manager.py` | `models.py` | emits Signal dataclass | WIRED | Lines 236-246 and 248-258: `Signal(code=code, side="BUY", ...)` and `Signal(code=code, side="SELL", ...)` |
| `paper_trader.py` | CSV | writes trade records | WIRED | Lines 155-171: `_write_trade()` uses `csv.writer` to append rows |
| `main.py` | `real_data.py` | register_subscriber for CandleAggregator | WIRED | Line 176-178: `real_data_manager.register_subscriber("주식체결", candle_aggregator.on_tick)` |
| `main.py` | `strategy_manager.py` | register_callback -> on_candle_complete | WIRED | Line 182: `candle_aggregator.register_callback(strategy_manager.on_candle_complete)` |
| `main.py` | VWAP reset | strategy_manager.reset_vwap() on TRADING state | NOT_WIRED | Lines 187-190: `if market_hours is not None: pass` — no actual reset_vwap() call |
| `main.py` | daily reset | strategy_manager.reset_daily() on new trading day | NOT_WIRED | Line 193: comment only, no actual call |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TRAD-01 | 03-01-PLAN.md, 03-03-PLAN.md | 기술적 지표 계산 — 이동평균(SMA/EMA), RSI, MACD, 볼린저밴드 | SATISFIED | All 7 indicators in indicators.py with incremental update, warmup handling. CandleAggregator converts ticks to candles. StrategyManager wires indicators to candle stream. |
| TRAD-02 | 03-02-PLAN.md, 03-03-PLAN.md | 복합 매매 조건 엔진 — 기술지표 + 가격/거래량 조합 조건 평가 | SATISFIED | ConditionEngine evaluates AND/OR composite rules with 6 operators. StrategyManager manages 2 preset strategies. Signals flow to PaperTrader. Integration tests prove end-to-end. |

Both TRAD-01 and TRAD-02 are satisfied at the functional level. The two gaps (VWAP reset, cooldown daily reset) represent operational lifecycle hooks that do not prevent the core indicator-to-signal pipeline from functioning.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `kiwoom_trader/main.py` | 187-190 | `if market_hours is not None: pass` — reset_vwap() block is a no-op | Warning | VWAP values accumulate across trading days without reset; VWAP indicator will produce incorrect values on day 2+ of continuous operation |
| `kiwoom_trader/main.py` | 192-194 | Comment-only wiring: "strategy_manager.reset_daily() should be called..." — never called | Warning | Cooldown state never clears between trading days; after day 1, all signals for codes that fired within cooldown window will be permanently blocked |

### Human Verification Required

#### 1. RSI Divergence Test

**Test:** Start the application in paper mode. Register stock 005930 with RSI_REVERSAL strategy. Let the system run through a morning session where RSI dips below 30, then check that the BUY trade is recorded in `logs/trades.csv`.
**Expected:** CSV has a BUY row for 005930 with price matching the tick at the time RSI crossed below 30.
**Why human:** Requires actual Kiwoom API connection and live tick flow; cannot simulate full API event chain in automated tests.

#### 2. VWAP Multi-Day Accuracy

**Test:** Run paper trading across two consecutive trading days. On day 2, verify that VWAP values for registered stocks reset at market open (09:05).
**Expected:** Day 2 VWAP values start fresh; not contaminated by day 1 cumulative data.
**Why human:** The VWAP reset wiring is not implemented (gap found). This test will currently FAIL — including it to document the gap's observable impact.

#### 3. MA Crossover Signal Timing

**Test:** Monitor MA_CROSSOVER strategy on a stock exhibiting a clear uptrend breakout. Verify a BUY signal fires at the candle where EMA(5) crosses above EMA(20) — not one candle late.
**Expected:** Signal timestamp matches the crossover candle, not the following one.
**Why human:** Cross detection timing edge cases depend on exact EMA convergence which varies with real price data.

## Gaps Summary

Two gaps prevent full goal achievement as specified in the PLAN-03 must_haves:

**Gap 1: VWAP daily reset not wired (main.py lines 187-190)**

The plan required `strategy_manager.reset_vwap()` to be called when MarketHoursManager transitions to TRADING state. The implementation has `if market_hours is not None: pass` — the block is intentionally empty with only explanatory comments. `strategy_manager.reset_vwap()` exists and works (StrategyManager delegates to VWAPIndicator.reset()), but no trigger calls it. This means VWAP computes cumulative values across all days without resetting, producing incorrect VWAP from day 2 onward.

**Gap 2: Cooldown daily reset not wired (main.py line 193)**

The plan required `strategy_manager.reset_daily()` to be called alongside existing daily resets. The method exists and clears `self._cooldowns`, but no code in main.py calls it. The comment at line 193 explicitly acknowledges this omission. Without this call, a signal that fired near the end of trading day 1 will still be within its 300s cooldown at the start of day 2, silently blocking the first signal of the new day.

**Root cause:** Both gaps share the same root cause — `MarketHoursManager` lacks a `state_changed` event (confirmed in 03-03-SUMMARY.md decision notes: "MarketHoursManager lacks event emission"). The original plan assumed an event-based hook, but the Phase 2 implementation of MarketHoursManager uses polling (`get_market_state()`). The fix requires either: (a) adding an event/signal to MarketHoursManager for state transitions, or (b) calling reset methods from a QTimer or daily initialization path in main.py.

The core indicator-to-signal pipeline (success criteria 1, 2, and the bulk of 3) is fully implemented and tested with 6 integration tests. The gaps affect operational correctness in multi-day production use but do not block single-day paper trading validation.

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
