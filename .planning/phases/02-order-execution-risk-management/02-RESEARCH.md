# Phase 2: Order Execution & Risk Management - Research

**Researched:** 2026-03-13
**Domain:** Kiwoom OpenAPI+ SendOrder/ChejanData, Order State Machine, Risk Management Engine
**Confidence:** MEDIUM-HIGH

## Summary

Phase 2 builds the order execution layer (SendOrder, OnReceiveChejanData, order state machine) and risk management engine (stop-loss, take-profit, trailing stop, position limits, market hours) on top of Phase 1's API foundation. The Kiwoom API's asynchronous order model -- where SendOrder returns only an acceptance code and actual fills arrive via OnReceiveChejanData events -- requires a robust state machine to avoid duplicate orders, missed fills, and position tracking errors.

The official Kiwoom OpenAPI+ dev guide v1.5 (PDF) provides complete specifications for SendOrder parameters, OnReceiveChejanData gubun values, GetChejanData FID numbers, and error codes. All ChejanData FIDs for both order/execution (gubun=0) and balance (gubun=1) have been extracted and verified from the official document.

**Primary recommendation:** Build OrderManager (state machine + SendOrder wrapper) and RiskManager (pre-trade validation + real-time triggers) as two separate classes that communicate via pyqtSignal. RiskManager subscribes to RealDataManager price events and gates all orders through pre-submission validation. Use Python Enum for order states and dataclass for order/position models.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 기본 손절: -2% (매수가 대비)
- 기본 익절: +3% (매수가 대비, 손익비 1:1.5)
- 트레일링 스탑: 최고가 대비 -1.5% 하락 시 동적 손절
- 모든 비율은 config.json에서 사용자 수정 가능 (기본값 제공)
- 실시간 체결가(RealDataManager) 이벤트로 트리거
- 분할 매수/매도 기본 3회, 균등 분할 (33% + 33% + 34%)
- 매도도 매수와 동일 방식 (3회 균등 분할)
- 추가 진입 조건: 시간 간격 기반 (1차 매수 후 일정 시간 경과 후 조건 재확인 시 2차 진입)
- 종목별 최대 투자 비중: 총 투자금의 20%
- 동시 보유 최대 종목 수: 5종목
- 일일 최대 손실 한도: 총 투자금의 -3%
- 일일 손실 한도 도달 시: 전 포지션 시장가 청산 + 당일 신규 매수 차단
- 매매 시작: 09:05 (장 시작 후 5분, 동시호가 종료 후 안정화 대기)
- 신규 매수 중단 + 보유 종목 청산 시작: 15:15 (장 종료 15분 전)
- 동시호가 시간대(08:30~09:00, 15:20~15:30): 모든 주문 완전 차단
- 데이트레이딩 특성상 당일 전량 청산 원칙 -- 오버나잇 포지션 없음

### Claude's Discretion
- SendOrder API 래핑 및 주문 상태 머신 구현 상세
- OnReceiveChejanData 이벤트 파싱 및 주문 상태 추적 방식
- 리스크 매니저와 주문 매니저 간 인터페이스 설계
- 분할 매수 시간 간격 기본값 (30초~60초 범위에서 결정)
- 일일 손실 계산 방식 (실현손익 vs 평가손익 포함 여부)
- 포지션 청산 시 주문 우선순위 및 순서

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRAD-03 | 자동 주문 실행 -- 시장가/지정가 매수/매도, 주문 상태 머신(접수->체결->완료) | SendOrder API spec, OnReceiveChejanData FIDs, order state machine pattern, error codes |
| TRAD-04 | 매매 시간대 관리 -- 장 시작/종료 시간, 동시호가 제외, 사용자 구간 설정 | MarketHoursManager pattern, FID 215 (장운영구분), QTimer-based scheduling |
| RISK-01 | 기본 손절/익절 -- % 기반 손절매, 목표가 매도 | RealDataManager price subscription, trigger evaluation pattern |
| RISK-02 | 트레일링 스탑 -- 최고가 대비 하락폭으로 동적 손절 | High-water mark tracking per position, dynamic stop-level adjustment |
| RISK-03 | 분할 매수/매도 -- 여러 번에 나눠 진입/청산 | SplitOrderExecutor pattern, time-interval scheduling via QTimer |
| RISK-04 | 포지션 제한 -- 종목별 비중 한도, 총 투자 한도, 일일 손실 한도 | Pre-trade validation gate, PositionTracker with real-time P&L |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt5 | 5.15.10 | Event loop, signals/slots, QTimer | Required for Kiwoom OCX COM STA model |
| loguru | latest | Structured logging with trade log sink | Already configured in Phase 1 |
| python-dotenv | latest | Environment variable management | Already in use for account credentials |

