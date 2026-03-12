# Architecture Patterns

**Domain:** 키움증권 OpenAPI+ 주식 데이트레이딩 자동매매 시스템
**Researched:** 2026-03-13
**Confidence:** MEDIUM (training data based; Kiwoom OpenAPI+ COM architecture is stable and well-documented in Korean developer community, patterns are well-established)

## Recommended Architecture

### System Overview

키움 OpenAPI+ 자동매매 시스템은 **이벤트 기반 아키텍처**다. COM/OCX 컨트롤이 PyQt5 이벤트 루프 위에서 동작하므로, 전체 시스템은 PyQt5의 QApplication 이벤트 루프를 중심축으로 구성된다.

```
+------------------------------------------------------------------+
|                    QApplication Event Loop                        |
|                    (메인 스레드 - 절대 블로킹 금지)                    |
|                                                                    |
|  +----------------+    +------------------+    +----------------+  |
|  | Kiwoom OCX     |    | GUI Dashboard    |    | Timer/Scheduler|  |
|  | (COM Control)  |    | (PyQt5 Widgets)  |    | (QTimer)       |  |
|  +-------+--------+    +--------+---------+    +-------+--------+  |
|          |                      |                       |          |
+------------------------------------------------------------------+
           |                      |                       |
     [이벤트 시그널]          [UI 업데이트]          [주기적 작업]
           |                      |                       |
+------------------------------------------------------------------+
|                     Worker Threads (QThread)                       |
|                                                                    |
|  +------------------+  +------------------+  +------------------+  |
|  | Strategy Engine  |  | Risk Manager     |  | Data Processor   |  |
|  | (매매 판단)       |  | (리스크 관리)     |  | (지표 계산)       |  |
|  +------------------+  +------------------+  +------------------+  |
+------------------------------------------------------------------+
           |                      |                       |
+------------------------------------------------------------------+
|                        Data Layer                                  |
|  +------------------+  +------------------+  +------------------+  |
|  | SQLite/CSV       |  | Config (JSON/    |  | Log Files        |  |
|  | (거래 기록)       |  |  YAML)           |  | (매매 로그)       |  |
|  +------------------+  +------------------+  +------------------+  |
+------------------------------------------------------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Thread |
|-----------|---------------|-------------------|--------|
| **KiwoomAPI (OCX Wrapper)** | COM OCX 컨트롤 래핑. 로그인, TR 요청, 실시간 등록, 주문 전송 | Strategy Engine, Data Processor, GUI | 메인 스레드 (필수) |
| **Event Router** | OCX 이벤트 시그널을 적절한 핸들러로 라우팅 | KiwoomAPI, Strategy Engine, GUI | 메인 스레드 |
| **Strategy Engine** | 매매 조건 판단, 진입/청산 시그널 생성 | KiwoomAPI (주문), Risk Manager, Data Processor | 워커 스레드 (권장) |
| **Risk Manager** | 포지션 크기, 손절/익절, 일일 손실 한도, 종목별 비중 관리 | Strategy Engine, KiwoomAPI | 워커 스레드 또는 메인 |
| **Data Processor** | 실시간 데이터 가공, 기술적 지표 계산 (MA, RSI, MACD, BB) | KiwoomAPI (데이터 수신), Strategy Engine | 워커 스레드 (권장) |
| **Order Manager** | 주문 상태 추적, 미체결 관리, 주문 큐 관리, TR 요청 제한 준수 | KiwoomAPI, Risk Manager, GUI | 메인 스레드 (API 호출 필요) |
| **GUI Dashboard** | 실시간 차트, 보유종목, 주문현황, 수익률 표시 | 모든 컴포넌트 (표시 목적) | 메인 스레드 |
| **Scheduler** | 장 시작/종료 관리, 매매 시간대 제어 | Strategy Engine, KiwoomAPI | 메인 스레드 (QTimer) |
| **Config Manager** | 전략 파라미터, 종목 리스트, 시스템 설정 관리 | 모든 컴포넌트 | 어느 스레드든 (읽기 전용) |
| **Logger/Notifier** | 매매 기록, 시스템 로그, Discord 웹훅 알림 | 모든 컴포넌트 | 별도 스레드 (I/O) |
| **Backtest Engine** | 과거 데이터 기반 전략 시뮬레이션 | Data Processor, Strategy Engine | 별도 프로세스 또는 스레드 |

### Data Flow

#### 1. 실시간 시세 수신 흐름 (핵심)

```
키움 서버 → OCX 컨트롤 (OnReceiveRealData)
  → Event Router (메인 스레드)
    → Data Processor (워커 스레드로 emit)
      → 시세 데이터 파싱 + 지표 계산
        → Strategy Engine (매매 조건 평가)
          → [조건 충족 시] Risk Manager (포지션 검증)
            → [승인 시] Order Manager → KiwoomAPI.SendOrder()
              → 주문 접수 → OnReceiveChejanData (체결/잔고 이벤트)
