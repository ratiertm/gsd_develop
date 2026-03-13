# Phase 3: Data Pipeline & Strategy Engine - Research

**Researched:** 2026-03-14
**Domain:** Technical indicator incremental calculation, condition engine, automated trading signal pipeline
**Confidence:** HIGH

## Summary

Phase 3 transforms raw tick data from the existing RealDataManager into actionable trading signals. The pipeline is: tick data -> CandleAggregator (OHLCV 분봉) -> IndicatorEngine (7 indicators, incremental) -> ConditionEngine (AND/OR rules) -> StrategyManager (signal priority, cooldown) -> RiskManager.validate_order() -> OrderManager.submit_order(). A paper trading mode intercepts at the final step, logging virtual trades to CSV instead of submitting real orders.

All 7 indicators (SMA, EMA, RSI, MACD, Bollinger Bands, VWAP, OBV) have well-established incremental formulas that update in O(1) per new candle (except SMA/Bollinger Bands which need a sliding window of size N). No external indicator library is needed -- pure Python with `collections.deque` for windows is sufficient and avoids C compilation dependencies (TA-Lib) that would complicate Windows deployment on top of the Kiwoom OCX environment.

**Primary recommendation:** Implement all indicators as pure Python classes with a common `update(candle) -> value` interface. Use `collections.deque(maxlen=N)` for sliding windows. No third-party indicator libraries.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- 분봉 기반 계산 -- 틱 데이터를 실시간으로 분봉 OHLCV로 집계 (TR 요청 없음)
- 분봉 주기는 config.json에서 설정 가능 (기본값 제공)
- 인디케이터 업데이트는 분봉 완성 시점에만 (진행 중 봉에서는 재계산 안 함)
- 장 시작 시 워밍업: 충분한 분봉 수집될 때까지 신호 없음 (예: SMA(20)이면 20분봉 후 첫 신호)
- 증분 계산 (incremental) -- 전체 윈도우 재계산이 아닌 새 봉 추가 시 업데이트
- 7개 인디케이터: SMA, EMA, RSI, MACD, Bollinger Bands, VWAP, OBV
- 전략별 내장 파라미터 -- 각 전략 프리셋에 인디케이터 + 파라미터 포함
- AND/OR 복합 조건 조합
- 진입(entry) + 청산(exit) 조건을 하나의 전략에 통합 정의
- 기본 프리셋 2개: RSI 역발 전략, 이동평균 교차 전략
- 가격/거래량 조건 포함 가능
- 전략 설정은 config.json 내 strategies 섹션에 저장
- 종목당 여러 전략 동시 적용 가능
- 신호 충돌 시 전략별 priority 설정으로 우선순위 결정
- 감시 종목 목록은 config.json에서 설정 (종목별 적용 전략 지정)
- 전략별 enabled 플래그로 장 중 개별 on/off 제어 가능
- 신호 발생 -> RiskManager.validate_order() -> OrderManager.submit_order() 즉시 실행
- 동일 종목 중복 신호: 쿨다운 적용
- 기본 주문 유형: 시장가
- 페이퍼 트레이딩 모드 포함 (mode: "paper" / "live")
- 가상 손익 계산: 신호 발생 시점의 현재가를 가상 체결가로 사용
- 거래 기록: CSV 파일 (trades.csv)

### Claude's Discretion
- IndicatorEngine 클래스 설계 및 증분 계산 알고리즘 구현
- CandleAggregator 틱->분봉 변환 내부 구현
- ConditionEngine 규칙 평가 엔진 아키텍처
- StrategyManager 전략 로드/관리 구조
- 분봉 주기 기본값 (1분/3분/5분 중 선택)
- 쿨다운 시간 기본값
- CSV 파일 컬럼 구조