### Supporting (no new dependencies needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| enum (stdlib) | - | Order states, order types as Enum | All order state definitions |
| dataclasses (stdlib) | - | Order, Position, RiskConfig models | All data transfer objects |
| datetime (stdlib) | - | Market hours comparison, timestamp tracking | MarketHoursManager |
| collections.deque (stdlib) | - | Fixed-size price history for trailing stop | High-water mark tracking |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual state machine | `transitions` library | Adds dependency for simple 6-state machine; stdlib Enum is sufficient |
| dataclasses | Pydantic | Heavier validation framework; overkill for internal DTOs in this domain |

**Installation:**
```bash
# No new packages needed -- all stdlib + existing dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
kiwoom_trader/
├── api/
│   ├── kiwoom_api.py          # (extend) add send_order, get_chejan_data
│   └── event_handler.py       # (extend) add chejan handler routing
├── core/                       # NEW directory
│   ├── __init__.py
│   ├── order_manager.py        # OrderManager: state machine, SendOrder wrapper
│   ├── risk_manager.py         # RiskManager: pre-trade + real-time risk
│   ├── position_tracker.py     # PositionTracker: holdings, P&L
│   ├── market_hours.py         # MarketHoursManager: time window enforcement
│   └── models.py               # Order, Position, RiskConfig dataclasses
├── config/
│   ├── constants.py            # (extend) add CHEJAN FIDs, ORDER constants
│   └── settings.py             # (extend) add risk config loading
└── main.py                     # (extend) wire OrderManager, RiskManager
```

### Pattern 1: Order State Machine (Enum-based)
**What:** Explicit Enum states with legal transitions enforced by OrderManager
**When to use:** Every order from creation to terminal state

```python
from enum import Enum, auto

class OrderState(Enum):
    CREATED = auto()       # 주문 생성 (아직 SendOrder 호출 전)
    SUBMITTED = auto()     # SendOrder 호출됨, 접수 대기
    ACCEPTED = auto()      # 접수 확인 (gubun=0, 주문상태=접수)
    PARTIAL_FILL = auto()  # 부분 체결 (미체결수량 > 0)
    FILLED = auto()        # 전량 체결 (미체결수량 == 0)
    CANCELLED = auto()     # 취소 완료
    REJECTED = auto()      # 거부됨
    MODIFY_PENDING = auto()  # 정정 요청 중

# Legal transitions
VALID_TRANSITIONS = {
    OrderState.CREATED: {OrderState.SUBMITTED, OrderState.REJECTED},
    OrderState.SUBMITTED: {OrderState.ACCEPTED, OrderState.REJECTED},
    OrderState.ACCEPTED: {OrderState.PARTIAL_FILL, OrderState.FILLED,
                          OrderState.CANCELLED, OrderState.MODIFY_PENDING},
    OrderState.PARTIAL_FILL: {OrderState.FILLED, OrderState.CANCELLED,
                              OrderState.MODIFY_PENDING, OrderState.PARTIAL_FILL},
    OrderState.MODIFY_PENDING: {OrderState.ACCEPTED, OrderState.REJECTED},
    # FILLED, CANCELLED, REJECTED are terminal states
}
```

### Pattern 2: Pre-Trade Risk Validation Gate
**What:** RiskManager.validate_order() called before every SendOrder; returns allow/reject
**When to use:** Every order submission path

```python
# Source: Architecture decision from CONTEXT.md
class RiskManager:
    def validate_order(self, order: Order) -> tuple[bool, str]:
        """Returns (allowed, reason). All checks must pass."""
        # 1. Market hours check
        if not self._market_hours.is_trading_allowed():
            return False, "Outside trading hours"
        # 2. Daily loss limit check
        if self._daily_loss_exceeded():
            return False, "Daily loss limit reached"
        # 3. Per-symbol weight limit
        if self._exceeds_symbol_weight(order):
            return False, f"Symbol weight exceeds {self._config.max_symbol_weight_pct}%"
        # 4. Max concurrent positions
        if self._exceeds_max_positions(order):
            return False, f"Max positions ({self._config.max_positions}) reached"
        return True, "OK"
```