```

#### 2. TR 데이터 조회 흐름

```
Strategy Engine 또는 Scheduler → 데이터 요청
  → Order Manager (TR 큐 관리, 3.6초 제한 준수)
    → KiwoomAPI.CommRqData() (메인 스레드에서 호출)
      → 키움 서버 응답 → OnReceiveTrData (콜백)
        → Event Router → 요청자에게 데이터 전달
```

#### 3. 주문 체결 흐름

```
KiwoomAPI.SendOrder() → 키움 서버
  → OnReceiveChejanData (체결 이벤트)
    → Order Manager (주문 상태 업데이트)
      → Risk Manager (포지션/잔고 업데이트)
        → GUI (보유종목, 수익률 갱신)
        → Logger (매매 기록 저장)
        → Notifier (Discord 알림)
```

#### 4. GUI 업데이트 흐름

```
워커 스레드 데이터 → pyqtSignal.emit()
  → 메인 스레드 슬롯 → GUI Widget 업데이트
  (절대 워커 스레드에서 직접 GUI 접근 금지)
```

## Threading Model (핵심 아키텍처 결정)

### 제약 조건

키움 OpenAPI+ COM 컨트롤은 **STA(Single-Threaded Apartment)** 모델이다. 모든 COM 호출(TR 요청, 주문, 실시간 등록)은 반드시 **OCX를 생성한 메인 스레드**에서 이루어져야 한다. 이것이 전체 스레딩 모델을 결정한다.

### 권장 스레딩 구조

```
메인 스레드 (QApplication)
├── Kiwoom OCX 컨트롤 (COM 호출 전용)
├── GUI 위젯 렌더링
├── QTimer 기반 스케줄러
├── Event Router (시그널/슬롯)
└── Order Manager (SendOrder는 메인에서 호출)

워커 스레드 1: DataProcessor
├── 실시간 데이터 가공
├── 기술적 지표 계산
└── 계산 완료 시 pyqtSignal로 결과 전달

워커 스레드 2: StrategyEngine
├── 매매 조건 평가
├── 시그널 생성
└── 주문 요청 시 메인 스레드로 QMetaObject.invokeMethod

워커 스레드 3: Logger/Notifier (선택)
├── 파일 I/O
├── Discord HTTP 요청
└── 비동기 알림 처리
```

### 스레드 간 통신 패턴

**pyqtSignal/Slot이 유일한 안전한 방법이다.**

```python
# 워커 스레드 → 메인 스레드 (GUI 업데이트, API 호출)
class DataProcessor(QThread):
    data_processed = pyqtSignal(dict)  # 가공된 데이터 전달
    order_request = pyqtSignal(dict)   # 주문 요청 전달

    def run(self):
        while self.running:
            data = self.data_queue.get()
            result = self.calculate_indicators(data)
            self.data_processed.emit(result)

# 메인 스레드에서 연결
self.data_processor.data_processed.connect(self.on_data_ready)
self.data_processor.order_request.connect(self.execute_order)  # 메인에서 실행
```

**메인 스레드 → 워커 스레드 (데이터 전달)**

```python
# Queue 기반 전달 (thread-safe)
import queue

class DataProcessor(QThread):
    def __init__(self):
        self.data_queue = queue.Queue()

    def add_data(self, data):
        self.data_queue.put(data)  # thread-safe