### Deferred Ideas (OUT OF SCOPE)
- 전략 자동 최적화 (파라미터 그리드 서치/유전 알고리즘) -- v2 STRT-03
- 전체 시장 스캔으로 조건 충족 종목 자동 탐색 -- v2 범위
- 멀티 타임프레임 분석 (1분봉 + 5분봉 동시) -- 복잡도 높음, v2 검토

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRAD-01 | 기술적 지표 계산 -- 이동평균(SMA/EMA), RSI, MACD, 볼린저밴드 | Incremental formulas for all 7 indicators documented in Architecture Patterns; pure Python O(1) update per candle |
| TRAD-02 | 복합 매매 조건 엔진 -- 기술지표 + 가격/거래량 조합 조건 평가 | ConditionEngine AND/OR tree evaluation, StrategyManager signal flow, 2 preset strategies documented |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `collections.deque` | 3.14 | Sliding window for SMA, Bollinger Bands | O(1) append/popleft, maxlen auto-eviction |
| Python stdlib `math.sqrt` | 3.14 | Standard deviation for Bollinger Bands | No numpy dependency needed for single values |
| Python stdlib `csv` | 3.14 | Paper trading trade log | Simple, no dependencies |
| Python stdlib `dataclasses` | 3.14 | Candle, Signal, StrategyConfig models | Already used throughout project |
| Python stdlib `datetime` | 3.14 | Candle timestamps, cooldown tracking | Already used in models.py |
| loguru | (installed) | Logging | Already used throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyQt5 pyqtSignal | 5.15.10 | Component-to-component signals | CandleAggregator -> IndicatorEngine -> ConditionEngine signal chain |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure Python indicators | TA-Lib | TA-Lib requires C compilation, problematic on Windows with Kiwoom OCX. Only 7 indicators needed -- pure Python is simpler |
| Pure Python indicators | pandas-ta | Adds heavy pandas dependency for simple calculations. Overkill for streaming single-value updates |
| deque sliding window | numpy rolling | numpy adds dependency for trivial operations on small windows (< 200 values) |

**Installation:**
```bash
# No new packages needed -- all stdlib + existing dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
kiwoom_trader/
├── core/
│   ├── models.py          # + Candle, Signal, StrategyConfig, TradeRecord dataclasses
│   ├── candle_aggregator.py   # Tick -> OHLCV candle aggregation
│   ├── indicators.py      # 7 indicator classes with common interface
│   ├── condition_engine.py    # AND/OR rule evaluation
│   ├── strategy_manager.py    # Strategy lifecycle, signal routing, cooldown
│   └── paper_trader.py    # Paper trading mode: virtual execution + CSV logging
├── config/
│   └── settings.py        # + strategies/indicators/watchlist config loading
```

### Pattern 1: Candle Dataclass & Aggregation
**What:** CandleAggregator subscribes to RealDataManager "주식체결" events, accumulates ticks into OHLCV candles, emits completed candles.
**When to use:** Every tick received from Kiwoom API.

```python
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

@dataclass
class Candle:
    """Single OHLCV candle."""
    code: str
    open: int
    high: int
    low: int
    close: int
    volume: int
    timestamp: datetime
    # For VWAP: cumulative price*volume
    cum_price_volume: float = 0.0
    cum_volume: int = 0

class CandleAggregator:
    """Aggregates ticks into candles per stock code.

    Subscribes to RealDataManager as "주식체결" observer.
    Emits completed candles via callback or pyqtSignal.
    """
    def __init__(self, interval_minutes: int = 1):
        self._interval = interval_minutes
        self._building: dict[str, dict] = {}  # code -> partial candle data
        self._callbacks: list = []

    def on_tick(self, code: str, data_dict: dict):
        """RealDataManager subscriber callback.

        Extracts price/volume from FID dict, updates building candle.
        When minute boundary crossed, finalizes candle and notifies.
        """
        price = abs(int(data_dict.get(10, "0") or "0"))  # FID.CURRENT_PRICE
        volume = abs(int(data_dict.get(15, "0") or "0"))  # FID.EXEC_VOLUME
        exec_time = data_dict.get(20, "")  # FID.EXEC_TIME (HHMMSS)

        if price == 0:
            return

        # Determine which candle slot this tick belongs to
        minute_slot = self._get_minute_slot(exec_time)

        building = self._building.get(code)
        if building is None or building["slot"] != minute_slot:
            # Finalize previous candle if exists
            if building is not None:
                self._finalize_candle(code, building)
            # Start new candle
            self._building[code] = {
                "slot": minute_slot,
                "open": price, "high": price,
                "low": price, "close": price,
                "volume": 0, "timestamp": datetime.now(),
            }
            building = self._building[code]

        # Update building candle
        building["high"] = max(building["high"], price)
        building["low"] = min(building["low"], price)
        building["close"] = price
        building["volume"] += volume
```