### Pattern 3: Real-Time Risk Trigger (Observer on RealDataManager)
**What:** RiskManager subscribes to real-time price data and checks stop-loss/take-profit/trailing stop on every tick
**When to use:** While positions are held

```python
# RiskManager registers as subscriber to RealDataManager
real_data_manager.register_subscriber("주식체결", self._on_price_update)

def _on_price_update(self, code: str, data_dict: dict):
    """Check risk triggers for each held position on every price tick."""
    current_price = abs(int(data_dict.get(FID.CURRENT_PRICE, "0")))
    position = self._position_tracker.get_position(code)
    if not position:
        return

    # Stop-loss check
    if current_price <= position.stop_loss_price:
        self.trigger_stop_loss.emit(code, current_price)

    # Take-profit check
    if current_price >= position.take_profit_price:
        self.trigger_take_profit.emit(code, current_price)

    # Trailing stop: update high-water mark, check dynamic stop
    if current_price > position.high_water_mark:
        position.high_water_mark = current_price
        position.trailing_stop_price = int(
            current_price * (1 - self._config.trailing_stop_pct / 100)
        )
    elif current_price <= position.trailing_stop_price:
        self.trigger_trailing_stop.emit(code, current_price)
```

### Pattern 4: MarketHoursManager with QTimer
**What:** QTimer checks time at 1-second interval; emits signals at market state transitions
**When to use:** Controlling when orders can be submitted, triggering end-of-day cleanup

```python
class MarketState(Enum):
    PRE_MARKET_AUCTION = auto()   # 08:30~09:00 동시호가 -- 주문 차단
    MARKET_OPEN_BUFFER = auto()   # 09:00~09:05 안정화 대기 -- 주문 차단
    TRADING = auto()              # 09:05~15:15 정규 매매
    CLOSING = auto()              # 15:15~15:20 신규매수 중단, 청산 진행
    CLOSING_AUCTION = auto()      # 15:20~15:30 장종료 동시호가 -- 주문 차단
    CLOSED = auto()               # 15:30~ 장 종료
```

### Anti-Patterns to Avoid
- **SendOrder 반환값 0을 체결 완료로 착각:** SendOrder() 반환 0은 "접수 성공"일 뿐, 체결은 OnReceiveChejanData로 비동기 수신됨. 반드시 상태 머신으로 추적.
- **미체결 수량 무시:** 부분체결 시 미체결수량(FID 902)을 확인하지 않으면 중복 주문 발생.
- **워커 스레드에서 SendOrder 호출:** COM STA 모델 위반 -- 반드시 메인 스레드에서 호출. 워커에서 주문 요청 시 pyqtSignal로 메인 스레드에 위임.
- **가격 데이터의 부호 처리 누락:** 키움 API는 가격에 +/- 부호를 붙여 반환. 반드시 abs() 처리 후 사용.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 주문 상태 추적 | 단순 bool 플래그 | Enum 기반 상태 머신 with transition validation | 6개 상태 + 전이 규칙이 복잡; 플래그로는 불가능한 상태 조합 발생 |
| 시간대 비교 | 문자열 비교 ("09:05" > time_str) | datetime.time 객체 비교 | 문자열 비교는 포맷 의존적이고 버그 유발 |
| ChejanData 파싱 | 매번 수동 get_chejan_data 호출 | FID 상수 + 파싱 헬퍼 함수 | FID 번호 하드코딩 방지, strip()/abs() 일관 적용 |
| 설정값 관리 | 코드 내 하드코딩 | config.json의 risk 섹션 + Settings 클래스 확장 | 전략 파라미터 변경 시 코드 수정 불필요 |

**Key insight:** 키움 API의 비동기 주문 모델은 "요청 -> 접수 -> 체결" 3단계가 각각 다른 시점에 도착하므로, 상태 머신 없이는 주문 상태를 정확히 추적할 수 없다. 이것이 Phase 2의 핵심 난이도.

## Common Pitfalls

