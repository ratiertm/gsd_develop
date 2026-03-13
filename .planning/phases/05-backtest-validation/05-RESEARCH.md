# Phase 5: Backtest & Validation - Research

**Researched:** 2026-03-14
**Domain:** Backtesting engine, historical data retrieval, performance analytics, result visualization
**Confidence:** HIGH

## Summary

Phase 5 builds a backtest engine that replays historical OHLCV data through the existing StrategyManager and RiskManager code. The architecture is straightforward: a DataSource ABC fetches historical candles via Kiwoom opt10081 (daily) / opt10080 (minute) TRs, and a BacktestEngine feeds them one-by-one to the same StrategyManager/ConditionEngine/indicator pipeline used in live trading. A simulated execution layer (similar to PaperTrader but with cost modeling) tracks positions, applies commission/tax/slippage, and records trades. PerformanceCalculator computes the required metrics from the trade history and equity curve. BacktestDialog renders results using pyqtgraph (already in the project).

The key complexity is in correctly reusing live-trading components in a synchronous replay loop (no Qt event loop needed for the engine itself), handling Kiwoom TR rate limits during data download (3.6s/request), and ensuring cost modeling produces realistic results. All libraries needed are already in the project (pyqtgraph, PyQt5, loguru). No new dependencies required.

**Primary recommendation:** Build a clean DataSource ABC with KiwoomDataSource implementation, a BacktestEngine that orchestrates replay through existing components, a PerformanceCalculator as a pure function module, and a BacktestDialog with pyqtgraph charts. Run backtest in QThread to avoid UI blocking.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 키움 API opt10081(일봉)/opt10080(분봉) TR 조회로 과거 데이터 다운로드. 기존 TRRequestQueue 재사용 (3.6초 제한 준수)
- DataSource ABC (추상 클래스) 정의: get_candles(code, start_date, end_date) -> list[Candle]. KiwoomDataSource 구현. 향후 CSVDataSource 등 확장 가능
- 봉별 리플레이: 과거 봉 데이터를 시간순으로 하나씩 인디케이터/전략에 피딩. CandleAggregator 없이 직접 Candle 객체를 StrategyManager에 전달
- 백테스트 구간: 사용자가 시작일 ~ 종료일 직접 지정
- 수수료 + 거래세 반영: 매수 수수료 %, 매도 수수료 %, 거래세 0.18%(매도시). 모두 config.json에서 설정 가능
- 고정 슬리페이지: 체결가 = close +/- 고정 bp. config.json에서 설정 가능
- 실전 RiskManager 룰 그대로 적용: 손절/익절/트레일링스톱/포지션 제한/일일 손실 한도 동일 로직
- 초기 자본금: 사용자 입력 (기본값 1천만원)
- 핵심 5개 지표: 총 수익률, MDD(최대낙폭), 승률, Profit Factor(손익비), Sharpe Ratio
- 추가 지표: 평균 손익, 최대 연속 손실, 총 거래 횟수, 평균 보유 기간 등 부가 통계
- 결과 표시: 백테스트 완료 후 QDialog로 성과 요약 테이블 + 차트 표시
- 진행 상황: QProgressBar로 다운로드/시뮬레이션 진행률 + 예상 잔여시간 표시
- pyqtgraph 사용 (Phase 4 CandlestickItem 재사용)
- 핵심 3개 차트: Equity curve, Drawdown chart, 가격차트+매매마커
- 추가 차트: 월별 수익 막대차트, 거래 분포 등
- 별도 BacktestDialog (QDialog)
- StrategyTab에 "백테스트 실행" 버튼 추가 -> 기간/종목/자본금 입력 팝업 -> 실행 -> BacktestDialog 표시