### Pattern 2: Common Indicator Interface (Incremental)
**What:** All indicators implement `update(candle) -> float | None` returning None until warmup complete.
**When to use:** Every completed candle.

```python
from collections import deque
from math import sqrt

class SMAIndicator:
    """Simple Moving Average with O(1) incremental update."""
    def __init__(self, period: int):
        self._period = period
        self._window = deque(maxlen=period)
        self._sum = 0.0

    def update(self, value: float) -> float | None:
        if len(self._window) == self._period:
            self._sum -= self._window[0]  # Remove oldest
        self._window.append(value)
        self._sum += value
        if len(self._window) < self._period:
            return None  # Warmup
        return self._sum / self._period

class EMAIndicator:
    """Exponential Moving Average: EMA_t = alpha * value + (1-alpha) * EMA_{t-1}"""
    def __init__(self, period: int):
        self._period = period
        self._alpha = 2.0 / (period + 1)
        self._ema: float | None = None
        self._count = 0

    def update(self, value: float) -> float | None:
        self._count += 1
        if self._ema is None:
            self._ema = value  # Seed with first value
            if self._count < self._period:
                return None
            return self._ema
        self._ema = self._alpha * value + (1 - self._alpha) * self._ema
        if self._count < self._period:
            return None
        return self._ema

class RSIIndicator:
    """RSI with Wilder's smoothing: avg_gain/loss rolling update."""
    def __init__(self, period: int = 14):
        self._period = period
        self._prev_close: float | None = None
        self._avg_gain: float = 0.0
        self._avg_loss: float = 0.0
        self._count = 0
        self._gains: list[float] = []
        self._losses: list[float] = []

    def update(self, close: float) -> float | None:
        if self._prev_close is None:
            self._prev_close = close
            return None

        change = close - self._prev_close
        self._prev_close = close
        gain = max(change, 0)
        loss = abs(min(change, 0))
        self._count += 1

        if self._count <= self._period:
            self._gains.append(gain)
            self._losses.append(loss)
            if self._count == self._period:
                self._avg_gain = sum(self._gains) / self._period
                self._avg_loss = sum(self._losses) / self._period
                self._gains.clear()
                self._losses.clear()
                return self._compute_rsi()
            return None

        # Wilder's smoothing
        self._avg_gain = (self._avg_gain * (self._period - 1) + gain) / self._period
        self._avg_loss = (self._avg_loss * (self._period - 1) + loss) / self._period
        return self._compute_rsi()

    def _compute_rsi(self) -> float:
        if self._avg_loss == 0:
            return 100.0
        rs = self._avg_gain / self._avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

class MACDIndicator:
    """MACD = EMA(fast) - EMA(slow), Signal = EMA(MACD, signal_period)."""
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self._fast_ema = EMAIndicator(fast)
        self._slow_ema = EMAIndicator(slow)
        self._signal_ema = EMAIndicator(signal)
        self._slow_period = slow

    def update(self, value: float) -> tuple[float, float, float] | None:
        fast = self._fast_ema.update(value)
        slow = self._slow_ema.update(value)
        if fast is None or slow is None:
            return None
        macd_line = fast - slow
        signal_line = self._signal_ema.update(macd_line)
        if signal_line is None:
            return None
        histogram = macd_line - signal_line
        return (macd_line, signal_line, histogram)

class BollingerBandsIndicator:
    """Bollinger Bands = SMA +/- K * StdDev over sliding window."""
    def __init__(self, period: int = 20, num_std: float = 2.0):
        self._period = period
        self._num_std = num_std
        self._window = deque(maxlen=period)

    def update(self, value: float) -> tuple[float, float, float] | None:
        self._window.append(value)
        if len(self._window) < self._period:
            return None
        mean = sum(self._window) / self._period
        variance = sum((x - mean) ** 2 for x in self._window) / self._period
        std = sqrt(variance)
        return (mean + self._num_std * std, mean, mean - self._num_std * std)

class VWAPIndicator:
    """Intraday VWAP = cumulative(typical_price * volume) / cumulative(volume).

    Resets daily. Uses typical price = (high + low + close) / 3.
    """
    def __init__(self):
        self._cum_pv: float = 0.0
        self._cum_vol: int = 0

    def update_candle(self, high: int, low: int, close: int, volume: int) -> float | None:
        if volume == 0:
            return None
        typical_price = (high + low + close) / 3.0
        self._cum_pv += typical_price * volume
        self._cum_vol += volume
        return self._cum_pv / self._cum_vol

    def reset(self):
        """Call at start of each trading day."""
        self._cum_pv = 0.0
        self._cum_vol = 0

class OBVIndicator:
    """On-Balance Volume: cumulative volume weighted by price direction."""
    def __init__(self):
        self._obv: int = 0
        self._prev_close: float | None = None

    def update(self, close: float, volume: int) -> int:
        if self._prev_close is not None:
            if close > self._prev_close:
                self._obv += volume
            elif close < self._prev_close:
                self._obv -= volume
        self._prev_close = close
        return self._obv
```