### Pitfall 1: SendOrder 반환값과 체결 혼동
**What goes wrong:** SendOrder() 반환 0을 "주문 체결"로 해석하여 중복 주문, 포지션 오추적 발생
**Why it happens:** 동기 프로그래밍 사고방식. 실제 체결은 OnReceiveChejanData 이벤트로 비동기 도착.
**How to avoid:** OrderManager가 SendOrder 후 SUBMITTED 상태로 전환, OnReceiveChejanData에서 ACCEPTED/FILLED/REJECTED로 전이. 미체결 주문은 주기적으로 opt10075 TR로 동기화.
**Warning signs:** 동일 종목에 동일 방향 주문 다수 접수, 시스템 보유수량과 실제 잔고 불일치

### Pitfall 2: ChejanData FID 값의 공백/부호 미처리
**What goes wrong:** GetChejanData 반환값에 공백, +/- 부호가 포함됨. 정수 변환 실패 또는 음수 가격 사용.
**Why it happens:** 키움 API가 모든 값을 문자열로 반환하며, 가격에 부호를 붙이는 관례.
**How to avoid:** 모든 GetChejanData 결과에 strip() 적용 (KiwoomAPI에서 이미 적용됨). 가격 필드는 abs(int(value)) 패턴 적용. 빈 문자열 체크.
**Warning signs:** ValueError 예외 발생, 음수 가격 로깅됨

### Pitfall 3: 장 종료 시 미체결 주문 방치
**What goes wrong:** 15:20 이후 미체결 주문이 남아있으면 동시호가에서 예상치 못한 가격에 체결됨
**Why it happens:** 장 종료 전 미체결 정리 로직 누락
**How to avoid:** 15:15에 MarketHoursManager가 CLOSING 시그널 emit -> 신규 매수 차단 + 보유 종목 시장가 매도. 15:19까지 미체결 주문 전량 취소 (SendOrder nOrderType=3,4).
**Warning signs:** 장 종료 후 미체결 잔량 존재

### Pitfall 4: 일일 손실 계산에 평가손익 미포함
**What goes wrong:** 실현 손익만 계산하면 보유 중인 대폭 하락 종목이 손실 한도에 잡히지 않음
**Why it happens:** 실현 손익만 추적하고 평가 손익(미실현)을 무시
**How to avoid:** 일일 손실 = 실현손익 + 평가손익(보유종목 현재가 기준). RealDataManager 가격 업데이트마다 평가손익 재계산.
**Warning signs:** 일일 손실 -3% 한도 미도달이지만 계좌 평가 금액이 이미 크게 감소

### Pitfall 5: 분할 주문 간 시간 간격 미확보
**What goes wrong:** 3회 분할 매수를 연속 SendOrder로 호출하면 사실상 한 번에 매수한 것과 동일
**Why it happens:** 시간 간격 기반 재진입 조건 없이 순차 주문만 구현
**How to avoid:** SplitOrderExecutor가 QTimer로 각 분할 주문 간 간격(기본 45초) 확보. 2차/3차 진입 전 조건 재확인 필수.
**Warning signs:** 분할 매수 3건이 1~2초 내에 모두 접수됨

## Code Examples

### SendOrder API Wrapper (KiwoomAPI 확장)

```python
# Source: Kiwoom OpenAPI+ Dev Guide v1.5, Section 6.1 함수
# SendOrder signature from official docs (page 28):
# LONG SendOrder(BSTR sRQName, BSTR sScreenNo, BSTR sAccNo,
#                LONG nOrderType, BSTR sCode, LONG nQty,
#                LONG nPrice, BSTR sHogaGb, BSTR sOrgOrderNo)

class KiwoomAPI(QObject):
    # Add to existing class
    chejan_data_received = pyqtSignal(str, int, str)  # gubun, item_cnt, fid_list

    def send_order(
        self,
        rq_name: str,
        screen_no: str,
        account_no: str,
        order_type: int,     # 1:신규매수, 2:신규매도, 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정
        code: str,
        qty: int,
        price: int,
        hoga_gb: str,        # "00":지정가, "03":시장가
        org_order_no: str,   # 신규주문은 ""
    ) -> int:
        """Submit order via SendOrder. Returns 0 on acceptance, negative on error."""
        logger.info(
            f"SendOrder: type={order_type}, code={code}, qty={qty}, "
            f"price={price}, hoga={hoga_gb}"
        )
        ret = self.ocx.dynamicCall(
            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
            [rq_name, screen_no, account_no, order_type, code, qty, price, hoga_gb, org_order_no]
        )
        if ret != 0:
            logger.error(f"SendOrder failed: ret={ret}")
        return ret

    def get_chejan_data(self, fid: int) -> str:
        """Get chejan data by FID within OnReceiveChejanData context."""
        ret = self.ocx.dynamicCall("GetChejanData(int)", fid)
        return ret.strip()
```