### Claude's Discretion
- BacktestEngine 클래스 설계 및 리플레이 루프 구현
- KiwoomDataSource opt10080/opt10081 파싱 세부사항
- PerformanceCalculator 내부 지표 계산 알고리즘
- BacktestDialog 레이아웃 (차트 배치, 테이블 컬럼)
- 슬리페이지 기본값 (합리적 수준)
- 추가 지표/차트의 정확한 항목 선택
- QThread 기반 백테스트 실행 (UI 블로킹 방지)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BACK-01 | 전략 시뮬레이션 엔진 -- 과거 데이터로 전략 실행, DataSource 추상화로 실전과 코드 공유 | DataSource ABC + KiwoomDataSource + BacktestEngine replay loop + StrategyManager reuse pattern |
| BACK-02 | 성과 분석 -- 수익률, MDD, 승률, 손익비, 샤프비율 등 통계 | PerformanceCalculator pure functions with verified formulas |
| BACK-03 | 결과 시각화 -- 백테스트 결과 차트/그래프 (수익곡선, 드로다운 등) | BacktestDialog with pyqtgraph PlotWidget, CandlestickItem reuse |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt5 | 5.15.x | BacktestDialog, QThread, QProgressBar | Already in project, locked decision |
| pyqtgraph | 0.13.x | Equity curve, drawdown chart, price chart | Already in project, Phase 4 CandlestickItem reusable |
| abc (stdlib) | - | DataSource abstract base class | Standard Python ABC pattern, no deps |
| dataclasses (stdlib) | - | BacktestResult, CostConfig dataclasses | Project pattern from models.py |
| math (stdlib) | - | Sharpe ratio, MDD calculation | No numpy/pandas needed for these simple formulas |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| loguru | 0.7.x | Logging during backtest replay | Already in project |
| datetime (stdlib) | - | Date parsing for TR request/response | Already used throughout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure Python metrics | numpy/pandas | Overkill for 5 metrics on trade lists; no dependency needed |
| Custom charts | matplotlib | pyqtgraph already in project, integrates natively with PyQt5 |
| Custom backtest | backtrader/zipline | Locked decision to reuse existing StrategyManager; external lib mismatch |

**Installation:**
```bash
# No new packages needed -- all already installed
```

## Architecture Patterns

### Recommended Project Structure
```
kiwoom_trader/
├── backtest/
│   ├── __init__.py           # Module exports
│   ├── data_source.py        # DataSource ABC + KiwoomDataSource
│   ├── backtest_engine.py    # BacktestEngine replay orchestrator
│   ├── cost_model.py         # CostConfig + cost calculation functions
│   └── performance.py        # PerformanceCalculator pure functions
├── gui/
│   ├── backtest_dialog.py    # BacktestDialog QDialog with charts
│   └── ...existing...
├── core/
│   └── models.py             # Add BacktestResult, CostConfig dataclasses
└── config/
    └── settings.py           # Add backtest_config property
```

### Pattern 1: DataSource ABC with KiwoomDataSource
**What:** Abstract base class defining `get_candles(code, start_date, end_date) -> list[Candle]`. KiwoomDataSource implements via opt10081/opt10080 TR requests through existing TRRequestQueue.
**When to use:** All historical data retrieval. CSVDataSource can be added later for offline testing.
**Example:**
```python
# kiwoom_trader/backtest/data_source.py
from abc import ABC, abstractmethod
from datetime import date
from kiwoom_trader.core.models import Candle

class DataSource(ABC):
    @abstractmethod
    def get_candles(
        self, code: str, start_date: date, end_date: date,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[Candle]:
        """Fetch historical OHLCV candles, sorted by timestamp ascending."""
        ...

class KiwoomDataSource(DataSource):
    """Fetches via opt10081 (daily) or opt10080 (minute) TR requests."""

    def __init__(self, kiwoom_api, tr_queue: TRRequestQueue):
        self._api = kiwoom_api
        self._tr_queue = tr_queue

    def get_candles(self, code, start_date, end_date, on_progress=None):
        # 1. Enqueue TR requests with pagination (prev_next=0, then 2)
        # 2. Parse GetCommData response fields
        # 3. Filter to date range, sort ascending
        # 4. Convert to Candle dataclass list
        ...
```

