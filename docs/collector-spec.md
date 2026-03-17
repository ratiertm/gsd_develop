# 키움 데이터 수집기 설계 문서

## 개요

`scripts/collector.py`는 키움 OpenAPI+를 통해 **과거 분봉 조회(TR)**와 **실시간 틱 수집**을 하나의 프로세스로 통합 실행하는 데이터 수집기다.

수집 결과는 `data/` 폴더에 **SQLite + CSV** 이중 저장되며, ReplayEngine의 입력 데이터로 사용된다.

## 실행 흐름

```
.venv32\Scripts\python.exe scripts/collector.py
                │
                ▼
          QApplication + 로그인
                │
                ▼
     ┌─── Phase 1: MinuteCandleFetcher ───┐
     │  opt10080 TR → 종목별 과거 분봉     │
     │  페이징 조회 (3.6초 제한 준수)      │
     │  → minute_1m_{date}.db / .csv      │
     └──────────── on_done ───────────────┘
                │
                ▼
     ┌─── Phase 2: RealtimeCollector ─────┐
     │  SetRealReg → OnReceiveRealData    │
     │  체결/호가/거래원/시간외/종목정보/장시작 │
     │  → realtime_{date}.db             │
     │  → {타입}_{date}.csv (타입별)      │
     └────────────────────────────────────┘
                │
                ▼
          18시 자동 종료 (QTimer)
```

## 아키텍처

### 공유 인프라

```python
api = KiwoomAPI()                           # OCX 래퍼
event_registry = EventHandlerRegistry()      # TR 응답 라우팅
tr_queue = TRRequestQueue(api, interval_ms=4000)  # 3.6초 제한 준수
```

세 컴포넌트를 `MinuteCandleFetcher`와 `RealtimeCollector`가 공유한다. TR 큐의 4초 간격은 키움 API의 초당 요청 제한(3.6초)을 준수하기 위한 설정이다.

### Phase 1: MinuteCandleFetcher

opt10080(주식분봉차트조회) TR로 과거 분봉 데이터를 페이징 조회한다.

**동작:**

1. 종목 리스트를 순차 처리 (`_fetch_next_code`)
2. 종목당 페이지를 반복 조회 (`prev_next=2`로 다음 페이지 요청)
3. cutoff 날짜(기본 3일 전) 도달 시 해당 종목 중단
4. DB + CSV 저장 후 다음 종목으로 이동
5. 전 종목 완료 시 `on_done` 콜백 → Phase 2 시작

**페이징 처리:**

```
page 0: prev_next=0 (최초 요청)
page 1: prev_next=2 (연속 조회)
page 2: prev_next=2
  ...
cutoff 도달 또는 has_next=False → 다음 종목
```

**저장 스키마 (candles 테이블):**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER PK | 자동 증가 |
| `code` | TEXT | 종목코드 |
| `name` | TEXT | 종목명 |
| `datetime` | TEXT | `"YYYY-MM-DD HH:MM:SS"` |
| `open` | INTEGER | 시가 |
| `high` | INTEGER | 고가 |
| `low` | INTEGER | 저가 |
| `close` | INTEGER | 종가 |
| `volume` | INTEGER | 거래량 |

- `UNIQUE(code, datetime)` 제약으로 중복 방지
- `INSERT OR IGNORE`로 재실행 시 안전

### Phase 2: RealtimeCollector

`SetRealReg`로 실시간 데이터를 등록하고, `OnReceiveRealData` 이벤트를 수신하여 저장한다.

**수집 대상 (6가지 실시간 타입):**

| 타입 | real_type | FID 수 | 주요 데이터 |
|------|-----------|--------|------------|
| 체결 | 주식체결 | 44 | 현재가, 체결량, 체결시간, 등락율 |
| 호가 | 주식호가잔량 | 163 | 매수/매도 10단계 호가 + 잔량 |
| 거래원 | 주식당일거래원 | 88 | 매수/매도 상위 거래원별 수량 |
| 시간외 | 주식시간외체결 | - | 시간외 단일가 체결 |
| 종목정보 | 주식종목정보 | - | 상한가/하한가, 기준가 등 |
| 장시작 | 장시작시간 | - | 장 상태 (동시호가, 개장, 폐장) |

**실시간 등록:**

```python
codes = "005930;005380;000660"
fid_str = "10;11;12;13;..."  # 모든 타입의 FID 합집합
api.set_real_reg("5000", codes, fid_str, "0")
```

모든 FID를 하나의 `set_real_reg` 호출로 통합 등록한다. 수신된 `real_type`으로 어떤 타입인지 분류한다.