### OnReceiveChejanData Event Handler

```python
# Source: Kiwoom OpenAPI+ Dev Guide v1.5, Section 6.2 Event #4
# OnReceiveChejanData(LPCTSTR sGubun, LONG nItemCnt, LPCTSTR sFidList)
# sGubun: "0" = 주문체결통보, "1" = 국내주식 잔고통보, "4" = 파생상품 잔고통보

def _on_receive_chejan_data(self, gubun: str, item_cnt: int, fid_list: str):
    """Parse ChejanData and update order/position state."""
    if gubun == "0":  # 주문체결통보
        order_no = self._api.get_chejan_data(CHEJAN_FID.ORDER_NO)       # 9203
        code = self._api.get_chejan_data(CHEJAN_FID.CODE).replace("A", "")  # 9001
        order_status = self._api.get_chejan_data(CHEJAN_FID.ORDER_STATUS)   # 913
        order_qty = int(self._api.get_chejan_data(CHEJAN_FID.ORDER_QTY) or "0")   # 900
        order_price = int(self._api.get_chejan_data(CHEJAN_FID.ORDER_PRICE) or "0") # 901
        unfilled_qty = int(self._api.get_chejan_data(CHEJAN_FID.UNFILLED_QTY) or "0") # 902
        exec_price = self._api.get_chejan_data(CHEJAN_FID.EXEC_PRICE)       # 910
        exec_qty = self._api.get_chejan_data(CHEJAN_FID.EXEC_QTY)           # 911
        sell_buy = self._api.get_chejan_data(CHEJAN_FID.SELL_BUY)            # 907

        self._update_order_state(order_no, order_status, unfilled_qty, exec_price, exec_qty)

    elif gubun == "1":  # 잔고통보
        code = self._api.get_chejan_data(CHEJAN_FID.CODE).replace("A", "")  # 9001
        holding_qty = int(self._api.get_chejan_data(930) or "0")   # 보유수량
        buy_price = int(self._api.get_chejan_data(931) or "0")     # 매입단가
        current_price = abs(int(self._api.get_chejan_data(10) or "0"))  # 현재가
        pnl_rate = self._api.get_chejan_data(8019)                 # 손익률

        self._position_tracker.update_from_chejan(code, holding_qty, buy_price, current_price)
```

### ChejanData FID Constants

```python
# Source: Kiwoom OpenAPI+ Dev Guide v1.5, Section 8.19 주문체결 + 8.20 잔고

class CHEJAN_FID:
    """FID numbers for GetChejanData() calls."""

    # --- gubun=0: 주문체결통보 ---
    ACCOUNT_NO = 9201      # 계좌번호
    ORDER_NO = 9203        # 주문번호
    ADMIN_NO = 9205        # 관리자사번
    CODE = 9001            # 종목코드, 업종코드
    ORDER_CATEGORY = 912   # 주문업무분류(JJ:주식주문, FJ:선물옵션, JG:주식잔고, FG:선물옵션잔고)
    ORDER_STATUS = 913     # 주문상태(접수, 확인, 체결)
    STOCK_NAME = 302       # 종목명
    ORDER_QTY = 900        # 주문수량
    ORDER_PRICE = 901      # 주문가격
    UNFILLED_QTY = 902     # 미체결수량
    EXEC_CUMUL_AMOUNT = 903  # 체결누계금액
    ORG_ORDER_NO = 904     # 원주문번호
    ORDER_GUBUN = 905      # 주문구분(+현금내수,-현금매도...)
    TRADE_GUBUN = 906      # 매매구분(보통,시장가...)
    SELL_BUY = 907         # 매도수구분 (1:매도, 2:매수)
    ORDER_EXEC_TIME = 908  # 주문/체결시간(HHMMSSMS)
    EXEC_NO = 909          # 체결번호
    EXEC_PRICE = 910       # 체결가
    EXEC_QTY = 911         # 체결량
    CURRENT_PRICE = 10     # 현재가, 체결가, 실시간종가
    BEST_ASK = 27          # (최우선)매도호가
    BEST_BID = 28          # (최우선)매수호가
    UNIT_EXEC_PRICE = 914  # 단위체결가
    UNIT_EXEC_QTY = 915    # 단위체결량
    DAY_COMMISSION = 938   # 당일매매 수수료
    DAY_TAX = 939          # 당일매매세금

    # --- gubun=1: 잔고통보 ---
    # ACCOUNT_NO = 9201    # (same) 계좌번호
    # CODE = 9001          # (same) 종목코드
    # STOCK_NAME = 302     # (same) 종목명
    # CURRENT_PRICE = 10   # (same) 현재가
    HOLDING_QTY = 930      # 보유수량
    BUY_UNIT_PRICE = 931   # 매입단가
    TOTAL_BUY_PRICE = 932  # 총매입가
    ORDERABLE_QTY = 933    # 주문가능수량
    DAY_NET_BUY_QTY = 945  # 당일순매수량
    SELL_BUY_GUBUN = 946   # 매도/매수구분
    DAY_TOTAL_SELL_PNL = 950  # 당일 총 매도 손익
    DEPOSIT = 951          # 예수금
    REFERENCE_PRICE = 307  # 기준가
    PNL_RATE = 8019        # 손익률
```