### Pattern 2: BacktestEngine Replay Loop
**What:** Synchronous loop that feeds candles one-by-one to StrategyManager.on_candle_complete(), captures signals, and executes simulated trades with cost modeling. Bypasses CandleAggregator (candles are already formed).
**When to use:** Core simulation execution.
**Example:**
```python
class BacktestEngine:
    def __init__(self, strategy_manager, risk_checker, cost_config, initial_capital):
        self._sm = strategy_manager
        self._risk = risk_checker       # Simplified risk check (no market hours)
        self._cost = cost_config
        self._capital = initial_capital
        self._positions = {}            # {code: {qty, avg_price}}
        self._trades = []               # list[TradeRecord]
        self._equity_curve = []         # list[(timestamp, equity)]

    def run(self, candles: list[Candle], on_progress=None) -> BacktestResult:
        for i, candle in enumerate(candles):
            signals = self._sm.on_candle_complete(candle.code, candle)
            for sig in signals:
                self._execute_signal(sig, candle)
            # Check risk triggers (SL/TP/TS) against candle.close
            self._check_risk_triggers(candle)
            # Record equity snapshot
            self._record_equity(candle.timestamp)
            if on_progress:
                on_progress(i + 1, len(candles))
        # Force close remaining positions at last candle price
        self._close_all_positions(candles[-1])
        return self._build_result()
```

### Pattern 3: Simulated Risk Check (Backtest-Adapted)
**What:** Reuse RiskManager's position limit/daily loss logic but skip market hours checks (backtest replays outside real market hours). Implement SL/TP/trailing stop checks per-candle using the same percentage thresholds from RiskConfig.
**When to use:** During backtest replay loop.
**Key insight:** Cannot directly reuse RiskManager instance because it depends on QObject signals and MarketHoursManager. Instead, extract the risk check logic into the BacktestEngine or create a lightweight BacktestRiskChecker that applies the same RiskConfig percentages.

### Pattern 4: PerformanceCalculator as Pure Functions
**What:** Stateless functions that take trade list + equity curve and compute all metrics. Easy to test independently.
**When to use:** After backtest run completes.
**Example:**
```python
# All pure functions -- no class state needed
def calc_total_return(initial_capital: int, final_capital: int) -> float:
    return (final_capital - initial_capital) / initial_capital * 100

def calc_max_drawdown(equity_curve: list[tuple[datetime, float]]) -> float:
    peak = equity_curve[0][1]
    max_dd = 0.0
    for _, equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return max_dd

def calc_sharpe_ratio(
    daily_returns: list[float], risk_free_rate: float = 0.035, trading_days: int = 252
) -> float:
    if not daily_returns or len(daily_returns) < 2:
        return 0.0
    mean_ret = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std_ret = variance ** 0.5
    if std_ret == 0:
        return 0.0
    annual_ret = mean_ret * trading_days
    annual_std = std_ret * (trading_days ** 0.5)
    daily_rf = risk_free_rate / trading_days
    excess_daily = mean_ret - daily_rf
    return (excess_daily * trading_days) / annual_std

def calc_profit_factor(trades: list[TradeRecord]) -> float:
    gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return gross_profit / gross_loss

def calc_win_rate(trades: list[TradeRecord]) -> float:
    sell_trades = [t for t in trades if t.side == "SELL"]
    if not sell_trades:
        return 0.0
    winners = sum(1 for t in sell_trades if t.pnl > 0)
    return winners / len(sell_trades) * 100
```

