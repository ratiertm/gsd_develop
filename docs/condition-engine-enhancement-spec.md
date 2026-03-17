# ConditionEngine Enhancement: value_ref 설계 문서

## 1. 배경 및 목적

### 현재 문제

ConditionEngine의 `Condition`은 인디케이터를 **고정 숫자(threshold)**와만 비교할 수 있다.

```python
# 현재: "RSI < 30" 만 가능
Condition(indicator="rsi", operator="lt", value=30)

# 불가능: "price < bollinger_lower", "macd cross_above macd_signal"
```

**결과:**
- MACD 시그널 크로스오버, 볼린저밴드 이탈 전략 등 구현 불가
- EMA 크로스오버만 하드코딩으로 우회 (strategy_manager.py:223-232)
- MACD tuple `(line, signal, histogram)` 중 line만 사용, 나머지 소실
- Bollinger tuple `(upper, middle, lower)` 중 upper만 사용, 나머지 소실

### 목표

`value_ref` 필드를 추가하여 **인디케이터 vs 인디케이터** 비교를 지원한다.

```json
{"indicator": "price", "operator": "lt", "value_ref": "bollinger_lower"}
{"indicator": "macd_line", "operator": "cross_above", "value_ref": "macd_signal"}
{"indicator": "ema_short", "operator": "cross_above", "value_ref": "ema_long"}
```

---

## 2. 현재 아키텍처 분석

### 데이터 흐름

```
config.json (strategy 정의)
  → StrategyManager._load_strategies()
    → _parse_rule() → CompositeRule 트리 생성
    → _init_indicators() → INDICATOR_CLASSES 매핑으로 인스턴스 생성

candle 수신
  → StrategyManager.on_candle_complete(code, candle)
    → _update_indicator() → 각 인디케이터 업데이트
    → context dict 구성 (indicator_name → value)
    → ConditionEngine.evaluate(rule, context) → bool
    → Signal 생성 → 매매 실행
```

### 현재 Condition 모델

```python
# models.py
@dataclass
class Condition:
    indicator: str   # "rsi", "ema_short"
    operator: str    # "gt", "lt", "gte", "lte", "cross_above", "cross_below"
    value: float     # 고정 숫자만 가능
```

### 튜플 반환 인디케이터의 데이터 소실

| 인디케이터 | 반환 | 사용 | 소실 |
|-----------|------|------|------|
| Bollinger | `(upper, middle, lower)` | `[0]` upper만 | middle, lower |
| MACD | `(line, signal, histogram)` | `[0]` line만 | signal, histogram |
| RSI, EMA, SMA | `float` | 전체 | 없음 |
| VWAP | `float` | 전체 | 없음 |
| OBV | `int` | 전체 | 없음 |

**소실 원인** — `strategy_manager.py` `_update_indicator()`:
```python
result = instance.update(candle.close)
if isinstance(result, tuple):
    return result[0]  # ← 첫 번째 요소만 반환, 나머지 버림
```

### 하드코딩된 EMA 크로스오버 (제거 대상)

```python
# strategy_manager.py:223-232 — 현재 코드
if "ema_short" in context and "ema_long" in context:
    ema_diff = context["ema_short"] - context["ema_long"]
    context["ema_short"] = ema_diff  # 원본 EMA 값 덮어씀
```

**문제:**
- `ema_short`/`ema_long` 이름에만 동작 (다른 이름 불가)
- 원본 EMA 값 소실
- 다른 인디케이터 쌍에 확장 불가

---

## 3. 변경 설계

### 3.1 Condition 모델 확장

```python
# models.py — 변경
@dataclass
class Condition:
    indicator: str                    # "rsi", "price", "macd_line"
    operator: str                     # "gt", "lt", "gte", "lte", "cross_above", "cross_below"
    value: float | None = None        # 고정 임계값 (기존)
    value_ref: str | None = None      # 인디케이터 참조 (신규)
```

**규칙:** `value`와 `value_ref` 중 정확히 하나만 설정. 둘 다 없거나 둘 다 있으면 에러.

### 3.2 튜플 인디케이터 서브 컴포넌트 확장

`_update_indicator()` 반환값을 변경하여 모든 서브 컴포넌트를 context에 등록한다.