### Order Error Codes

```python
# Source: Kiwoom OpenAPI+ Dev Guide v1.5, Section 7 에러코드표

class ORDER_ERROR:
    """SendOrder and general API error codes."""
    SUCCESS = 0                    # OP_ERR_NONE: 정상처리
    FAIL = -10                     # OP_ERR_FAIL: 실패
    LOGIN_FAIL = -100              # OP_ERR_LOGIN: 사용자정보 교환실패
    CONNECT_FAIL = -101            # OP_ERR_CONNECT: 서버접속 실패
    VERSION_FAIL = -102            # OP_ERR_VERSION: 버전처리 실패
    FIREWALL_FAIL = -103           # OP_ERR_FIREWALL: 개인방화벽 실패
    MEMORY_FAIL = -104             # OP_ERR_MEMORY: 메모리보호 실패
    INPUT_FAIL = -105              # OP_ERR_INPUT: 함수입력값 오류
    SOCKET_CLOSED = -106           # OP_ERR_SOCKET_CLOSED: 통신 연결종료
    SISE_OVERFLOW = -200           # OP_ERR_SISE_OVERFLOW: 시세조회 과부하
    RQ_STRUCT_FAIL = -201          # 전문작성 초기화 실패
    RQ_STRING_FAIL = -202          # 전문작성 입력값 오류
    NO_DATA = -203                 # OP_ERR_NO_DATA: 데이터 없음
    OVER_MAX_DATA = -204           # 조회 가능한 종목수 초과
    DATA_RCV_FAIL = -205           # 데이터수신 실패
    OVER_MAX_FID = -206            # 조회 가능한 FID수 초과
    REAL_CANCEL = -207             # 실시간 해제 오류
    ORD_WRONG_INPUT = -300         # OP_ERR_ORD_WRONG_INPUT: 입력값 오류
    ORD_WRONG_ACCTNO = -301        # 계좌 비밀번호 없음
    OTHER_ACC_USE = -302           # 타인계좌사용 오류
    MIS_2BILL_EXC = -303           # 주문가격이 20억원을 초과
    MIS_5BILL_EXC = -304           # 주문가격이 50억원을 초과
    MIS_1PER_EXC = -305            # 주문수량이 총발행주수의 1% 초과오류
    MIS_3PER_EXC = -306            # 주문수량이 총발행주수의 3% 초과오류
    SEND_FAIL = -307               # OP_ERR_SEND_FAIL: 주문전송 실패
    ORD_OVERFLOW = -308            # 주문전송 과부하 (-308 ~ -311)
    MIS_300CNT_EXC = -309          # 주문수량 300계약 초과
    MIS_500CNT_EXC = -310          # 주문수량 500계약 초과
    ORD_WRONG_ACCTINFO = -340      # 계좌정보없음
    ORD_SYMCODE_EMPTY = -500       # 종목코드없음
```