### Pattern 3: ConditionEngine -- AND/OR Composite Rules
**What:** Tree-based rule evaluation where each node is either a leaf (single comparison) or composite (AND/OR of children).
**When to use:** Every time indicators update on a completed candle.

```python
@dataclass
class Condition:
    """Single condition: indicator_name operator threshold."""
    indicator: str      # e.g., "rsi", "ema_short", "volume_ratio"
    operator: str       # "gt", "lt", "gte", "lte", "cross_above", "cross_below"
    value: float        # Threshold value

@dataclass
class CompositeRule:
    """AND/OR combination of conditions."""
    logic: str          # "AND" or "OR"
    conditions: list    # List of Condition or CompositeRule (nested)

class ConditionEngine:
    """Evaluates composite rules against current indicator values."""

    def evaluate(self, rule: CompositeRule, context: dict) -> bool:
        """Evaluate rule tree against indicator context dict.

        context = {"rsi": 28.5, "ema_short": 50200, "ema_long": 50100,
                    "price": 50300, "volume_ratio": 2.5, ...}
        """
        results = []
        for cond in rule.conditions:
            if isinstance(cond, CompositeRule):
                results.append(self.evaluate(cond, context))
            else:
                results.append(self._eval_condition(cond, context))

        if rule.logic == "AND":
            return all(results)
        return any(results)  # OR
```

### Pattern 4: Strategy Signal Flow with Priority & Cooldown
**What:** StrategyManager evaluates all active strategies for each stock, resolves signal conflicts by priority, applies cooldown.
**When to use:** After indicator update on each completed candle.

```python
@dataclass
class Signal:
    """Trading signal emitted by strategy evaluation."""
    code: str
    side: str           # "BUY" or "SELL"
    strategy_name: str
    priority: int
    price: int          # Current price at signal time
    timestamp: datetime
    reason: str         # Human-readable trigger description

class StrategyManager:
    """Loads strategies from config, evaluates on candle update, emits signals."""

    def on_candle_complete(self, code: str, candle: Candle, indicators: dict):
        """Called when CandleAggregator finalizes a candle.

        1. Build context dict from indicators
        2. Evaluate all enabled strategies for this code
        3. Collect signals, resolve conflicts by priority
        4. Apply cooldown filter
        5. Route surviving signals to execution
        """
        signals = []
        for strategy in self._get_strategies_for_code(code):
            if not strategy.enabled:
                continue
            signal = self._evaluate_strategy(strategy, code, candle, indicators)
            if signal:
                signals.append(signal)

        # Resolve: highest priority wins per direction
        signal = self._resolve_conflicts(signals)
        if signal and self._check_cooldown(code, signal):
            self._execute_signal(signal)
```

### Pattern 5: Paper Trading Mode
**What:** When config mode="paper", intercept signal execution: log to CSV instead of calling OrderManager.
**When to use:** Strategy validation before live deployment.

