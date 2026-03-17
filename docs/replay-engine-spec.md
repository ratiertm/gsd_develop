# Replay Engine 설계 문서

## 개요

ReplayEngine은 수집된 실시간 틱 데이터(SQLite DB)를 **라이브 트레이딩과 동일한 코드 경로**로 재생하여 전략을 시뮬레이션하는 엔진이다.

기존 BacktestEngine이 **이미 만들어진 봉 데이터**를 소비하는 반면, ReplayEngine은 **raw tick부터 시작**하여 봉 생성 → 전략 평가 → 매매 실행까지 전체 파이프라인을 검증한다.

## 데이터 파이프라인

```
SQLite DB (체결 테이블)
  │  raw ticks: code, timestamp, fid_10(현재가), fid_15(거래량), fid_20(체결시간) ...
  ▼
CandleAggregator.on_tick(code, fid_dict)
  │  틱 → N분봉 변환 (라이브와 동일한 코드)
  ▼
StrategyManager.on_candle_complete(code, candle)
  │  인디케이터 계산 → ConditionEngine으로 진입/청산 규칙 평가 → Signal 생성
  ▼
ReplayEngine 매매 실행
  │  포지션 관리, 비용 계산, 리스크 체크
  ▼
BacktestResult (거래 내역, 에쿼티 커브, 성과 지표)
```

## 핵심 컴포넌트

### ReplayEngine (`kiwoom_trader/backtest/replay_engine.py`)

엔진 본체. 틱 로딩, 파이프라인 조립, 매매 시뮬레이션을 담당한다.

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `strategy_configs` | `dict` | (필수) | 전략 설정 (strategies, watchlist_strategies 등) |
| `risk_config` | `RiskConfig` | 기본값 사용 | 손절/익절/트레일링/일일손실한도 |
| `cost_config` | `CostConfig` | 기본값 사용 | 수수료/세금/슬리피지 |
| `initial_capital` | `int` | 10,000,000 | 초기 자본금 (KRW) |
| `candle_interval` | `int` | 1 | 봉 간격 (분) |

**`run()` 메서드:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `db_path` | `str \| Path` | SQLite DB 경로 |
| `codes` | `list[str] \| None` | 종목 필터 (None = 전체) |
| `start_time` | `str \| None` | 시작 시각 `"HH:MM:SS"` |
| `end_time` | `str \| None` | 종료 시각 `"HH:MM:SS"` |
| `speed` | `float` | 재생 속도 (0 = 최대) |
| `on_progress` | `Callable` | 진행률 콜백 |
| `on_candle` | `Callable` | 봉 완성 콜백 |
| `on_signal` | `Callable` | 시그널 발생 콜백 |

### CandleAggregator (`kiwoom_trader/core/candle_aggregator.py`)

틱 데이터를 N분봉으로 변환. `replay_date` 파라미터로 리플레이 날짜를 주입받아 타임스탬프를 보정한다. 봉이 완성되면 등록된 콜백을 호출한다.

### StrategyManager + ConditionEngine

봉 완성 시 인디케이터를 계산하고, `CompositeRule` 트리를 `ConditionEngine`으로 평가하여 `Signal`을 생성한다.

**지원 연산자:** `gt`, `lt`, `gte`, `lte`, `cross_above`, `cross_below`

**지원 인디케이터:** `ema`, `rsi`, `bollinger` 등 (config의 `indicators` 섹션으로 정의)

## DB 스키마 (체결 테이블)

| 컬럼 | 설명 |
|------|------|
| `id` | 자동 증가 PK |
| `code` | 종목 코드 (e.g., `"005930"`) |
| `timestamp` | ISO 형식 타임스탬프 |
| `fid_10` | 현재가 |
| `fid_15` | 거래량 |
| `fid_20` | 체결시간 (`"HHMMSS"`) |
| `fid_*` | 기타 키움 API FID 값들 |

`_iter_ticks()`가 `fid_*` 컬럼을 `{int_fid: str_value}` dict로 변환하여 `CandleAggregator.on_tick()`에 전달한다. 이는 라이브에서 `OnReceiveRealData`가 전달하는 형식과 동일하다.

## 비용 모델 (`CostConfig`)

한국 주식시장 비용 구조를 반영한다.

| 항목 | 기본값 | 적용 |
|------|--------|------|
| 매수 수수료 | 0.015% | 매수 시 |
| 매도 수수료 | 0.015% | 매도 시 |
| 거래세 | 0.18% | 매도 시에만 |
| 슬리피지 | 5bp (0.05%) | 매수 시 가격 상승, 매도 시 가격 하락 |