```

### 절대 하지 말아야 할 것

1. **워커 스레드에서 COM 메서드 직접 호출** -- 크래시 또는 예측 불가 동작
2. **워커 스레드에서 GUI 위젯 직접 접근** -- Qt 크래시
3. **메인 스레드에서 time.sleep() 호출** -- 이벤트 루프 블로킹, 실시간 데이터 수신 중단
4. **메인 스레드에서 무한 루프** -- GUI 프리징, OCX 이벤트 수신 불가

## Patterns to Follow

### Pattern 1: TR 요청 큐 (Rate Limiter)

키움 API는 TR 요청 시 3.6초 간격 제한이 있다. QTimer 기반 큐로 관리해야 한다.

**What:** TR 요청을 큐에 넣고 QTimer로 3.6초 간격 디큐
**When:** 모든 TR(조회) 요청 시

```python
class TRRequestQueue:
    def __init__(self, kiwoom_api):
        self.queue = []
        self.timer = QTimer()
        self.timer.setInterval(3600)  # 3.6초
        self.timer.timeout.connect(self._process_next)
        self.kiwoom = kiwoom_api

    def enqueue(self, tr_code, input_data, callback):
        self.queue.append((tr_code, input_data, callback))
        if not self.timer.isActive():
            self._process_next()
            self.timer.start()

    def _process_next(self):
        if not self.queue:
            self.timer.stop()
            return
        tr_code, input_data, callback = self.queue.pop(0)
        self.kiwoom.request_tr(tr_code, input_data, callback)
```

### Pattern 2: 이벤트 기반 응답 대기 (QEventLoop)

TR 요청은 비동기지만, 동기적 흐름이 필요할 때 QEventLoop를 사용한다.

**What:** 로컬 QEventLoop로 응답 대기 (메인 이벤트 루프는 블로킹하지 않음)
**When:** 로그인 대기, 초기 데이터 로딩 등 순차 흐름이 필요할 때

```python
class KiwoomAPI(QAxWidget):
    def login(self):
        self.dynamicCall("CommConnect()")
        self.login_loop = QEventLoop()
        self.login_loop.exec_()  # OnEventConnect에서 quit 호출

    def _on_event_connect(self, err_code):
        self.login_loop.quit()
        if err_code == 0:
            print("로그인 성공")
```

### Pattern 3: Observer Pattern for Real-time Data

**What:** 실시간 데이터 수신 시 여러 구독자에게 알림
**When:** 여러 컴포넌트가 같은 실시간 데이터를 필요로 할 때

```python
class RealDataDispatcher:
    def __init__(self):
        self._subscribers = {}  # {fid_type: [callback, ...]}

    def subscribe(self, data_type, callback):
        self._subscribers.setdefault(data_type, []).append(callback)

    def dispatch(self, code, data_type, data):
        for callback in self._subscribers.get(data_type, []):
            callback(code, data)
```

### Pattern 4: State Machine for Order Lifecycle

**What:** 주문 상태를 명시적 상태 머신으로 관리
**When:** 주문 접수 ~ 체결 ~ 정정/취소 전체 라이프사이클

```
주문생성 → 접수대기 → 접수완료 → 부분체결 → 전량체결
                  ↘ 거부         ↘ 정정요청 → 정정완료
                                  ↘ 취소요청 → 취소완료
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: 단일 God Class
**What:** KiwoomAPI 클래스 하나에 로그인, TR 처리, 실시간, 주문, 전략, GUI 로직을 모두 넣는 것
**Why bad:** 유지보수 불가. 키움 관련 예제 코드 대부분이 이 패턴이라 그대로 따라하기 쉬움.
**Instead:** 책임별로 분리. KiwoomAPI는 COM 래핑만, 전략/리스크/GUI는 별도 클래스.

### Anti-Pattern 2: Polling Loop in Main Thread
**What:** while True 루프로 시세 체크하거나 time.sleep()으로 대기
**Why bad:** PyQt5 이벤트 루프 블로킹 → 실시간 데이터 수신 불가, GUI 프리징
**Instead:** QTimer, pyqtSignal/Slot, QEventLoop 사용