**네이밍 규칙:** `{indicator_name}_{component}` (언더스코어 접미사)

| 인디케이터 | Context 키 | 값 |
|-----------|-----------|-----|
| `bollinger` | `bollinger_upper` | 상단 밴드 |
| | `bollinger_middle` | 중심선 (SMA) |
| | `bollinger_lower` | 하단 밴드 |
| `macd` | `macd_line` | MACD 라인 |
| | `macd_signal` | 시그널 라인 |
| | `macd_histogram` | 히스토그램 |
| `rsi` | `rsi` | RSI 값 (단일) |
| `ema_short` | `ema_short` | EMA 값 (단일) |
| `vwap` | `vwap` | VWAP 값 (단일) |
| `obv` | `obv` | OBV 값 (단일) |

**내장 context 키:**

| 키 | 값 |
|---|-----|
| `price` | `candle.close` |
| `volume` | `candle.volume` |

### 3.3 Context 구조 (변경 전 → 후)

**변경 전:**
```python
context = {
    "price": 68500,
    "volume": 15000,
    "rsi": 45.3,
    "rsi_prev": 43.2,
    "ema_short": -2.5,        # ← 차이값으로 덮어씀!
    "ema_short_prev": -1.8,
    "macd": 0.15,             # ← line만, signal/histogram 소실
    "bollinger": 69200,       # ← upper만, middle/lower 소실
}
```

**변경 후:**
```python
context = {
    "price": 68500,
    "volume": 15000,
    # 단일값 인디케이터
    "rsi": 45.3,
    "rsi_prev": 43.2,
    "ema_short": 68300.0,     # ← 원본 값 보존
    "ema_short_prev": 68250.0,
    "ema_long": 68100.0,
    "ema_long_prev": 68080.0,
    "vwap": 68400.0,
    "vwap_prev": 68350.0,
    "obv": 125000,
    "obv_prev": 124000,
    # MACD 서브 컴포넌트
    "macd_line": 0.15,
    "macd_line_prev": 0.12,
    "macd_signal": 0.10,
    "macd_signal_prev": 0.09,
    "macd_histogram": 0.05,
    "macd_histogram_prev": 0.03,
    # Bollinger 서브 컴포넌트
    "bollinger_upper": 69200,
    "bollinger_upper_prev": 69150,
    "bollinger_middle": 68500,
    "bollinger_middle_prev": 68450,
    "bollinger_lower": 67800,
    "bollinger_lower_prev": 67750,
}
```

### 3.4 ConditionEngine 평가 로직

```python
# condition_engine.py — _eval_condition() 변경
def _eval_condition(self, condition: Condition, context: dict) -> bool:
    ind = condition.indicator
    op = condition.operator

    # threshold 해석: value_ref가 있으면 context에서 조회
    if condition.value_ref:
        threshold = context.get(condition.value_ref)
        if threshold is None:
            return False  # 참조 인디케이터 미준비 (warmup)
    else:
        threshold = condition.value

    # cross 연산자
    if op in ("cross_above", "cross_below"):
        if ind not in context or f"{ind}_prev" not in context:
            return False
        current = context[ind]
        prev = context[f"{ind}_prev"]

        # value_ref 일 때: threshold도 이전 값 필요
        if condition.value_ref:
            threshold_prev = context.get(f"{condition.value_ref}_prev")
            if threshold_prev is None:
                return False
            if op == "cross_above":
                return prev <= threshold_prev and current > threshold
            else:
                return prev >= threshold_prev and current < threshold
        else:
            if op == "cross_above":
                return prev <= threshold and current > threshold
            else:
                return prev >= threshold and current < threshold

    # 비교 연산자
    if ind not in context:
        return False
    current = context[ind]

    if op == "gt":  return current > threshold
    if op == "lt":  return current < threshold
    if op == "gte": return current >= threshold
    if op == "lte": return current <= threshold
    return False
```

**cross + value_ref 핵심:**
- `ema_short cross_above ema_long` 평가 시:
  - 이전: `ema_short_prev <= ema_long_prev` (아래에 있었고)
  - 현재: `ema_short > ema_long` (위로 올라옴)
  - → 크로스오버 감지

---

## 4. 수정 파일 및 영향 범위