```
매수 총비용 = (체결가 + 슬리피지) × 수량 + 수수료
매도 순수익 = (체결가 - 슬리피지) × 수량 - 수수료 - 거래세
```

## 리스크 관리 (`RiskConfig`)

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `stop_loss_pct` | -2.0% | 손절 |
| `take_profit_pct` | 3.0% | 익절 |
| `trailing_stop_pct` | 1.5% | 트레일링 스탑 (고점 대비) |
| `max_symbol_weight_pct` | 20.0% | 종목당 최대 비중 |
| `max_positions` | 5 | 최대 동시 포지션 수 |
| `daily_loss_limit_pct` | 3.0% | 일일 손실 한도 |

리스크 체크는 매 봉 완성 시 `_check_risk_triggers()`에서 수행:
1. 손절가 도달 → 즉시 청산
2. 익절가 도달 → 즉시 청산
3. 트레일링 스탑 (고점 갱신 후 하락) → 청산

일일 손실 한도 초과 시 신규 매수를 차단한다.

## 전략 설정 구조

```json
{
  "mode": "paper",
  "strategies": [
    {
      "name": "MA_CROSSOVER",
      "enabled": true,
      "priority": 1,
      "indicators": {
        "ema_short": {"type": "ema", "period": 5},
        "ema_long": {"type": "ema", "period": 20},
        "rsi": {"type": "rsi", "period": 14}
      },
      "entry_rule": {
        "logic": "AND",
        "conditions": [
          {"indicator": "ema_short", "operator": "cross_above", "value": 0},
          {"indicator": "rsi", "operator": "lt", "value": 70}
        ]
      },
      "exit_rule": {
        "logic": "OR",
        "conditions": [
          {"indicator": "ema_short", "operator": "cross_below", "value": 0},
          {"indicator": "rsi", "operator": "gt", "value": 80}
        ]
      },
      "cooldown_sec": 300
    }
  ],
  "watchlist_strategies": {
    "005930": ["MA_CROSSOVER"],
    "000660": ["MA_CROSSOVER"]
  }
}
```

- `watchlist_strategies`가 비어있으면 CLI가 DB의 전 종목에 자동 배정
- `--config` 미지정 시 EMA(5/20) + RSI(14) 기본 전략 사용

## 리플레이 종료 처리

1. `aggregator.flush()` — 미완성 봉 강제 완성
2. 미청산 포지션 전량 **평균 매입가**로 강제 청산 (reason: `"Replay end - forced close"`)
3. `BacktestResult` 빌드 → `compute_all_metrics()`로 성과 지표 계산

## CLI 사용법

```bash
# 기본 실행 (기본 전략, 자본금 1천만원, 1분봉)
python scripts/replay.py data/realtime_20260317.db

# 종목/시간 필터
python scripts/replay.py data/realtime_20260317.db \
    --codes 005930,000660 --start 09:00:00 --end 15:00:00

# 자본금/봉 간격 변경
python scripts/replay.py data/realtime_20260317.db \
    --capital 50000000 --interval 3

# 커스텀 전략 설정
python scripts/replay.py data/realtime_20260317.db \
    --config strategies/bollinger_rsi.json

# 디버그 로깅
python scripts/replay.py data/realtime_20260317.db -v
```

## BacktestEngine과의 차이점

| 항목 | BacktestEngine | ReplayEngine |
|------|---------------|--------------|
| 입력 데이터 | 사전 구축된 봉 | raw tick (SQLite DB) |
| 봉 생성 | 외부에서 제공 | CandleAggregator 내부 생성 |
| 코드 경로 | 백테스트 전용 | 라이브와 동일 |
| 검증 범위 | 전략 로직만 | 틱→봉 변환 + 전략 로직 |
| 용도 | 히스토리컬 백테스트 | 수집 데이터 리플레이, 라이브 파이프라인 검증 |

## 출력 예시

```
  Replaying: data/realtime_20260317.db
  [##############################] 100.0% (125,430/125,430 ticks)

============================================================
  REPLAY RESULT
============================================================

  Data: 125,430 ticks → 2,340 candles
  Capital: 10,000,000 → 10,245,000 KRW
  Return: +2.45%
  Max Drawdown: 1.23%
  Sharpe Ratio: 1.85

  Trades: 8
  Win Rate: 62.5%
  Profit Factor: 2.15
  Avg P&L: 30,625 KRW
  Max Consec. Losses: 2
  Avg Holding Period: 0.02 days

  Time                 Code     Side      Price    Qty          P&L Reason
  -------------------------------------------------------------------------------------
  09:15:32             005930   BUY       68,500    29              MA crossover entry
  09:42:18             005930   SELL      69,200    29      +18,350 Take profit triggered
  ...
============================================================
```