### Pattern 5: QThread Backtest Execution
**What:** Run data download + simulation in a QThread worker, emit progress signals to update QProgressBar in BacktestDialog. Emit result signal on completion.
**When to use:** Always -- backtest can take minutes due to TR rate limits.
**Example:**
```python
class BacktestWorker(QThread):
    progress = pyqtSignal(int, int, str)  # current, total, phase_name
    finished = pyqtSignal(object)          # BacktestResult
    error = pyqtSignal(str)

    def run(self):
        try:
            # Phase 1: Download data
            candles = self._data_source.get_candles(
                self._code, self._start, self._end,
                on_progress=lambda cur, tot: self.progress.emit(cur, tot, "Downloading")
            )
            # Phase 2: Run simulation
            result = self._engine.run(
                candles,
                on_progress=lambda cur, tot: self.progress.emit(cur, tot, "Simulating")
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

### Anti-Patterns to Avoid
- **Reusing RiskManager directly:** It has QObject/signal dependencies and MarketHoursManager coupling. Extract the risk *logic* (SL/TP/TS percentages, position limits) instead.
- **Running backtest on main thread:** TR downloads at 3.6s/request for potentially hundreds of requests = minutes of blocking. Always use QThread.
- **Building indicators from scratch in backtest:** Reuse the same indicator classes (SMAIndicator, etc.) -- they are already pure Python with no Qt dependency.
- **Using CandleAggregator in backtest:** Candles from historical data are already complete -- no tick-to-candle aggregation needed. Feed Candle objects directly to StrategyManager.on_candle_complete().

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Candlestick charting | Custom QPainter code | Existing CandlestickItem | Already handles QPicture pre-rendering, sliding window |
| Indicator calculation | New indicator code | Existing indicators.py classes | Same SMA/EMA/RSI/MACD/Bollinger/VWAP/OBV, pure Python |
| Strategy evaluation | New condition engine | Existing ConditionEngine + StrategyManager | Core requirement is code reuse between live and backtest |
| TR rate limiting | Custom timer | Existing TRRequestQueue | Already handles 3.6s throttle with FIFO queue |
| Config management | Ad hoc config parsing | Existing Settings class | Add backtest section to existing config pattern |

**Key insight:** This phase's core value proposition is reusing live-trading components. Building custom versions defeats the purpose and creates maintenance divergence.

## Common Pitfalls

### Pitfall 1: Look-Ahead Bias
**What goes wrong:** Using future data in backtest decisions (e.g., using the current candle's high/low to determine entry before the candle closes).
**Why it happens:** Temptation to use full candle data for entry/exit when in reality only close is known at candle completion.
**How to avoid:** Feed candles strictly sequentially. Use close price for signal evaluation (matching on_candle_complete behavior). SL/TP checks use close price only -- do not check if intra-candle high/low would have triggered stops.
**Warning signs:** Backtest results significantly better than paper trading.

### Pitfall 2: Forgetting Cost Modeling Edge Cases
**What goes wrong:** Commission calculated on wrong base, or tax applied to both sides.
**Why it happens:** Korean market specifics: 거래세 0.18% is sell-side only, commission applies to both sides.
**How to avoid:** CostConfig dataclass with explicit buy_commission_pct, sell_commission_pct, tax_pct (sell-only), slippage_bp. Apply costs in execute_signal:
```python
def apply_costs(price, qty, side, cost_config):
    amount = price * qty
    if side == "BUY":
        commission = amount * cost_config.buy_commission_pct / 100
        slippage_cost = price * cost_config.slippage_bp / 10000 * qty
        total_cost = amount + commission + slippage_cost
    else:  # SELL
        commission = amount * cost_config.sell_commission_pct / 100
        tax = amount * cost_config.tax_pct / 100
        slippage_cost = price * cost_config.slippage_bp / 10000 * qty
        total_cost = amount - commission - tax - slippage_cost
    return total_cost