### SendOrder Parameter Constants

```python
# Source: Kiwoom OpenAPI+ Dev Guide v1.5

class OrderType:
    """nOrderType parameter for SendOrder."""
    NEW_BUY = 1       # 신규매수
    NEW_SELL = 2      # 신규매도
    CANCEL_BUY = 3    # 매수취소
    CANCEL_SELL = 4   # 매도취소
    MODIFY_BUY = 5    # 매수정정
    MODIFY_SELL = 6   # 매도정정

class HogaGb:
    """sHogaGb (거래구분) parameter for SendOrder."""
    LIMIT = "00"              # 지정가
    MARKET = "03"             # 시장가
    CONDITIONAL_LIMIT = "05"  # 조건부지정가
    BEST_LIMIT = "06"         # 최유리지정가
    FIRST_LIMIT = "07"        # 최우선지정가
    LIMIT_IOC = "10"          # 지정가IOC
    MARKET_IOC = "13"         # 시장가IOC
    BEST_IOC = "16"           # 최유리IOC
    LIMIT_FOK = "20"          # 지정가FOK
    MARKET_FOK = "23"         # 시장가FOK
    BEST_FOK = "26"           # 최유리FOK
    PRE_MARKET_CLOSE = "61"   # 장전시간외종가
    AFTER_HOURS = "62"        # 시간외단일가
    POST_MARKET_CLOSE = "81"  # 장후시간외종가
    # Note: 시장가/최유리/최우선 주문 시 nPrice=0 입력

class SCREEN:
    # Add to existing SCREEN class
    ORDER_BASE = 2000   # 주문용 화면번호 시작
```

### Market Hours FID (장시작시간)