**저장 스키마 (타입별 테이블, 예: 체결):**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER PK | 자동 증가 |
| `timestamp` | TEXT | 수신 시각 (밀리초 포함) |
| `code` | TEXT | 종목코드 |
| `name` | TEXT | 종목명 |
| `real_type` | TEXT | `"주식체결"` 등 |
| `fid_10` | TEXT | 현재가 |
| `fid_15` | TEXT | 체결량 |
| `fid_20` | TEXT | 체결시간 |
| `fid_*` | TEXT | 해당 타입의 모든 FID |

**성능 최적화:**

- `PRAGMA journal_mode=WAL` — 쓰기 잠금 최소화
- `PRAGMA synchronous=NORMAL` — 쓰기 속도 향상
- 50틱마다 CSV flush + DB commit (배치 쓰기)
- 별도 QTimer로 5초마다 DB commit (안전장치)

## 자동 종료 및 모니터링

```python
# 10초마다 실행
def periodic():
    if now.hour >= 18:       # 18시 자동 종료
        realtime.cleanup()
        app.quit()
    if now.minute % 5 == 0:  # 5분마다 상태 출력
        realtime.print_status()
```

- 18시 자동 종료 → `cleanup()`으로 파일/DB 정상 닫기
- 5분 간격 상태 로그 (타입별 틱 수)
- 50틱 간격 현재가 로그

## CLI 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--interval` | 1 | 분봉 간격 (1, 3, 5, 10, 15, 30, 60) |
| `--days` | 3 | 분봉 조회 기간 (일) |
| `--codes` | 삼성전자,현대차,SK하이닉스 | 종목코드 (쉼표 구분) |
| `--types` | 전체 (6가지) | 실시간 수집 타입 (쉼표 구분) |
| `--skip-history` | false | 분봉 조회 건너뛰기 (실시간만 수집) |

```bash
# 기본 실행 (분봉 3일 + 실시간 전체)
.venv32\Scripts\python.exe scripts/collector.py

# 분봉 5일, 3분봉
.venv32\Scripts\python.exe scripts/collector.py --interval 3 --days 5

# 체결+호가만 수집, 분봉 건너뛰기
.venv32\Scripts\python.exe scripts/collector.py --skip-history --types 체결,호가

# 특정 종목만
.venv32\Scripts\python.exe scripts/collector.py --codes 005930,000660
```

## 출력 파일 구조

```
data/
  minute_1m_{date}.db       # Phase 1: 분봉 SQLite
  minute_1m_{date}.csv      # Phase 1: 분봉 CSV
  realtime_{date}.db        # Phase 2: 실시간 전체 SQLite (체결/호가/거래원/... 테이블)
  체결_{date}.csv           # Phase 2: 체결 CSV
  호가_{date}.csv           # Phase 2: 호가 CSV
  거래원_{date}.csv         # Phase 2: 거래원 CSV
  시간외_{date}.csv         # Phase 2: 시간외 CSV
  종목정보_{date}.csv       # Phase 2: 종목정보 CSV
  장시작_{date}.csv         # Phase 2: 장시작 CSV
  collector_{date}.log      # 로그 (10MB rotation)
```

## 대상 종목 (WATCH_LIST)

| 코드 | 종목명 |
|------|--------|
| 005930 | 삼성전자 |
| 005380 | 현대차 |
| 000660 | SK하이닉스 |

종목 변경은 `collector.py` 상단의 `WATCH_LIST` dict를 수정한다.

## ReplayEngine과의 연결

```
collector.py → realtime_{date}.db (체결 테이블)
                     │
                     ▼
            replay.py → ReplayEngine
                     │  CandleAggregator.on_tick(code, fid_dict)
                     ▼
              BacktestResult (성과 분석)
```

ReplayEngine은 `realtime_{date}.db`의 **체결 테이블**에서 `fid_*` 컬럼을 읽어 `{int_fid: str_value}` dict로 변환한 뒤, `CandleAggregator.on_tick()`에 전달한다. 이는 라이브에서 `OnReceiveRealData` → `get_comm_real_data()`로 받는 형식과 동일하다.

## realtime_collector.py와의 관계

`realtime_collector.py`는 실시간 수집만 하는 초기 버전이다. `collector.py`는 이를 발전시켜 분봉 조회를 Phase 1으로 추가하고, API 인프라(EventHandlerRegistry, TRRequestQueue)를 공유하는 통합 버전이다.

| | realtime_collector.py | collector.py |
|--|--|--|
| 분봉 조회 | 없음 | opt10080 페이징 조회 |
| API 구조 | KiwoomAPI 단독 | KiwoomAPI + EventHandlerRegistry + TRRequestQueue |
| TR 큐 | 없음 | TRRequestQueue (4초 간격) |
| 실시간 수집 | 동일 | 동일 |