```
**Warning signs:** Backtest P&L much higher than expected, or negative P&L on small profitable trades.

### Pitfall 3: Kiwoom TR Data Parsing Gotchas
**What goes wrong:** Price values returned with leading +/- sign or spaces, dates in YYYYMMDD format without separators, volume values as strings.
**Why it happens:** Kiwoom GetCommData returns raw strings that need strip() and abs(int()) for price fields (already established in Phase 2 chejan parsing).
**How to avoid:** Apply the same parsing pattern from Phase 2: `abs(int(raw_value.strip() or '0'))` for all price/qty fields. Date fields: `datetime.strptime(date_str, "%Y%m%d")` or `"%Y%m%d%H%M%S"` for minute data.
**Warning signs:** Negative prices, parse errors, missing data.

### Pitfall 4: Indicator Warmup Period Data Loss
**What goes wrong:** First N candles produce no signals because indicators haven't warmed up, making short backtest periods useless.
**Why it happens:** RSI needs 15 candles, MACD needs 35+ candles, Bollinger needs 20 candles before producing values.
**How to avoid:** Fetch extra candles before the start date to allow warmup. Document in UI that backtest start date should allow warmup buffer. MACD(12,26,9) needs ~35 candles minimum -- if using 1-min candles, that is only ~35 minutes, trivial. For daily candles, need ~2 months extra.
**Warning signs:** Zero trades in backtest results.

### Pitfall 5: opt10080 Data Volume and TR Limits
**What goes wrong:** Downloading 6 months of 1-minute data requires many TR requests (each returns ~900 rows), taking 10+ minutes at 3.6s/request.
**Why it happens:** opt10080 returns data in blocks, newest first. Pagination via prev_next=2. 1 trading day has ~380 minutes, so 1 month = ~8000+ candles.
**How to avoid:** Use QProgressBar with estimated time remaining. Allow cancellation. Consider using daily candles (opt10081, 600 rows per request) as default for longer periods. Show expected download time before starting.
**Warning signs:** User thinks app is frozen during long downloads.

### Pitfall 6: StrategyManager Reuse Side Effects
**What goes wrong:** StrategyManager maintains internal state (_indicators, _prev_values, _cooldowns) that persists between calls and across backtests.
**Why it happens:** StrategyManager was designed for a single continuous session, not repeated backtests.
**How to avoid:** Create a fresh StrategyManager instance for each backtest run. Use the same StrategyConfig from Settings but instantiate new indicator objects. This is clean and matches the hot-swap pattern from Phase 4.
**Warning signs:** Second backtest run gives different results than first.

## Code Examples

### Kiwoom opt10081 (Daily) Data Request & Parsing
```python
# Source: Kiwoom OpenAPI+ DevGuide + project patterns from tr_request_queue.py
# opt10081 inputs
inputs = {
    "종목코드": code,          # e.g., "005930"
    "기준일자": end_date_str,   # "YYYYMMDD" -- fetch backward from this date
    "수정주가구분": "1",        # 1 = adjusted prices
}
# Enqueue via TRRequestQueue
tr_queue.enqueue(
    tr_code="opt10081",
    rq_name="주식일봉차트조회",
    screen_no="4001",
    inputs=inputs,
    prev_next=0,           # 0 = first request, 2 = continuation
)

# opt10081 output parsing (in TR response handler)
# Returns ~600 rows per request, newest first
for i in range(data_count):
    date_str = api.get_comm_data("opt10081", "주식일봉차트조회", i, "일자").strip()
    open_price = abs(int(api.get_comm_data("opt10081", "주식일봉차트조회", i, "시가").strip() or "0"))
    high = abs(int(api.get_comm_data("opt10081", "주식일봉차트조회", i, "고가").strip() or "0"))
    low = abs(int(api.get_comm_data("opt10081", "주식일봉차트조회", i, "저가").strip() or "0"))
    close = abs(int(api.get_comm_data("opt10081", "주식일봉차트조회", i, "현재가").strip() or "0"))
    volume = abs(int(api.get_comm_data("opt10081", "주식일봉차트조회", i, "거래량").strip() or "0"))

    candle = Candle(
        code=code,
        open=open_price, high=high, low=low, close=close,
        volume=volume,
        timestamp=datetime.strptime(date_str, "%Y%m%d"),
    )
```

### Kiwoom opt10080 (Minute) Data Request & Parsing
```python
# Source: Kiwoom OpenAPI+ DevGuide
# opt10080 inputs
inputs = {
    "종목코드": code,
    "틱범위": "1",             # 1분봉 (1/3/5/10/15/30/45/60)
    "수정주가구분": "1",
}
tr_queue.enqueue(
    tr_code="opt10080",
    rq_name="주식분봉차트조회",
    screen_no="4002",
    inputs=inputs,
    prev_next=0,
)

# opt10080 output parsing
for i in range(data_count):
    dt_str = api.get_comm_data("opt10080", "주식분봉차트조회", i, "체결시간").strip()
    # dt_str format: "YYYYMMDDHHMMSS"  (e.g., "20250315090100")
    open_p = abs(int(api.get_comm_data("opt10080", "주식분봉차트조회", i, "시가").strip() or "0"))
    high = abs(int(api.get_comm_data("opt10080", "주식분봉차트조회", i, "고가").strip() or "0"))
    low = abs(int(api.get_comm_data("opt10080", "주식분봉차트조회", i, "저가").strip() or "0"))
    close = abs(int(api.get_comm_data("opt10080", "주식분봉차트조회", i, "현재가").strip() or "0"))
    volume = abs(int(api.get_comm_data("opt10080", "주식분봉차트조회", i, "거래량").strip() or "0"))

    candle = Candle(
        code=code,
        open=open_p, high=high, low=low, close=close,
        volume=volume,
        timestamp=datetime.strptime(dt_str, "%Y%m%d%H%M%S"),
    )