```python
import csv
from pathlib import Path

class PaperTrader:
    """Virtual order execution for strategy validation."""

    def __init__(self, csv_path: str = "trades.csv", initial_capital: int = 10_000_000):
        self._csv_path = Path(csv_path)
        self._capital = initial_capital
        self._positions: dict[str, dict] = {}
        self._init_csv()

    def execute_signal(self, signal: Signal):
        """Record virtual trade at current price."""
        # ... virtual execution logic ...
        self._write_trade(trade_record)

    def _init_csv(self):
        if not self._csv_path.exists():
            with open(self._csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "code", "side", "strategy", "price",
                    "qty", "amount", "pnl", "pnl_pct", "balance", "reason"
                ])
```

### Anti-Patterns to Avoid
- **Full recomputation per tick:** Recalculating SMA(200) over full window on every tick wastes CPU. Use incremental update.
- **Indicator calculation on in-progress candles:** Causes whipsaw signals from incomplete data. Only calculate on finalized candles.
- **Shared mutable state between strategies:** Each strategy instance must have its own indicator instances to avoid cross-contamination when strategies use different parameters.
- **Blocking indicator calculation in Qt event loop:** Keep calculations fast (O(1) per indicator). If ever slow, offload to QThread -- but with pure Python incrementals on 7 indicators this is unnecessary.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sliding window | Manual list slicing | `collections.deque(maxlen=N)` | O(1) append/evict, no memory leak |
| Timestamp parsing | Manual string splitting | `datetime.strptime` / Kiwoom HHMMSS direct | Edge cases with midnight rollover |
| CSV writing | Manual string concatenation | `csv.writer` | Handles quoting, encoding, newlines |
| Config JSON schema | Custom validation | Simple dict.get with defaults | Already established pattern in Settings |

**Key insight:** This phase is pure algorithmic Python -- no new external dependencies needed. The complexity is in the correct incremental math and the signal routing logic, not in infrastructure.

## Common Pitfalls

### Pitfall 1: EMA Seed Value
**What goes wrong:** EMA diverges from expected values if seeded incorrectly.
**Why it happens:** Common mistake is to seed EMA with 0 instead of the first actual value, or to use SMA of first N values as seed.
**How to avoid:** Seed EMA with the first close price. Return None until `period` values have been processed.
**Warning signs:** EMA values significantly different from SMA for same period in early candles.

### Pitfall 2: RSI Division by Zero
**What goes wrong:** RS calculation divides by avg_loss which can be 0 if all candles are gains.
**Why it happens:** In strong uptrends, all changes can be positive for the initial period.
**How to avoid:** Check `avg_loss == 0` -> return 100.0 (maximum bullish). Check `avg_gain == 0` -> return 0.0.
**Warning signs:** Crashes on first RSI calculation after warmup in trending markets.

### Pitfall 3: Kiwoom Price Sign Convention
**What goes wrong:** Negative prices passed to indicators corrupt calculations.
**Why it happens:** Kiwoom API returns signed prices (negative = price drop from prev close). Existing code uses `abs()` but new code might forget.
**How to avoid:** CandleAggregator must `abs()` all prices from FID data at the entry point, before any downstream processing. This is already done in RiskManager.on_price_update.
**Warning signs:** Negative candle prices, nonsensical indicator values.

### Pitfall 4: VWAP Not Resetting Daily
**What goes wrong:** VWAP cumulative values carry over from previous day, producing wrong intraday VWAP.
**Why it happens:** Forgetting to call `reset()` at market open.
**How to avoid:** Wire VWAP reset to MarketHoursManager state change to TRADING.
**Warning signs:** VWAP diverging significantly from current price at market open.

### Pitfall 5: Candle Minute Boundary Off-By-One
**What goes wrong:** Candle closes at wrong time, or ticks assigned to wrong candle.
**Why it happens:** Using `//` integer division on minutes without accounting for interval correctly. E.g., 09:04:59 and 09:05:00 should be in different 5-minute candles.
**How to avoid:** Use `minutes_since_open // interval * interval` for slot calculation. Test with boundary timestamps.
**Warning signs:** Candle counts don't match expected count for trading session duration.

### Pitfall 6: Signal Cooldown State Not Reset Daily
**What goes wrong:** Cooldown from previous day prevents first signal of new day.
**Why it happens:** Cooldown timestamp stored as absolute time, not cleared overnight.
**How to avoid:** Reset cooldown state in daily reset (alongside RiskManager.reset_daily, PositionTracker.reset_daily).
**Warning signs:** First candle of day should be eligible for signals after warmup.