| 파일 | 변경 | 영향도 | 하위 호환 |
|------|------|--------|----------|
| `core/models.py` | Condition에 `value_ref` 필드 추가 | 낮음 | O (default None) |
| `core/condition_engine.py` | value_ref 해석 로직 추가 | 중간 | O |
| `core/strategy_manager.py` | 튜플 확장 + EMA 하드코딩 제거 | 높음 | O |
| `gui/strategy_tab.py` | 조건 편집 UI에 value_ref 모드 추가 | 중간 | O |
| `backtest/backtest_engine.py` | 변경 없음 (StrategyManager 경유) | 없음 | - |
| `backtest/replay_engine.py` | 변경 없음 (StrategyManager 경유) | 없음 | - |
| `config.json` | 예시 전략 추가 | 문서 | O |
| `tests/` | 테스트 추가 (~105 LOC) | - | - |

**핵심:** BacktestEngine과 ReplayEngine은 **수정 불필요** — 동일한 StrategyManager 경로를 사용하므로 자동으로 value_ref 지원.

---

## 5. 레퍼런스 전략 설정 (value_ref 적용 예시)

### 5.1 볼린저밴드 리버설

가격이 하단밴드 아래 + RSI 과매도 → 매수, 중심선 회복 → 매도.

```json
{
  "name": "BOLLINGER_REVERSAL",
  "enabled": true,
  "priority": 15,
  "cooldown_sec": 300,
  "indicators": {
    "bollinger": {"type": "bollinger", "period": 20, "num_std": 2.0},
    "rsi": {"type": "rsi", "period": 14}
  },
  "entry_rule": {
    "logic": "AND",
    "conditions": [
      {"indicator": "price", "operator": "lt", "value_ref": "bollinger_lower"},
      {"indicator": "rsi", "operator": "lt", "value": 30}
    ]
  },
  "exit_rule": {
    "logic": "OR",
    "conditions": [
      {"indicator": "price", "operator": "gt", "value_ref": "bollinger_middle"},
      {"indicator": "rsi", "operator": "gt", "value": 80}
    ]
  }
}
```

### 5.2 MACD 시그널 크로스오버

MACD 라인이 시그널 라인 상향 돌파 → 매수, 하향 돌파 → 매도.

```json
{
  "name": "MACD_SIGNAL_CROSS",
  "enabled": true,
  "priority": 20,
  "cooldown_sec": 300,
  "indicators": {
    "macd": {"type": "macd", "fast": 12, "slow": 26, "signal": 9}
  },
  "entry_rule": {
    "logic": "AND",
    "conditions": [
      {"indicator": "macd_line", "operator": "cross_above", "value_ref": "macd_signal"}
    ]
  },
  "exit_rule": {
    "logic": "AND",
    "conditions": [
      {"indicator": "macd_line", "operator": "cross_below", "value_ref": "macd_signal"}
    ]
  }
}
```

### 5.3 VWAP 브레이크아웃

가격이 VWAP 상향 돌파 + 거래량 평균 이상 → 매수.

```json
{
  "name": "VWAP_BREAKOUT",
  "enabled": true,
  "priority": 12,
  "cooldown_sec": 600,
  "indicators": {
    "vwap": {"type": "vwap"},
    "volume_sma": {"type": "sma", "period": 20}
  },
  "entry_rule": {
    "logic": "AND",
    "conditions": [
      {"indicator": "price", "operator": "cross_above", "value_ref": "vwap"},
      {"indicator": "volume", "operator": "gte", "value_ref": "volume_sma"}
    ]
  },
  "exit_rule": {
    "logic": "AND",
    "conditions": [
      {"indicator": "price", "operator": "cross_below", "value_ref": "vwap"}
    ]
  }
}
```

### 5.4 일반화된 MA 크로스오버 (하드코딩 대체)

기존 EMA 하드코딩을 value_ref로 대체. 어떤 MA 조합이든 사용 가능.

```json
{
  "name": "MA_CROSSOVER_V2",
  "enabled": true,
  "priority": 10,
  "cooldown_sec": 300,
  "indicators": {
    "ema_short": {"type": "ema", "period": 5},
    "ema_long": {"type": "ema", "period": 20},
    "rsi": {"type": "rsi", "period": 14}
  },
  "entry_rule": {
    "logic": "AND",
    "conditions": [
      {"indicator": "ema_short", "operator": "cross_above", "value_ref": "ema_long"},
      {"indicator": "rsi", "operator": "lt", "value": 70}
    ]
  },
  "exit_rule": {
    "logic": "OR",
    "conditions": [
      {"indicator": "ema_short", "operator": "cross_below", "value_ref": "ema_long"},
      {"indicator": "rsi", "operator": "gt", "value": 80}
    ]
  }
}
```