```

### Cost Model Config and Application
```python
@dataclass
class CostConfig:
    buy_commission_pct: float = 0.015    # 매수 수수료 0.015%
    sell_commission_pct: float = 0.015   # 매도 수수료 0.015%
    tax_pct: float = 0.18               # 거래세 0.18% (매도시만)
    slippage_bp: float = 5.0            # 슬리페이지 5bp (0.05%)

def calc_buy_cost(price: int, qty: int, config: CostConfig) -> int:
    """Total cost to buy = amount + commission + slippage."""
    amount = price * qty
    slippage = int(price * config.slippage_bp / 10000) * qty
    effective_price = price + int(price * config.slippage_bp / 10000)
    effective_amount = effective_price * qty
    commission = int(effective_amount * config.buy_commission_pct / 100)
    return effective_amount + commission

def calc_sell_proceeds(price: int, qty: int, config: CostConfig) -> int:
    """Net proceeds from sell = amount - commission - tax - slippage."""
    effective_price = price - int(price * config.slippage_bp / 10000)
    effective_amount = effective_price * qty
    commission = int(effective_amount * config.sell_commission_pct / 100)
    tax = int(effective_amount * config.tax_pct / 100)
    return effective_amount - commission - tax
```

### BacktestResult Dataclass
```python
@dataclass
class BacktestResult:
    """Complete backtest output -- consumed by PerformanceCalculator and BacktestDialog."""
    trades: list[TradeRecord]
    equity_curve: list[tuple[datetime, float]]  # (timestamp, total_equity)
    initial_capital: int
    final_capital: float
    # Pre-computed metrics (filled by PerformanceCalculator)
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    avg_pnl: float = 0.0
    max_consecutive_losses: int = 0
    avg_holding_periods: float = 0.0