### Anti-Pattern 3: 전역 변수로 상태 공유
**What:** 보유종목, 잔고, 주문 상태를 전역 dict로 관리
**Why bad:** 스레드 안전성 없음, 디버깅 어려움, 테스트 불가
**Instead:** 상태 관리 클래스 + thread-safe 접근 메서드

### Anti-Pattern 4: 콜백 지옥 (Callback Spaghetti)
**What:** OnReceiveTrData에서 모든 TR 응답을 거대한 if-elif 분기로 처리
**Why bad:** 새 TR 추가 시 기존 코드 수정 필요, 가독성 저하
**Instead:** TR 코드별 핸들러 레지스트리 패턴

```python
# 나쁜 예
def _on_receive_tr_data(self, screen, rq_name, tr_code, ...):
    if rq_name == "opt10001":
        ...
    elif rq_name == "opt10081":
        ...
    # 수십 개의 elif...

# 좋은 예
class TRHandlerRegistry:
    def __init__(self):
        self._handlers = {}

    def register(self, rq_name, handler):
        self._handlers[rq_name] = handler

    def handle(self, rq_name, *args):
        handler = self._handlers.get(rq_name)
        if handler:
            handler(*args)
```

## Module/Package Structure

```
kiwoom_day_trader/
├── main.py                    # 진입점, QApplication 생성
├── config/
│   ├── settings.py            # 시스템 설정
│   └── strategies/            # 전략별 파라미터 (JSON/YAML)
├── api/
│   ├── kiwoom_api.py          # OCX 래퍼 (COM 호출 전용)
│   ├── event_router.py        # OCX 이벤트 라우팅
│   ├── tr_request_queue.py    # TR 요청 큐 (3.6초 제한)
│   └── constants.py           # TR 코드, FID 번호 상수
├── core/
│   ├── strategy_engine.py     # 매매 전략 판단
│   ├── risk_manager.py        # 리스크 관리
│   ├── order_manager.py       # 주문 관리/상태 추적
│   ├── scheduler.py           # 장 시간 관리
│   └── indicators.py          # 기술적 지표 계산
├── data/
│   ├── market_data.py         # 실시간 시세 데이터 관리
│   ├── data_processor.py      # 데이터 가공 (QThread)
│   └── storage.py             # SQLite/CSV 저장
├── gui/
│   ├── main_window.py         # 메인 윈도우
│   ├── chart_widget.py        # 실시간 차트
│   ├── portfolio_widget.py    # 보유종목 표시
│   ├── order_widget.py        # 주문 현황
│   └── log_widget.py          # 로그 표시
├── backtest/
│   ├── backtest_engine.py     # 백테스트 실행
│   ├── data_loader.py         # 과거 데이터 로딩
│   └── performance.py         # 성과 분석
├── notification/
│   ├── notifier.py            # 알림 매니저
│   └── discord_webhook.py     # Discord 알림
└── utils/
    ├── logger.py              # 로깅 설정
    └── helpers.py             # 유틸리티 함수
```

## Scalability Considerations

| Concern | 종목 10개 이하 | 종목 50개 | 종목 100개 이상 |
|---------|--------------|----------|---------------|
| 실시간 데이터 처리 | 메인 스레드 직접 처리 가능 | 워커 스레드 분리 필수 | 데이터 배치 처리 + 우선순위 큐 |
| 지표 계산 | 즉시 계산 | 증분 계산 (전체 재계산 금지) | numpy 벡터 연산 필수 |
| TR 요청 | 순차 처리 | 큐 관리 + 우선순위 | 3.6초 제한으로 초기 로딩 수 분 소요 |
| GUI 렌더링 | 즉시 갱신 | 갱신 주기 제한 (0.5초) | 가시 영역만 갱신, 가상화 |
| 주문 관리 | dict로 충분 | 상태 머신 필수 | 상태 머신 + 이벤트 소싱 고려 |

## Suggested Build Order (Dependencies)

빌드 순서는 의존성 기반으로 다음을 따른다.

### Phase 1: Foundation (선행 필수)
1. **KiwoomAPI OCX Wrapper** -- 모든 것의 기반. COM 연결, 로그인, 기본 이벤트 핸들링
2. **Event Router** -- OCX 이벤트를 시스템으로 전달하는 허브
3. **Config Manager** -- 설정 로딩 (이후 모든 컴포넌트가 참조)
4. **Logger** -- 디버깅과 매매 기록의 기초