### Pitfall 7: Paper Trading Position Tracking Disconnected from Live Tracker
**What goes wrong:** Paper mode signals conflict with PositionTracker state.
**Why it happens:** PaperTrader tracks its own virtual positions but RiskManager queries PositionTracker for real positions.
**How to avoid:** In paper mode, PaperTrader should update PositionTracker with virtual fills so that RiskManager validation (duplicate signal check, position limit) works correctly. OR make the signal path call validate_order before paper execution.
**Warning signs:** Paper mode allows unlimited positions or duplicate buys.

## Code Examples

### Verified: Wilder's RSI Smoothing (incremental)
```python
# Source: StockCharts RSI documentation + Wilder's original method
# After initial period average:
# avg_gain = (prev_avg_gain * (period - 1) + current_gain) / period
# avg_loss = (prev_avg_loss * (period - 1) + current_loss) / period
# RS = avg_gain / avg_loss
# RSI = 100 - 100 / (1 + RS)
```

### Verified: EMA Recursive Formula
```python
# Source: Wikipedia Exponential smoothing
# alpha = 2 / (period + 1)
# EMA_t = alpha * price_t + (1 - alpha) * EMA_{t-1}
# Equivalent stable form: EMA_t = EMA_{t-1} + alpha * (price_t - EMA_{t-1})
```

### Verified: VWAP Intraday Formula
```python
# Source: Databento, QuantConnect documentation
# typical_price = (high + low + close) / 3
# VWAP = sum(typical_price * volume) / sum(volume)  -- cumulative from market open
# Reset all sums at start of each trading day
```

### Verified: Bollinger Bands with Population StdDev
```python
# Source: StockCharts Bollinger Bands documentation
# Middle Band = SMA(period)
# Upper Band = SMA + (num_std * StdDev)
# Lower Band = SMA - (num_std * StdDev)
# Note: Bollinger uses POPULATION stddev (divide by N, not N-1)
```