```

### BacktestDialog Layout Pattern
```python
class BacktestDialog(QDialog):
    def __init__(self, result: BacktestResult, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backtest Results")
        self.resize(1200, 800)

        layout = QVBoxLayout(self)

        # Top: Summary table (QTableWidget, 2 columns: metric name, value)
        self._summary_table = QTableWidget()
        layout.addWidget(self._summary_table, stretch=2)

        # Middle: Charts in QTabWidget
        charts = QTabWidget()
        charts.addTab(self._create_equity_chart(result), "Equity Curve")
        charts.addTab(self._create_drawdown_chart(result), "Drawdown")
        charts.addTab(self._create_price_chart(result), "Price + Trades")
        charts.addTab(self._create_monthly_chart(result), "Monthly Returns")
        layout.addWidget(charts, stretch=6)

        # Bottom: Close button
        btn = QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Backtest with separate strategy code | Reuse live strategy engine directly | Current best practice | Eliminates live/backtest divergence |
| No cost modeling | Commission + tax + slippage | Always essential | Prevents unrealistic profit expectations |
| Blocking backtest execution | QThread worker with progress | Standard Qt pattern | UI remains responsive |

**Korean market cost specifics (2025):**
- 거래세: 0.18% on sell side (KOSPI/KOSDAQ, reduced from 0.23% in 2023)
- 증권사 수수료: varies by broker, typically 0.015% for online trades at Kiwoom
- Slippage: 5bp (0.05%) is a reasonable default for liquid large-caps; illiquid stocks may need 10-20bp

## Open Questions

1. **opt10080 data row count per request**
   - What we know: opt10081 (daily) returns ~600 rows per request. opt10080 (minute) returns data in blocks.
   - What is unclear: Exact row count per opt10080 request (likely 900 based on community sources, needs validation on live system)
   - Recommendation: Implement pagination with prev_next=2 and detect end-of-data when returned count is 0 or date exceeds range.

2. **opt10080 historical range limit**
   - What we know: Community sources report opt10080 can fetch up to ~8 months of minute data
   - What is unclear: Whether this limit still applies in 2026
   - Recommendation: Handle gracefully -- if fewer candles returned than expected, inform user of available range.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pytest.ini` or default discovery |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-01 | DataSource ABC contract + KiwoomDataSource parse | unit | `pytest tests/test_data_source.py -x` | Wave 0 |
| BACK-01 | BacktestEngine replay loop produces trades | unit | `pytest tests/test_backtest_engine.py -x` | Wave 0 |
| BACK-01 | StrategyManager reuse in backtest context | unit | `pytest tests/test_backtest_engine.py::test_strategy_reuse -x` | Wave 0 |
| BACK-02 | Total return calculation | unit | `pytest tests/test_performance.py::test_total_return -x` | Wave 0 |
| BACK-02 | MDD calculation | unit | `pytest tests/test_performance.py::test_max_drawdown -x` | Wave 0 |
| BACK-02 | Win rate calculation | unit | `pytest tests/test_performance.py::test_win_rate -x` | Wave 0 |
| BACK-02 | Profit factor calculation | unit | `pytest tests/test_performance.py::test_profit_factor -x` | Wave 0 |
| BACK-02 | Sharpe ratio calculation | unit | `pytest tests/test_performance.py::test_sharpe_ratio -x` | Wave 0 |
| BACK-02 | Cost model correctness | unit | `pytest tests/test_cost_model.py -x` | Wave 0 |
| BACK-03 | BacktestDialog renders without crash | smoke | `pytest tests/test_backtest_dialog.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_performance.py tests/test_backtest_engine.py tests/test_data_source.py tests/test_cost_model.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_data_source.py` -- covers BACK-01 (DataSource parsing)
- [ ] `tests/test_backtest_engine.py` -- covers BACK-01 (replay loop, strategy reuse)
- [ ] `tests/test_performance.py` -- covers BACK-02 (all 5 core metrics + extra)
- [ ] `tests/test_cost_model.py` -- covers BACK-02 (commission/tax/slippage)
- [ ] `tests/test_backtest_dialog.py` -- covers BACK-03 (dialog smoke test)

## Sources

### Primary (HIGH confidence)
- Project codebase: `kiwoom_trader/core/models.py`, `strategy_manager.py`, `paper_trader.py`, `risk_manager.py`, `position_tracker.py`, `indicators.py`, `condition_engine.py` -- direct code inspection
- Project codebase: `kiwoom_trader/api/kiwoom_api.py`, `tr_request_queue.py` -- TR request/response pattern
- Project codebase: `kiwoom_trader/gui/widgets/candlestick_item.py` -- pyqtgraph chart pattern
- Project codebase: `kiwoom_trader/config/settings.py` -- config management pattern
- [Kiwoom OpenAPI+ DevGuide v1.5](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf) -- TR specifications

### Secondary (MEDIUM confidence)
- [Kiwoom API 분봉 데이터](https://i-whale.com/entry/%ED%82%A4%EC%9B%80-API%EB%A5%BC-%ED%86%B5%ED%95%B4-%EB%B6%84%EB%B4%89-%EB%8D%B0%EC%9D%B4%ED%84%B0-%EA%B0%80%EC%A0%B8%EC%98%A4%EA%B8%B0-kiwoomblockrequest) -- opt10080 field names, pagination
- [WikiDocs 일봉 데이터 연속 조회](https://wikidocs.net/5756) -- opt10081 600 rows per request
- [WikiDocs 멀티데이터 TR](https://wikidocs.net/84131) -- multi-data TR patterns
- [QuantStart Sharpe Ratio](https://www.quantstart.com/articles/Sharpe-Ratio-for-Algorithmic-Trading-Performance-Measurement/) -- annualized Sharpe formula
- [Codearmo Sharpe/Sortino](https://www.codearmo.com/blog/sharpe-sortino-and-calmar-ratios-python) -- ratio calculation formulas

### Tertiary (LOW confidence)
- opt10080 row count per request (~900) -- community consensus, not officially verified
- opt10080 8-month historical limit -- community report, may have changed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new deps
- Architecture: HIGH -- patterns derived from existing codebase inspection, clear reuse path
- Pitfalls: HIGH -- based on direct code analysis of StrategyManager state, TR parsing patterns, Korean market cost structure
- Kiwoom TR field names: MEDIUM -- cross-verified from multiple community sources and DevGuide

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable -- no fast-moving dependencies)