### Phase 2: Data Pipeline
5. **TR Request Queue** -- 3.6초 제한 준수 큐 (이후 모든 TR 호출이 사용)
6. **Market Data** -- 실시간 시세 수신 및 저장
7. **Data Processor** -- 지표 계산 (QThread)

### Phase 3: Trading Core
8. **Risk Manager** -- 전략 엔진보다 먼저 (주문 실행 전 검증 필요)
9. **Order Manager** -- 주문 상태 추적, 체결 처리
10. **Strategy Engine** -- 매매 조건 판단 및 시그널 생성
11. **Scheduler** -- 장 시간 관리

### Phase 4: Interface & Monitoring
12. **GUI Dashboard** -- 실시간 모니터링
13. **Notifier** -- Discord 알림

### Phase 5: Validation
14. **Backtest Engine** -- 전략 검증 (독립적이므로 앞당길 수도 있음)

**의존성 그래프:**
```
KiwoomAPI → Event Router → Market Data → Data Processor → Strategy Engine
                        → TR Queue    ↗                 ↗
                                       Risk Manager ───┘
                                       Order Manager ──→ (체결 처리)
Strategy Engine → Risk Manager → Order Manager → KiwoomAPI.SendOrder()
GUI Dashboard ← (모든 컴포넌트의 시그널 구독)
Backtest Engine ← Strategy Engine (같은 인터페이스) + Data Loader
```

## Key Architecture Decisions

### 1. pykiwoom 사용 vs 직접 OCX 래핑

**권장: 직접 OCX 래핑 (QAxWidget 상속)**

pykiwoom은 빠른 프로토타이핑에 좋지만, 자동매매 시스템에서는 직접 래핑이 낫다.
- pykiwoom 내부 QEventLoop 사용이 복잡한 시나리오에서 충돌 가능
- 이벤트 핸들링 커스터마이징이 제한적
- 에러 처리를 세밀하게 제어할 수 없음
- 다만 pykiwoom 소스를 참조하여 설계 패턴을 배우는 것은 유용

### 2. 백테스트 엔진과 라이브 트레이딩의 인터페이스 통일

**권장: Strategy Engine에 추상 데이터 소스 인터페이스 적용**

```python
class DataSource(ABC):
    @abstractmethod
    def get_current_price(self, code): ...
    @abstractmethod
    def get_indicator(self, code, indicator_name): ...

class LiveDataSource(DataSource):
    # 실시간 API 데이터
    ...

class BacktestDataSource(DataSource):
    # 과거 데이터 재생
    ...
```

이렇게 하면 전략 코드 수정 없이 라이브/백테스트 전환이 가능하다.

### 3. 데이터 저장: SQLite

**권장: SQLite**

- 설치 불필요 (Python 내장)
- 단일 사용자 데스크톱 앱에 적합
- 매매 기록, 일봉/분봉 캐시, 설정 저장에 충분
- 동시 쓰기가 많지 않음 (트레이딩 주문은 순차적)

## Sources

- 키움증권 OpenAPI+ 개발 가이드 (공식 문서) -- MEDIUM confidence (training data 기반, 공식 문서 직접 검증 불가)
- pykiwoom 프로젝트 구조 (github.com/sharebook-kr/pykiwoom) -- MEDIUM confidence
- PyQt5 스레딩 모델 (Qt 공식 문서) -- HIGH confidence (잘 알려진 패턴)
- 한국 개발자 커뮤니티 키움 자동매매 패턴 (wikidocs, tistory 등) -- MEDIUM confidence
- COM/STA threading model (Microsoft 공식) -- HIGH confidence

**Note:** WebSearch/WebFetch가 차단되어 현재 버전 정보 및 최신 변경사항 검증이 불가했다. 키움 OpenAPI+ COM 아키텍처 자체는 안정적이어서 큰 변동은 없을 것으로 판단하나, 최신 API 변경사항은 개발 시작 전 공식 문서에서 확인해야 한다.