---

## 6. GUI 영향 (StrategyTab)

### 조건 편집 위젯 변경

현재: `[인디케이터 콤보] [연산자 콤보] [숫자 스핀박스]`

변경: `[인디케이터 콤보] [연산자 콤보] [모드 토글] [숫자 스핀박스 | 인디케이터 참조 콤보]`

**모드 토글:** "고정값" / "인디케이터 참조" 라디오 버튼
- 고정값 모드: 기존 QDoubleSpinBox 표시 → `value` 저장
- 참조 모드: QComboBox (현재 전략의 인디케이터 + 서브컴포넌트 목록) → `value_ref` 저장

**참조 콤보 항목 자동 구성:**
```
[인디케이터명]          → "rsi", "ema_short", "vwap"
[인디케이터_서브컴포넌트] → "bollinger_upper", "bollinger_middle", "bollinger_lower"
                        → "macd_line", "macd_signal", "macd_histogram"
[내장 키]              → "price", "volume"
```

### 직렬화/역직렬화

```python
# 저장 시
if mode == "고정값":
    cond_dict = {"indicator": ind, "operator": op, "value": spin.value()}
else:
    cond_dict = {"indicator": ind, "operator": op, "value_ref": combo.currentText()}

# 로드 시
if "value_ref" in cond_dict:
    mode_toggle.setChecked(True)  # 참조 모드
    ref_combo.setCurrentText(cond_dict["value_ref"])
else:
    mode_toggle.setChecked(False)  # 고정값 모드
    spin.setValue(cond_dict["value"])
```

---

## 7. 하위 호환성

| 항목 | 호환 | 설명 |
|------|------|------|
| 기존 config.json | O | `value`만 있는 조건은 그대로 동작 |
| 기존 전략 | O | value_ref 없으면 기존 로직 경유 |
| BacktestEngine | O | 수정 불필요 — StrategyManager 경유 |
| ReplayEngine | O | 수정 불필요 — StrategyManager 경유 |
| GUI 기존 전략 편집 | O | 고정값 모드가 기본 |
| MA_CROSSOVER 전략 | O | 하드코딩 제거 후 value_ref 버전으로 마이그레이션 |

---

## 8. 구현 순서 (권장)

| 단계 | 작업 | 파일 |
|------|------|------|
| 1 | Condition 모델에 `value_ref` 필드 추가 | `models.py` |
| 2 | `_update_indicator()` 튜플 확장 | `strategy_manager.py` |
| 3 | Context 구성에 서브컴포넌트 등록 | `strategy_manager.py` |
| 4 | EMA 하드코딩 제거 | `strategy_manager.py` |
| 5 | `_eval_condition()` value_ref 해석 | `condition_engine.py` |
| 6 | `_parse_rule()` value_ref 파싱 | `strategy_manager.py` |
| 7 | 테스트 추가 | `tests/` |
| 8 | GUI 조건 편집 위젯 확장 | `strategy_tab.py` |
| 9 | 레퍼런스 전략 JSON 추가 | `strategies/` |

---

## 9. 테스트 계획

### 신규 테스트 (~105 LOC)

**test_condition_engine.py:**
- `test_value_ref_gt` — 인디케이터 vs 인디케이터 비교
- `test_value_ref_missing_target` — 참조 인디케이터 없을 때 False
- `test_value_ref_cross_above` — 크로스오버 (양쪽 prev 필요)
- `test_value_ref_cross_below` — 크로스 다운

**test_strategy_manager.py:**
- `test_tuple_indicator_sub_components` — Bollinger/MACD 서브컴포넌트 context 등록
- `test_ema_crossover_without_hardcode` — value_ref로 EMA 크로스오버

**test_replay_engine.py:**
- `test_replay_with_value_ref_strategy` — value_ref 전략으로 리플레이

### 기존 테스트 영향: 없음 (하위 호환)
