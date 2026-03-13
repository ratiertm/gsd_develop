---
phase: 03-data-pipeline-strategy-engine
verified: 2026-03-14T12:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/6
  gaps_closed:
    - "VWAP resets on MarketHoursManager state change to TRADING via strategy_manager.reset_vwap()"
    - "StrategyManager cooldown resets daily alongside other daily resets"
  gaps_remaining: []
  regressions: []
---

# Phase 3: Data Pipeline & Strategy Engine Verification Report

**Phase Goal:** Technical indicators feed a condition engine that automatically generates buy/sell signals, completing the end-to-end automated trading loop.
**Verified:** 2026-03-14
**Status:** passed
**Re-verification:** Yes — after gap closure plan 03-04

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SMA, EMA, RSI, MACD, Bollinger Bands, VWAP, OBV compute correctly with incremental update and warmup | VERIFIED | `indicators.py`: all 7 classes present with `update()`/`update_candle()` returning None during warmup; deque-based O(1) SMA, EMAIndicator with count-based warmup, RSI with Wilder smoothing, MACD composing two EMAs + signal EMA, Bollinger with population stddev, VWAP cumulative, OBV directional |
| 2 | ConditionEngine evaluates composite AND/OR rules against indicator context and emits entry/exit signals | VERIFIED | `condition_engine.py`: recursive evaluate() with all 6 operators (gt, lt, gte, lte, cross_above, cross_below); missing keys return False gracefully. `strategy_manager.py` calls `self._condition_engine.evaluate(strategy.entry_rule, context)` and `evaluate(strategy.exit_rule, context)` |
| 3 | Complete automated trading loop runs in paper trading: data reception -> indicator calc -> condition eval -> risk validation -> order execution -> fill confirmation | VERIFIED | Pipeline wired in `main.py` lines 176-183: `real_data_manager.register_subscriber("주식체결", candle_aggregator.on_tick)` and `candle_aggregator.register_callback(strategy_manager.on_candle_complete)`. PaperTrader records trades to CSV with P&L. Integration test `test_rsi_buy_then_sell_with_csv` proves full flow. |
| 4 | Config.json strategies/watchlist sections load correctly through Settings | VERIFIED | `settings.py` `strategy_config` property returns mode, candle_interval_minutes, strategies list (2 presets: RSI_REVERSAL, MA_CROSSOVER), watchlist_strategies. Default config includes both presets with entry_rule/exit_rule keys matching StrategyManager parser. |
| 5 | VWAP resets on MarketHoursManager state change to TRADING via strategy_manager.reset_vwap() | VERIFIED | `main.py` lines 186-204: `_on_market_state_changed` callback registered via `market_hours.register_state_callback()`; callback calls `strategy_manager.reset_vwap()` when `new_state == MarketState.TRADING`. QTimer polls `check_state_transition()` every 10 s. No `pass` stub remains. Integration test `test_vwap_and_cooldown_reset_on_trading_start` asserts `vwap_instance._cum_pv == 0.0` and `vwap_instance._cum_vol == 0` after transition. |
| 6 | StrategyManager cooldown resets daily alongside other daily resets | VERIFIED | Same `_on_market_state_changed` callback at `main.py` line 191 calls `strategy_manager.reset_daily()` on TRADING entry. Comment-only stub is gone. Integration test asserts `len(strategy_manager._cooldowns) == 0` after state transition. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kiwoom_trader/core/models.py` | Candle, Signal, Condition, CompositeRule, StrategyConfig, TradeRecord dataclasses | VERIFIED | All 8 Phase 3 dataclasses present at lines 107-181. Existing Phase 2 models intact. |
| `kiwoom_trader/core/candle_aggregator.py` | CandleAggregator with on_tick/register_callback | VERIFIED | Full implementation: 114 lines, tick-to-OHLCV with minute slot calculation, abs() for Kiwoom prices, multiple code tracking, callback emission |
| `kiwoom_trader/core/indicators.py` | 7 incremental indicator classes | VERIFIED | All 7 classes present (226 lines): SMA, EMA, RSI, MACD, Bollinger, VWAP, OBV — all incremental, all return None during warmup (except OBV which always returns int) |
| `kiwoom_trader/core/condition_engine.py` | AND/OR rule evaluation engine | VERIFIED | 74 lines, ConditionEngine.evaluate() with recursive AND/OR and all 6 operators. Imports Condition and CompositeRule from models. |
| `kiwoom_trader/core/strategy_manager.py` | Strategy lifecycle, indicator management, signal routing, reset_vwap, reset_daily | VERIFIED | 329 lines: loads strategies, manages indicators per (code, strategy), builds context with prev values for cross detection, priority resolution, cooldown enforcement, live/paper routing. `reset_daily()` at line 319 clears `_cooldowns`. `reset_vwap()` at line 323 iterates all VWAPIndicator instances and calls `instance.reset()`. |
| `kiwoom_trader/core/paper_trader.py` | Virtual execution with CSV logging | VERIFIED | 190 lines: BUY/SELL execution, position tracking, P&L calculation on close, CSV append via csv.writer, get_summary() with win rate |
| `kiwoom_trader/config/settings.py` | strategy_config property with 2 presets | VERIFIED | Lines 127-135: strategy_config property present. Default config includes RSI_REVERSAL and MA_CROSSOVER presets with correct entry_rule/exit_rule keys. |
| `kiwoom_trader/core/__init__.py` | Phase 3 module exports | VERIFIED | Exports CandleAggregator, ConditionEngine, StrategyManager, PaperTrader, and all 7 indicator classes with try/except ImportError fallback. |
| `kiwoom_trader/core/market_hours.py` | State transition detection with on_state_changed callback | VERIFIED | `_previous_state: MarketState | None = None` at line 35; `_state_callbacks` at line 36; `register_state_callback()` at line 90-98; `check_state_transition()` at line 100-126. First call returns None (no spurious init transition). Subsequent calls compare against `_previous_state` and fire all callbacks on change. |
| `kiwoom_trader/main.py` | Full pipeline wiring with actual reset calls | VERIFIED | Pipeline wired (lines 142-214). CandleAggregator created and connected. `_on_market_state_changed` closure at lines 187-195 calls `reset_vwap()` and `reset_daily()`. `market_hours.register_state_callback()` at line 197. QTimer at lines 200-204 polls every 10 s. Zero `pass` stubs remain. |
| `tests/test_strategy_integration.py` | End-to-end pipeline integration test including reset flow | VERIFIED | 452 lines. Original 6 integration test classes intact. New `TestVWAPAndCooldownResetOnTradingStart` class at line 378 with `test_vwap_and_cooldown_reset_on_trading_start` verifying VWAP `_cum_pv == 0`, `_cum_vol == 0`, and `_cooldowns` empty after MARKET_OPEN_BUFFER -> TRADING transition. |
| `tests/test_market_hours.py` | State transition detection tests | VERIFIED | `TestStateTransition` class at line 161 with 5 tests covering: tuple return on change, None on no change, callback fires, BUFFER->TRADING detected, multiple callbacks all fire. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `candle_aggregator.py` | `models.py` | imports Candle dataclass | WIRED | Line 13: `from kiwoom_trader.core.models import Candle` |
| `candle_aggregator.py` | `config/constants.py` | FID.CURRENT_PRICE, FID.EXEC_VOLUME, FID.EXEC_TIME | WIRED | Line 12: `from kiwoom_trader.config.constants import FID`; used in on_tick() |
| `strategy_manager.py` | `condition_engine.py` | evaluates rules per strategy | WIRED | Lines 235, 248: `self._condition_engine.evaluate(strategy.entry_rule, context)` and `evaluate(strategy.exit_rule, context)` |
| `strategy_manager.py` | `indicators.py` | creates and updates indicator instances | WIRED | Lines 17-25: imports all 7 indicator classes; INDICATOR_CLASSES dict at lines 40-48; `_init_indicators()` creates instances; `_update_indicator()` calls update() |
| `strategy_manager.py` | `models.py` | emits Signal dataclass | WIRED | Lines 236-246 and 248-258: `Signal(code=code, side="BUY", ...)` and `Signal(code=code, side="SELL", ...)` |
| `paper_trader.py` | CSV | writes trade records | WIRED | Lines 155-171: `_write_trade()` uses `csv.writer` to append rows |
| `main.py` | `real_data.py` | register_subscriber for CandleAggregator | WIRED | Lines 176-178: `real_data_manager.register_subscriber("주식체결", candle_aggregator.on_tick)` |
| `main.py` | `strategy_manager.py` | register_callback -> on_candle_complete | WIRED | Line 183: `candle_aggregator.register_callback(strategy_manager.on_candle_complete)` |
| `main.py` | VWAP reset | strategy_manager.reset_vwap() on TRADING state | WIRED | Lines 189-191: `if new_state == MarketState.TRADING: strategy_manager.reset_vwap()` inside `_on_market_state_changed` callback registered at line 197 |
| `main.py` | daily reset | strategy_manager.reset_daily() on TRADING state | WIRED | Line 191: `strategy_manager.reset_daily()` in same `_on_market_state_changed` callback. Comment-only stub removed. |
| `market_hours.py` | `main.py` | check_state_transition() polled by QTimer | WIRED | Lines 200-204: QTimer created, `timeout.connect(market_hours.check_state_transition)`, started at 10 000 ms |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TRAD-01 | 03-01-PLAN.md, 03-03-PLAN.md, 03-04-PLAN.md | 기술적 지표 계산 — 이동평균(SMA/EMA), RSI, MACD, 볼린저밴드 | SATISFIED | All 7 indicators in indicators.py with incremental update, warmup handling. CandleAggregator converts ticks to candles. StrategyManager wires indicators to candle stream. VWAP daily reset now correctly clears cumulative state at trading day start, ensuring accurate VWAP from day 1 onward. |
| TRAD-02 | 03-02-PLAN.md, 03-03-PLAN.md, 03-04-PLAN.md | 복합 매매 조건 엔진 — 기술지표 + 가격/거래량 조합 조건 평가 | SATISFIED | ConditionEngine evaluates AND/OR composite rules with 6 operators. StrategyManager manages 2 preset strategies. Signals flow to PaperTrader. Cooldown daily reset ensures no carry-over state between trading days. Integration tests prove end-to-end including reset flow. |

Both TRAD-01 and TRAD-02 are fully satisfied. The two lifecycle gaps (VWAP reset, cooldown daily reset) that previously prevented operational correctness in multi-day use are now closed.

### Anti-Patterns Found

No blockers or warnings. The `pass` stub at lines 187-190 and comment-only daily reset at line 193 that were flagged in the initial verification have been replaced with working code.

### Human Verification Required

#### 1. RSI Divergence Test

**Test:** Start the application in paper mode. Register stock 005930 with RSI_REVERSAL strategy. Let the system run through a morning session where RSI dips below 30, then check that the BUY trade is recorded in `logs/trades.csv`.
**Expected:** CSV has a BUY row for 005930 with price matching the tick at the time RSI crossed below 30.
**Why human:** Requires actual Kiwoom API connection and live tick flow; cannot simulate full API event chain in automated tests.

#### 2. VWAP Multi-Day Accuracy

**Test:** Run paper trading across two consecutive trading days. On day 2, verify that VWAP values for registered stocks reset at market open transition (MARKET_OPEN_BUFFER -> TRADING, nominally 09:05).
**Expected:** Day 2 VWAP values start fresh; not contaminated by day 1 cumulative data. Log line "Trading day started (MARKET_OPEN_BUFFER -> TRADING): VWAP and cooldowns reset" should appear each morning.
**Why human:** The reset mechanism depends on QTimer polling against real wall-clock time and the live Kiwoom event loop; cannot drive live state transitions in unit tests.

#### 3. MA Crossover Signal Timing

**Test:** Monitor MA_CROSSOVER strategy on a stock exhibiting a clear uptrend breakout. Verify a BUY signal fires at the candle where EMA(5) crosses above EMA(20) — not one candle late.
**Expected:** Signal timestamp matches the crossover candle, not the following one.
**Why human:** Cross detection timing edge cases depend on exact EMA convergence which varies with real price data.

## Gaps Summary

No gaps remain. Both gaps identified in the initial verification are closed:

**Gap 1 (closed): VWAP daily reset**

`market_hours.register_state_callback(_on_market_state_changed)` at main.py line 197 registers a closure that calls `strategy_manager.reset_vwap()` when `new_state == MarketState.TRADING`. A QTimer polls `check_state_transition()` every 10 s to detect the MARKET_OPEN_BUFFER -> TRADING transition. The integration test `test_vwap_and_cooldown_reset_on_trading_start` asserts `vwap_instance._cum_pv == 0.0` and `vwap_instance._cum_vol == 0` after simulated transition.

**Gap 2 (closed): Cooldown daily reset**

The same `_on_market_state_changed` callback calls `strategy_manager.reset_daily()` (main.py line 191) alongside the VWAP reset. The integration test asserts `len(strategy_manager._cooldowns) == 0` after the transition, confirming carry-over state from the previous day cannot block new-day signals.

**Root cause resolution:** `MarketHoursManager` received `check_state_transition()` and `register_state_callback()` methods (market_hours.py lines 90-126). This replaced the polling-without-event-emission design that caused both gaps. All 5 new state transition tests in `TestStateTransition` cover the critical MARKET_OPEN_BUFFER -> TRADING path.

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