```python
# Source: Kiwoom OpenAPI+ Dev Guide v1.5, Section 8.17

class MarketOperation:
    """FID 215 장운영구분 values."""
    PRE_MARKET = "0"       # 장시작전
    CLOSE_APPROACHING = "2"  # 장종료전
    MARKET_OPEN = "3"      # 장시작
    MARKET_CLOSE_48 = "4"  # 장종료 (4 또는 8)
    MARKET_CLOSE_9 = "9"   # 장마감
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pykiwoom 내부 QEventLoop 동기 대기 | 직접 OCX 래핑 + pyqtSignal 비동기 | Project architecture decision | 이벤트 충돌 방지, 세밀한 에러 처리 가능 |
| 단순 if/else 주문 상태 | Enum 상태 머신 with transition map | Python 3.11+ 패턴 | 불법 상태 전이 탐지, 디버깅 용이 |
| 실시간 데이터 polling | Observer 패턴 (RealDataManager 구독) | Phase 1에서 구현됨 | RiskManager가 즉시 가격 업데이트 수신 |

**Deprecated/outdated:**
- pykiwoom의 `SendOrder` 동기 래퍼: QEventLoop 충돌 위험, 직접 구현이 더 안전

## Open Questions

1. **분할 매수 시간 간격 기본값**
   - What we know: CONTEXT.md에서 30초~60초 범위 지정
   - Recommendation: **45초** 기본값. 장중 변동성 대비 충분한 간격이면서, 3회 분할 시 전체 약 2분 15초 소요로 적절.

2. **일일 손실 계산 방식**
   - What we know: 실현손익만으로는 보유 중 평가 손실 누락
   - Recommendation: **실현손익 + 평가손익(미실현) 합산**. 평가손익 = SUM((현재가 - 매입단가) * 보유수량). RealDataManager 가격 업데이트마다 재계산. 일일 손실 한도 도달 시 즉시 전량 청산.

3. **포지션 청산 시 주문 우선순위**
   - What we know: 일일 손실 한도 도달 시 전 포지션 시장가 청산 필요
   - Recommendation: **손실률 큰 종목부터 우선 청산** (최악 포지션 먼저). 시장가 주문으로 즉시 처리. 각 청산 주문 간 0.5초 간격 (주문전송 과부하 방지).

4. **opt10075 (미체결 주문 조회) 동기화 주기**
   - What we know: OnReceiveChejanData가 주 추적 수단, TR 조회는 보조
   - Recommendation: 장 시작 시 1회 + 매 5분 주기로 동기화. ChejanData 누락 대비용.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed) |
| Config file | none -- use default discovery |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRAD-03 | Order state transitions (CREATED->SUBMITTED->ACCEPTED->FILLED) | unit | `python -m pytest tests/test_order_manager.py -x` | Wave 0 |
| TRAD-03 | SendOrder wrapper returns error codes | unit | `python -m pytest tests/test_order_manager.py::test_send_order_error -x` | Wave 0 |
| TRAD-03 | ChejanData parsing extracts correct FIDs | unit | `python -m pytest tests/test_order_manager.py::test_chejan_parsing -x` | Wave 0 |
| TRAD-04 | MarketHoursManager blocks orders outside trading hours | unit | `python -m pytest tests/test_market_hours.py -x` | Wave 0 |
| TRAD-04 | MarketState transitions at correct times | unit | `python -m pytest tests/test_market_hours.py::test_state_transitions -x` | Wave 0 |
| RISK-01 | Stop-loss triggers at -2% threshold | unit | `python -m pytest tests/test_risk_manager.py::test_stop_loss -x` | Wave 0 |
| RISK-01 | Take-profit triggers at +3% threshold | unit | `python -m pytest tests/test_risk_manager.py::test_take_profit -x` | Wave 0 |
| RISK-02 | Trailing stop updates high-water mark and triggers | unit | `python -m pytest tests/test_risk_manager.py::test_trailing_stop -x` | Wave 0 |
| RISK-03 | Split order divides quantity into 3 equal parts | unit | `python -m pytest tests/test_risk_manager.py::test_split_order -x` | Wave 0 |
| RISK-04 | Per-symbol weight limit rejects over-allocation | unit | `python -m pytest tests/test_risk_manager.py::test_position_limits -x` | Wave 0 |
| RISK-04 | Daily loss limit triggers full liquidation | unit | `python -m pytest tests/test_risk_manager.py::test_daily_loss_limit -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_order_manager.py` -- covers TRAD-03 (order state machine, ChejanData parsing, SendOrder wrapper)
- [ ] `tests/test_risk_manager.py` -- covers RISK-01, RISK-02, RISK-03, RISK-04 (stop-loss, trailing stop, split orders, position limits)
- [ ] `tests/test_market_hours.py` -- covers TRAD-04 (market hours enforcement, state transitions)
- [ ] `tests/test_position_tracker.py` -- covers RISK-04 (position tracking, P&L calculation)
- [ ] `tests/conftest.py` -- extend existing with mock_order_manager, mock_risk_config, mock_position_tracker fixtures

## Sources

### Primary (HIGH confidence)
- [Kiwoom OpenAPI+ Dev Guide v1.5 PDF](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf) -- SendOrder signature, OnReceiveChejanData spec, GetChejanData FID tables (Sections 6.1, 6.2, 7, 8.17, 8.19, 8.20), error code table (Section 7)
- Existing codebase: `kiwoom_trader/api/kiwoom_api.py`, `event_handler.py`, `real_data.py`, `session_manager.py` -- Phase 1 patterns and interfaces

### Secondary (MEDIUM confidence)
- [me2nuk/stockOpenAPI GitHub](https://github.com/me2nuk/stockOpenAPI) -- SendOrder example code, FID usage patterns
- [sharebook-kr/pykiwoom GitHub](https://github.com/sharebook-kr/pykiwoom) -- ChejanData handling reference
- [Wikidocs Kiwoom API Guide](https://wikidocs.net/191643) -- Order method documentation
- [Wikidocs Kiwoom Order API](https://wikidocs.net/90346) -- Order status codes (접수=10, 정정=11, 취소=12, 접수확인=20, 정정확인=21, 취소확인=22, 거부=90,92)

### Tertiary (LOW confidence)
- Korean developer community patterns for risk management (training data based)
- Order state machine design (general software pattern, adapted to Kiwoom specifics)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all stdlib + existing Phase 1 components
- Architecture: MEDIUM-HIGH -- patterns verified against official Kiwoom dev guide, FID numbers confirmed from PDF
- Pitfalls: MEDIUM-HIGH -- well-documented in Korean developer community and official guide error codes
- ChejanData FIDs: HIGH -- extracted directly from official dev guide v1.5 Section 8.19/8.20

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (Kiwoom API is stable; FID numbers and SendOrder interface rarely change)

---
*Phase: 02-order-execution-risk-management*
*Researched: 2026-03-13*