### Integration Wiring in main.py
```python
# Phase 3 additions to main.py:
# 1. Load strategy config from settings
# 2. Create CandleAggregator(interval_minutes=config.candle_interval)
# 3. Create IndicatorEngine (holds indicator instances per code)
# 4. Create ConditionEngine
# 5. Create StrategyManager(condition_engine, risk_manager, order_manager)
# 6. Create PaperTrader if mode=="paper"
# 7. Wire: real_data_manager.register_subscriber("주식체결", candle_aggregator.on_tick)
# 8. Wire: candle_aggregator.candle_complete -> strategy_manager.on_candle_complete
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full window recompute per tick | Incremental O(1) per candle | Always best practice | Critical for real-time: 7 indicators * N stocks in < 1ms |
| TA-Lib C dependency | Pure Python for small indicator sets | When TA-Lib install became problematic on restricted envs | No C compiler needed, easier Windows deployment |
| Separate entry/exit strategy definition | Unified strategy with entry+exit conditions | Modern quant frameworks (QuantConnect, etc.) | Simpler strategy management, atomic enable/disable |

**Deprecated/outdated:**
- Using `pandas` for real-time streaming single-value updates -- overhead of DataFrame creation per tick is wasteful

## Open Questions

1. **분봉 주기 기본값 선택 (Claude's Discretion)**
   - What we know: User wants choice of 1/3/5분, stored in config
   - Recommendation: **Default to 1분봉**. Day trading on KOSPI/KOSDAQ typically uses 1-minute candles for fastest signal response. 3분/5분 can be configured by user. RSI(14) on 1분봉 means 14분 warmup which is acceptable (signal starts at 09:19).

2. **쿨다운 시간 기본값 (Claude's Discretion)**
   - What we know: Prevents duplicate signals for same stock+direction
   - Recommendation: **Default 5분 (300초)**. On 1분봉, this means at least 5 candles must pass before same-direction signal. Prevents rapid-fire entries while allowing reasonable re-entry. Config-adjustable per strategy.

3. **CSV 컬럼 구조 (Claude's Discretion)**
   - Recommendation: `timestamp, code, side, strategy, price, qty, amount, pnl, pnl_pct, balance, reason`
   - `reason` contains human-readable trigger description (e.g., "RSI(14)=28.3 < 30")

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None (uses defaults, pyproject.toml if needed) |
| Quick run command | `.venv/bin/python -m pytest tests/ -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRAD-01a | SMA incremental correctness | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_sma -x` | No -- Wave 0 |
| TRAD-01b | EMA incremental correctness | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_ema -x` | No -- Wave 0 |
| TRAD-01c | RSI Wilder smoothing correctness | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_rsi -x` | No -- Wave 0 |
| TRAD-01d | MACD (fast EMA - slow EMA + signal) | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_macd -x` | No -- Wave 0 |
| TRAD-01e | Bollinger Bands (SMA +/- K*std) | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_bollinger -x` | No -- Wave 0 |
| TRAD-01f | VWAP intraday cumulative + daily reset | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_vwap -x` | No -- Wave 0 |
| TRAD-01g | OBV cumulative volume by direction | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_obv -x` | No -- Wave 0 |
| TRAD-01h | Warmup period returns None | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_warmup -x` | No -- Wave 0 |
| TRAD-01i | CandleAggregator tick -> candle | unit | `.venv/bin/python -m pytest tests/test_candle_aggregator.py -x` | No -- Wave 0 |
| TRAD-02a | ConditionEngine AND/OR evaluation | unit | `.venv/bin/python -m pytest tests/test_condition_engine.py -x` | No -- Wave 0 |
| TRAD-02b | Strategy preset loading from config | unit | `.venv/bin/python -m pytest tests/test_strategy_manager.py::test_load_presets -x` | No -- Wave 0 |
| TRAD-02c | Signal priority conflict resolution | unit | `.venv/bin/python -m pytest tests/test_strategy_manager.py::test_priority -x` | No -- Wave 0 |
| TRAD-02d | Cooldown filtering | unit | `.venv/bin/python -m pytest tests/test_strategy_manager.py::test_cooldown -x` | No -- Wave 0 |
| TRAD-02e | Paper trading CSV logging | unit | `.venv/bin/python -m pytest tests/test_paper_trader.py -x` | No -- Wave 0 |
| TRAD-02f | End-to-end: candle -> indicator -> condition -> signal | integration | `.venv/bin/python -m pytest tests/test_strategy_integration.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/ -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_indicators.py` -- covers TRAD-01a through TRAD-01h
- [ ] `tests/test_candle_aggregator.py` -- covers TRAD-01i
- [ ] `tests/test_condition_engine.py` -- covers TRAD-02a
- [ ] `tests/test_strategy_manager.py` -- covers TRAD-02b, TRAD-02c, TRAD-02d
- [ ] `tests/test_paper_trader.py` -- covers TRAD-02e
- [ ] `tests/test_strategy_integration.py` -- covers TRAD-02f

## Sources

### Primary (HIGH confidence)
- StockCharts RSI documentation (Wilder's method) -- RSI incremental formula
- Wikipedia Exponential smoothing -- EMA recursive formula
- Wikipedia Bollinger Bands -- Bollinger Bands formula with population stddev
- Databento VWAP documentation -- VWAP intraday formula and daily reset
- Wikipedia On-balance volume -- OBV algorithm

### Secondary (MEDIUM confidence)
- [TA-Lib Python](https://github.com/TA-Lib/ta-lib-python) -- Alternative library assessment (rejected for C dependency)
- [TradingView Welford Bollinger Bands](https://www.tradingview.com/script/H1t5bdeB-Welford-Bollinger-Bands-WBB/) -- Welford algorithm for streaming stddev
- [FMZ incremental mean/variance](https://www.fmz.com/digest-topic/10267) -- Incremental update algorithms for trading

### Tertiary (LOW confidence)
- None. All indicator formulas are well-established mathematical definitions with HIGH confidence.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all stdlib + existing packages
- Architecture: HIGH -- follows established project patterns (observer, PyQt5 signals, config-driven, TDD)
- Indicator math: HIGH -- well-established mathematical formulas, multiple independent sources agree
- Pitfalls: HIGH -- derived from actual codebase analysis (Kiwoom price signs, existing patterns)
- Condition engine: MEDIUM -- AND/OR tree is standard but exact config schema is Claude's discretion

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable domain -- mathematical formulas don't change)
