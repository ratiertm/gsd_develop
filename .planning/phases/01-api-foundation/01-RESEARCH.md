# Phase 1: API Foundation - Research

**Researched:** 2026-03-13
**Domain:** Kiwoom OpenAPI+ COM/OCX connectivity, session management, TR throttling, real-time market data
**Confidence:** MEDIUM-HIGH

## Summary

Phase 1 establishes the foundational infrastructure for the Kiwoom OpenAPI+ automated day-trading system. The core challenge is correctly wrapping a 32-bit Windows COM/OCX control (Kiwoom OpenAPI+) within a PyQt5 QAxWidget, establishing a login session with auto-reconnection, implementing a compliant TR request throttle queue (1 request per 3.6+ seconds for sequential queries, max 5/second overall), and subscribing to real-time market data via SetRealReg.

The Kiwoom API operates under a Single-Threaded Apartment (STA) COM model, meaning ALL API calls must occur on the main thread where the OCX was instantiated. This is the single most important architectural constraint. The entire system architecture flows from this: PyQt5's QApplication event loop is the backbone, QTimer handles periodic work, pyqtSignal/Slot handles cross-thread communication, and heavy computation is offloaded to QThread workers.

**Primary recommendation:** Build a direct QAxWidget wrapper (not pykiwoom) for full control over event handling, error recovery, and reconnection logic. Use pykiwoom source code as reference for API patterns, but own the implementation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 프로젝트 구조: 기능별 모듈 분리 (api/, strategy/, risk/, gui/, backtest/ 등)
- 설정 파일 형식: JSON (config.json)
- 로그 관리: 용도별 + 날짜 로테이션 복합 방식 (trade-2026-03-13.log, system-2026-03-13.log, error-2026-03-13.log)
- 민감 정보: .env 환경변수로 관리, .gitignore에 추가
- 32-bit Python 3.10.x 필수 (키움 COM/OCX 32비트 전용)
- PyQt5 5.15.x 필수 (PyQt6은 QAxWidget 미지원)
- COM STA 모델 -- 모든 키움 API 호출은 OCX를 생성한 메인 스레드에서 실행
- TR 요청 3.6초 제한 준수 필수

### Claude's Discretion
- API 래핑 방식 -- pykiwoom 래퍼 활용 vs 직접 QAxWidget OCX 컨트롤 (리서치에서 프로덕션용 직접 래핑 추천)
- 세션 관리 및 재접속 전략 상세 (재시도 횟수, 간격, 장중/장외 동작 차이)
- 실시간 데이터 수신 시 버퍼링/큐잉 방식
- TR 스로틀링 큐 구현 상세 (QTimer 간격, 큐 우선순위)
- 이벤트 라우터 설계 (COM 이벤트 -> 내부 시그널 변환 방식)
- 스레딩 모델 상세 (메인 스레드 COM 호출 vs QThread 워커 분리)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONN-01 | 키움 OpenAPI+ OCX 로그인 및 세션 유지, 연결 끊김 시 자동 재접속 | QAxWidget wrapper with CommConnect(), OnEventConnect handler, GetConnectState() heartbeat, exponential backoff reconnection with SetRealReg restoration |
| CONN-02 | TR 요청 스로틀링 큐 (3.6초/건 제한 준수, QTimer 기반) | QTimer-based TRRequestQueue with 4000ms interval (safety margin), callback registry per rq_name, priority support |
| CONN-03 | 실시간 시세 이벤트 수신 (호가, 체결, 거래량 -- SetRealReg 기반) | SetRealReg with screen numbers, OnReceiveRealData dispatch, GetCommRealData for FID extraction, Observer pattern for multi-subscriber distribution |
</phase_requirements>

## Standard Stack

### Core (Phase 1 Only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10.x (32-bit) | Runtime | Only reliable version for Kiwoom COM interop. 32-bit mandatory for 32-bit OCX. |
| PyQt5 | 5.15.10 | COM bridge + event loop | QAxWidget is the only way to host Kiwoom OCX in Python. Provides QTimer, pyqtSignal, QThread, QEventLoop. |
| loguru | 0.7.x | Structured logging | Daily rotation, multiple sinks (trade/system/error logs), simpler than stdlib logging. |
| python-dotenv | 1.0.x | Environment variables | Load .env for sensitive config (account passwords, webhook URLs). |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Unit testing | Test TR queue logic, event routing, config management in isolation (without COM) |
| black | 24.x | Code formatting | Consistent style from day one |
| ruff | 0.5.x+ | Linting | Fast linting, replaces flake8+isort |

### Not Needed in Phase 1

| Library | Phase | Why Not Now |
|---------|-------|-------------|
| pandas | Phase 2+ | No data analysis yet, just raw data receipt |
| ta | Phase 3 | Technical indicators come later |
| pyqtgraph | Phase 4 | GUI charting is Phase 4 |
| requests | Phase 4 | Discord notifications later |

**Installation (Phase 1):**
```bash
# Must use 32-bit Python 3.10.x on Windows
python -m venv venv
venv\Scripts\activate

pip install PyQt5==5.15.10
pip install loguru python-dotenv
pip install pytest black ruff
```

## Architecture Patterns

### Phase 1 Project Structure
```
kiwoom_trader/
├── main.py                    # Entry point, QApplication creation
├── config/
│   ├── __init__.py
│   ├── settings.py            # Config loader (JSON + .env)
│   └── constants.py           # FID codes, TR codes, error codes
├── api/
│   ├── __init__.py
│   ├── kiwoom_api.py          # QAxWidget wrapper (COM calls only)
│   ├── event_handler.py       # OCX event routing + handler registry
│   ├── tr_request_queue.py    # TR throttle queue (QTimer, 4s interval)
│   └── real_data.py           # SetRealReg management + real-time dispatch
├── utils/
│   ├── __init__.py
│   └── logger.py              # Loguru setup (trade/system/error sinks)
├── tests/
│   ├── __init__.py
│   ├── test_tr_queue.py       # TR queue throttling logic
│   ├── test_event_handler.py  # Event routing/registry
│   ├── test_config.py         # Config loading
│   └── test_real_data.py      # Real data dispatcher
├── config.json                # System configuration
├── .env                       # Sensitive credentials (gitignored)
├── .env.example               # Template for .env
└── requirements.txt
```

### Pattern 1: Direct QAxWidget Wrapper (Recommended over pykiwoom)

**What:** Subclass or aggregate QAxWidget to wrap all Kiwoom COM calls
**Why over pykiwoom:** Full control over event handling, error recovery, reconnection. pykiwoom's internal QEventLoop usage can conflict with complex async scenarios. Reference pykiwoom source for API patterns but own the code.

```python
# Source: Kiwoom OpenAPI+ dev guide patterns + community best practices
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QEventLoop, QTimer, pyqtSignal, QObject

class KiwoomAPI(QObject):
    """Kiwoom OCX wrapper. ALL COM calls happen on main thread."""

    # Signals for cross-component communication
    connected = pyqtSignal(int)          # err_code
    disconnected = pyqtSignal()
    tr_data_received = pyqtSignal(str, str, str, str, str, int, str, str, str)
    real_data_received = pyqtSignal(str, str, str)

    def __init__(self):
        super().__init__()
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self._connect_events()

    def _connect_events(self):
        self.ocx.OnEventConnect.connect(self._on_event_connect)
        self.ocx.OnReceiveTrData.connect(self._on_receive_tr_data)
        self.ocx.OnReceiveRealData.connect(self._on_receive_real_data)

    # --- Login ---
    def comm_connect(self):
        """Opens Kiwoom login dialog."""
        self.ocx.dynamicCall("CommConnect()")

    def get_connect_state(self) -> int:
        """0=disconnected, 1=connected"""
        return self.ocx.dynamicCall("GetConnectState()")

    # --- TR Request ---
    def set_input_value(self, id: str, value: str):
        self.ocx.dynamicCall("SetInputValue(QString, QString)", id, value)

    def comm_rq_data(self, rq_name: str, tr_code: str, prev_next: int, screen_no: str):
        return self.ocx.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            rq_name, tr_code, prev_next, screen_no
        )

    def get_comm_data(self, tr_code: str, record_name: str, index: int, item_name: str) -> str:
        ret = self.ocx.dynamicCall(
            "GetCommData(QString, QString, int, QString)",
            tr_code, record_name, index, item_name
        )
        return ret.strip()

    # --- Real-time ---
    def set_real_reg(self, screen_no: str, code_list: str, fid_list: str, real_type: str):
        """
        real_type: "0" = replace existing, "1" = add to existing
        code_list: semicolon-separated stock codes
        fid_list: semicolon-separated FID numbers
        Max 100 codes per call.
        """
        self.ocx.dynamicCall(
            "SetRealReg(QString, QString, QString, QString)",
            screen_no, code_list, fid_list, real_type
        )

    def get_comm_real_data(self, code: str, fid: int) -> str:
        """Must only be called within OnReceiveRealData context."""
        ret = self.ocx.dynamicCall("GetCommRealData(QString, int)", code, fid)
        return ret.strip()

    def set_real_remove(self, screen_no: str, code: str):
        self.ocx.dynamicCall("SetRealRemove(QString, QString)", screen_no, code)

    # --- Event Handlers ---
    def _on_event_connect(self, err_code: int):
        self.connected.emit(err_code)

    def _on_receive_tr_data(self, screen_no, rq_name, tr_code, record_name,
                             prev_next, data_len, err_code, msg1, msg2):
        self.tr_data_received.emit(
            screen_no, rq_name, tr_code, record_name,
            prev_next, int(data_len), err_code, msg1, msg2
        )

    def _on_receive_real_data(self, code, real_type, real_data):
        self.real_data_received.emit(code, real_type, real_data)
```

### Pattern 2: TR Request Throttle Queue

**What:** Centralized queue that dispatches TR requests at safe intervals
**Why:** Kiwoom enforces 1 request/3.6s for sequential queries, 5 requests/second overall. Violations cause error -200 or forced disconnection.

```python
from collections import deque
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from loguru import logger

class TRRequestQueue(QObject):
    """Rate-limited TR request dispatcher using QTimer."""

    queue_empty = pyqtSignal()

    def __init__(self, kiwoom_api, interval_ms: int = 4000):
        super().__init__()
        self._queue = deque()
        self._timer = QTimer()
        self._timer.setInterval(interval_ms)  # 4s > 3.6s safety margin
        self._timer.timeout.connect(self._process_next)
        self._api = kiwoom_api
        self._is_processing = False

    def enqueue(self, tr_code: str, rq_name: str, screen_no: str,
                inputs: dict, prev_next: int = 0, callback=None):
        """Add a TR request to the queue."""
        self._queue.append({
            "tr_code": tr_code,
            "rq_name": rq_name,
            "screen_no": screen_no,
            "inputs": inputs,
            "prev_next": prev_next,
            "callback": callback,
        })
        logger.debug(f"TR enqueued: {rq_name} ({tr_code}), queue size: {len(self._queue)}")
        if not self._timer.isActive():
            self._process_next()  # Process immediately if idle
            self._timer.start()

    def _process_next(self):
        if not self._queue:
            self._timer.stop()
            self.queue_empty.emit()
            return

        request = self._queue.popleft()
        for key, value in request["inputs"].items():
            self._api.set_input_value(key, value)

        ret = self._api.comm_rq_data(
            request["rq_name"],
            request["tr_code"],
            request["prev_next"],
            request["screen_no"]
        )
        logger.info(f"TR dispatched: {request['rq_name']} -> ret={ret}, remaining={len(self._queue)}")

    @property
    def pending_count(self) -> int:
        return len(self._queue)
```

### Pattern 3: Event Handler Registry

**What:** Map rq_name/real_type to specific handler functions instead of giant if-elif chains
**When:** All OnReceiveTrData and OnReceiveRealData processing

```python
from typing import Callable, Dict, Optional
from loguru import logger

class EventHandlerRegistry:
    """Routes TR responses and real-time data to registered handlers."""

    def __init__(self):
        self._tr_handlers: Dict[str, Callable] = {}
        self._real_handlers: Dict[str, list[Callable]] = {}

    def register_tr_handler(self, rq_name: str, handler: Callable):
        self._tr_handlers[rq_name] = handler
        logger.debug(f"TR handler registered: {rq_name}")

    def register_real_handler(self, real_type: str, handler: Callable):
        self._real_handlers.setdefault(real_type, []).append(handler)
        logger.debug(f"Real handler registered: {real_type}")

    def handle_tr_data(self, rq_name: str, *args):
        handler = self._tr_handlers.get(rq_name)
        if handler:
            handler(*args)
        else:
            logger.warning(f"No TR handler for: {rq_name}")

    def handle_real_data(self, real_type: str, code: str, data: str):
        handlers = self._real_handlers.get(real_type, [])
        for handler in handlers:
            handler(code, data)
```

### Pattern 4: Session Manager with Auto-Reconnection

**What:** Monitor connection state and auto-reconnect with exponential backoff
**When:** Connection drops during market hours

```python
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from loguru import logger

class SessionManager(QObject):
    """Manages Kiwoom API session lifecycle with auto-reconnect."""

    session_restored = pyqtSignal()
    session_lost = pyqtSignal()

    MAX_RETRIES = 5
    BASE_DELAY_MS = 5000  # 5 seconds
    MAX_DELAY_MS = 60000  # 1 minute

    def __init__(self, kiwoom_api):
        super().__init__()
        self._api = kiwoom_api
        self._retry_count = 0
        self._reconnect_timer = QTimer()
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)

        # Heartbeat: check connection every 30 seconds
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.setInterval(30000)
        self._heartbeat_timer.timeout.connect(self._check_connection)

        # Registered real-time subscriptions for restoration
        self._real_subscriptions: list[dict] = []

        # Connect to API signals
        self._api.connected.connect(self._on_connect)

    def start_monitoring(self):
        self._heartbeat_timer.start()

    def _on_connect(self, err_code: int):
        if err_code == 0:
            logger.info("Login successful")
            self._retry_count = 0
            self._heartbeat_timer.start()
            if self._real_subscriptions:
                self._restore_real_subscriptions()
            self.session_restored.emit()
        else:
            logger.error(f"Login failed: err_code={err_code}")
            self._schedule_reconnect()

    def _check_connection(self):
        state = self._api.get_connect_state()
        if state == 0:
            logger.warning("Connection lost detected by heartbeat")
            self._heartbeat_timer.stop()
            self.session_lost.emit()
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        if self._retry_count >= self.MAX_RETRIES:
            logger.critical(f"Max reconnection attempts ({self.MAX_RETRIES}) reached")
            return
        delay = min(
            self.BASE_DELAY_MS * (2 ** self._retry_count),
            self.MAX_DELAY_MS
        )
        self._retry_count += 1
        logger.info(f"Reconnect attempt {self._retry_count} in {delay}ms")
        self._reconnect_timer.setInterval(delay)
        self._reconnect_timer.start()

    def _attempt_reconnect(self):
        logger.info("Attempting reconnection...")
        self._api.comm_connect()

    def track_real_subscription(self, screen_no, code_list, fid_list, real_type):
        """Track subscriptions for restoration after reconnect."""
        self._real_subscriptions.append({
            "screen_no": screen_no,
            "code_list": code_list,
            "fid_list": fid_list,
            "real_type": real_type,
        })

    def _restore_real_subscriptions(self):
        logger.info(f"Restoring {len(self._real_subscriptions)} real-time subscriptions")
        for sub in self._real_subscriptions:
            self._api.set_real_reg(
                sub["screen_no"], sub["code_list"],
                sub["fid_list"], sub["real_type"]
            )
```

### Pattern 5: Loguru Multi-Sink Configuration

**What:** Separate log files by purpose with daily rotation, as per user decision

```python
from loguru import logger
import sys
from pathlib import Path

def setup_logging(log_dir: str = "logs"):
    """Configure loguru with purpose-specific daily-rotated log files."""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console output
    logger.add(sys.stderr, level="INFO",
               format="{time:HH:mm:ss} | {level:<8} | {message}")

    # System log: general application events
    logger.add(
        log_path / "system-{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",  # New file at midnight
        retention="30 days",
        filter=lambda record: record["extra"].get("log_type", "system") == "system",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {module}:{function}:{line} | {message}",
    )

    # Trade log: order/execution events only
    logger.add(
        log_path / "trade-{time:YYYY-MM-DD}.log",
        level="INFO",
        rotation="00:00",
        retention="365 days",  # Keep trade logs for 1 year
        filter=lambda record: record["extra"].get("log_type") == "trade",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}",
    )

    # Error log: warnings and above
    logger.add(
        log_path / "error-{time:YYYY-MM-DD}.log",
        level="WARNING",
        rotation="00:00",
        retention="90 days",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {module}:{function}:{line} | {message}\n{exception}",
    )

# Usage:
# logger.info("System started")                                        -> system log
# logger.bind(log_type="trade").info("BUY 005930 10 shares @ 72000")   -> trade log
# logger.error("Connection failed")                                     -> error log + system log
```

### Anti-Patterns to Avoid (Phase 1 Specific)

- **God Class:** Do NOT put login, TR, real-time, config all in one KiwoomAPI class. Separate into KiwoomAPI (COM calls), EventHandlerRegistry (routing), TRRequestQueue (throttling), SessionManager (connection).
- **Polling Loop:** Never `while True` or `time.sleep()` in main thread. Use QTimer and QEventLoop exclusively.
- **Global State:** Never use module-level dicts for connection state or subscription tracking. Use class instances.
- **Bare print():** Use loguru from day one. print() makes post-incident analysis impossible.
- **Ignoring Error Codes:** Always check dynamicCall return values and OnEventConnect err_code.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting | Custom time.sleep() loops | QTimer-based queue (see Pattern 2) | sleep() blocks event loop, kills COM events |
| Logging with rotation | Custom file management | loguru with rotation/retention params | Edge cases: midnight rollover, disk full, concurrent writes |
| Environment variables | Custom .env parser | python-dotenv | Standard, handles quoting, comments, multiline |
| COM/OCX hosting | pywin32 COM automation | PyQt5 QAxWidget | pywin32 can call COM methods but cannot host OCX visual controls needed for event-driven Kiwoom API |
| Event loop | asyncio or threading loops | QApplication.exec_() | Kiwoom OCX requires Qt event loop. Mixing asyncio causes deadlocks |

**Key insight:** Kiwoom API's COM/OCX model dictates that the Qt event loop is non-negotiable. Every "convenience" shortcut that bypasses the Qt event loop (sleep, polling, asyncio) will cause silent failures or crashes.

## Common Pitfalls

### Pitfall 1: TR Rate Limit Violation
**What goes wrong:** Exceeding 1 request/3.6s for sequential queries or 5/sec overall causes error -200, forced disconnection, or temporary ban.
**Why it happens:** for-loops calling TR sequentially; confusing real-time data (free, event-based) with TR queries (rate-limited).
**How to avoid:** Centralized TRRequestQueue with 4000ms interval (400ms safety margin). Use SetRealReg for live data instead of polling via TR.
**Warning signs:** Error code -200 from CommRqData; sudden disconnection during data fetching.

### Pitfall 2: Main Thread Blocking
**What goes wrong:** Heavy computation on main thread stops COM event processing -- real-time data stops, heartbeat fails, connection drops.
**Why it happens:** Indicator calculation, file I/O, or synchronous waits on main thread.
**How to avoid:** Keep main thread for COM calls + event dispatch only. Offload computation to QThread workers. Use pyqtSignal to send results back.
**Warning signs:** GUI freeze; real-time data gaps; OnReceiveRealData events arriving in bursts.

### Pitfall 3: SetRealReg Subscription Loss After Reconnect
**What goes wrong:** After automatic reconnection, real-time data stops because subscriptions are not restored.
**Why it happens:** SetRealReg state is server-side; reconnection creates a fresh session with no subscriptions.
**How to avoid:** Track all SetRealReg calls in SessionManager. On successful reconnect (OnEventConnect err_code=0), replay all subscriptions.
**Warning signs:** Data flowing before disconnect but silent after reconnect.

### Pitfall 4: GetCommRealData Outside Event Context
**What goes wrong:** Calling GetCommRealData outside of OnReceiveRealData event handler returns stale or empty data.
**Why it happens:** The data buffer is only valid within the event callback scope.
**How to avoid:** Extract ALL needed FID values within the OnReceiveRealData handler and pass them as a dict/dataclass to downstream consumers.
**Warning signs:** Empty strings or stale values from GetCommRealData.

### Pitfall 5: GetCommData Return Value Quirks
**What goes wrong:** String values from GetCommData contain leading/trailing spaces and sometimes sign characters (+/-) in numeric fields.
**Why it happens:** Kiwoom API pads all return values with spaces. Numeric values use + or - prefix.
**How to avoid:** Always call .strip() on return values. For numeric conversion: strip, remove +/- prefix, then convert. Create utility functions.
**Warning signs:** int() or float() conversion errors; comparison failures due to whitespace.

### Pitfall 6: Screen Number (화면번호) Conflicts
**What goes wrong:** Using the same screen number for different TR requests causes response routing errors.
**Why it happens:** Screen numbers are used internally to route OnReceiveTrData events. Reusing them mixes up responses.
**How to avoid:** Assign unique screen numbers per TR type or use an auto-incrementing screen number manager (4-digit string, "0001" to "9999").
**Warning signs:** TR responses arriving at wrong handler; intermittent wrong data.

## Code Examples

### Config Management (JSON + .env)

```python
# config/settings.py
import json
from pathlib import Path
from dotenv import load_dotenv
import os
from loguru import logger

class Settings:
    """Application settings from config.json + .env"""

    def __init__(self, config_path: str = "config.json"):
        load_dotenv()  # Load .env file

        self._config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"Config loaded from {self._config_path}")
                return config
        else:
            logger.warning(f"Config file not found: {self._config_path}, using defaults")
            return self._default_config()

    def _default_config(self) -> dict:
        return {
            "tr_interval_ms": 4000,
            "heartbeat_interval_ms": 30000,
            "max_reconnect_retries": 5,
            "real_data_fids": {
                "stock_execution": "10;11;12;13;15;20;21;25;27;28;41;61;62;63;64;65;66;67;68;69",
                "stock_orderbook": "41;61;62;63;64;65;66;67;68;69;71;72;73;74;75;76;77;78;79;80"
            },
            "watchlist": [],
            "log_dir": "logs"
        }

    @property
    def account_password(self) -> str:
        return os.getenv("KIWOOM_ACCOUNT_PW", "")

    @property
    def is_simulation(self) -> bool:
        return os.getenv("KIWOOM_SIMULATION", "true").lower() == "true"
```

### Main Entry Point

```python
# main.py
import sys
from PyQt5.QtWidgets import QApplication
from api.kiwoom_api import KiwoomAPI
from api.event_handler import EventHandlerRegistry
from api.tr_request_queue import TRRequestQueue
from api.real_data import RealDataManager
from config.settings import Settings
from utils.logger import setup_logging
from loguru import logger

def main():
    setup_logging()
    logger.info("=== KiwoomDayTrader starting ===")

    app = QApplication(sys.argv)
    settings = Settings()

    # Initialize core components
    api = KiwoomAPI()
    event_registry = EventHandlerRegistry()
    tr_queue = TRRequestQueue(api, interval_ms=settings._config["tr_interval_ms"])
    # real_data_manager = RealDataManager(api, event_registry)
    # session_manager = SessionManager(api)

    # Connect event routing
    api.tr_data_received.connect(
        lambda *args: event_registry.handle_tr_data(args[1], *args)  # args[1] = rq_name
    )
    api.real_data_received.connect(
        lambda code, real_type, data: event_registry.handle_real_data(real_type, code, data)
    )

    # Login
    api.comm_connect()
    logger.info("Login dialog opened, waiting for user...")

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
```

### Real-time FID Constants

```python
# config/constants.py

# Key FID codes for real-time data
# Source: Kiwoom OpenAPI+ dev guide, KOA Studio real-time tab
class FID:
    """Kiwoom real-time data Field IDs."""

    # 주식체결 (Stock Execution) real type
    CURRENT_PRICE = 10        # 현재가
    PREV_CLOSE_DIFF = 11      # 전일대비
    DIFF_RATE = 12             # 등락율
    PREV_CLOSE_DIFF_SIGN = 25 # 전일대비기호
    VOLUME = 13                # (누적)거래량
    EXEC_TIME = 20             # 체결시간 (HHMMSS)
    EXEC_VOLUME = 15           # 체결량
    OPEN_PRICE = 16            # 시가
    HIGH_PRICE = 17            # 고가
    LOW_PRICE = 18             # 저가
    ASK_PRICE_1 = 27           # 매도호가1
    BID_PRICE_1 = 28           # 매수호가1
    TRADE_AMOUNT = 14          # 거래대금
    EXEC_STRENGTH = 228        # 체결강도

    # 주식호가 (Stock Orderbook) real type
    # 매도호가 1~10: FID 41, 61, 62, 63, 64, 65, 66, 67, 68, 69
    # 매수호가 1~10: FID 51, 71, 72, 73, 74, 75, 76, 77, 78, 79
    # 매도호가수량 1~10: FID 61, 62, ...
    # 매수호가수량 1~10: FID 71, 72, ...
    ASK_PRICES = [41, 61, 62, 63, 64, 65, 66, 67, 68, 69]
    BID_PRICES = [51, 71, 72, 73, 74, 75, 76, 77, 78, 79]

    # 장시작시간 (Market Time) real type
    MARKET_OP = 215            # 장운영구분 (0:장시작전, 2:장마감전, 3:장시작, 4:장종료 등)
    MARKET_TIME = 20           # 체결시간

# Screen numbers - use unique per TR type
class SCREEN:
    LOGIN = "0000"
    TR_BASE = 1000  # Auto-increment from here
    REAL_BASE = 5000

# OnEventConnect error codes
class LOGIN_ERROR:
    SUCCESS = 0
    PASSWORD_ERROR = -100
    ACCOUNT_DIFF = -101
    MONTHLY_FEE_UNPAID = -102
    IP_RESTRICTED = -103
    VERSION_MISMATCH = -104
    AUTH_ERROR = -105
    USER_LOCKED = -106
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pykiwoom for all wrapping | Direct QAxWidget wrapper | N/A (architectural choice) | Full control over reconnection, event handling, error recovery |
| time.sleep() for rate limit | QTimer-based queue | Well-established pattern | Non-blocking, preserves event loop |
| print() debugging | loguru structured logging | loguru is mature | Daily rotation, multiple sinks, better filtering |
| Single-file scripts | Modular package structure | Best practice | Testable, maintainable, extensible |
| Polling GetConnectState | Heartbeat QTimer + event-driven | Community pattern | Reliable disconnection detection |

## Open Questions

1. **Exact TR rate limit rules in current API version**
   - What we know: Official docs say 1초 5회 limit. Community reports 3.6초 interval for sequential/continuous queries. Error -200 for overload.
   - What's unclear: Whether 3.6s is per-TR-type or global. Whether limits changed in recent API updates.
   - Recommendation: Use 4000ms (4s) as safe interval. Log all TR request timestamps to verify compliance during testing. Check latest dev guide version from kiwoom.com.

2. **SetRealReg maximum simultaneous registrations**
   - What we know: Max 100 codes per single SetRealReg call. Total limit unclear (community suggests ~200-300 total).
   - What's unclear: Whether screen number isolation allows more total registrations.
   - Recommendation: Start with conservative limits. Track registration count. Use screen number rotation if needed.

3. **Auto-login behavior after reconnection**
   - What we know: CommConnect() opens login dialog. Auto-login setting exists in Kiwoom OpenAPI+ manager.
   - What's unclear: Whether auto-login persists across network interruptions or requires fresh dialog.
   - Recommendation: Implement both paths -- attempt auto-reconnect, fall back to login dialog notification.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | none -- Wave 0 will create pytest.ini |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONN-01 | Login flow completes with err_code=0 | integration (manual, needs OCX) | Manual on Windows with Kiwoom installed | No -- Wave 0 |
| CONN-01 | Auto-reconnect with exponential backoff | unit (mock API) | `python -m pytest tests/test_session_manager.py -x` | No -- Wave 0 |
| CONN-01 | SetRealReg subscriptions restored after reconnect | unit (mock API) | `python -m pytest tests/test_session_manager.py::test_restore_subscriptions -x` | No -- Wave 0 |
| CONN-01 | Heartbeat detects disconnection | unit (mock API) | `python -m pytest tests/test_session_manager.py::test_heartbeat -x` | No -- Wave 0 |
| CONN-02 | TR queue enforces 4s minimum interval | unit | `python -m pytest tests/test_tr_queue.py::test_interval -x` | No -- Wave 0 |
| CONN-02 | TR queue processes requests in FIFO order | unit | `python -m pytest tests/test_tr_queue.py::test_fifo -x` | No -- Wave 0 |
| CONN-02 | TR queue stops timer when empty | unit | `python -m pytest tests/test_tr_queue.py::test_empty_stop -x` | No -- Wave 0 |
| CONN-03 | SetRealReg registers codes and receives OnReceiveRealData | integration (needs OCX) | Manual on Windows | No -- Wave 0 |
| CONN-03 | Event handler registry routes real_type to correct handler | unit | `python -m pytest tests/test_event_handler.py -x` | No -- Wave 0 |
| CONN-03 | GetCommRealData values parsed correctly (strip, sign removal) | unit | `python -m pytest tests/test_real_data.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pytest.ini` -- pytest configuration with Python path
- [ ] `tests/conftest.py` -- shared fixtures (mock KiwoomAPI, mock QTimer, mock QApplication)
- [ ] `tests/test_tr_queue.py` -- covers CONN-02 throttling logic
- [ ] `tests/test_session_manager.py` -- covers CONN-01 reconnection logic
- [ ] `tests/test_event_handler.py` -- covers CONN-03 event routing
- [ ] `tests/test_real_data.py` -- covers CONN-03 data parsing
- [ ] `tests/test_config.py` -- covers config loading
- [ ] Framework install: `pip install pytest` -- if not already installed

**Note:** CONN-01 and CONN-03 integration tests require a Windows machine with Kiwoom OpenAPI+ installed and a valid account. Unit tests can mock the QAxWidget interface and run anywhere.

## Sources

### Primary (HIGH confidence)
- [Kiwoom OpenAPI+ Dev Guide v1.7 (PDF)](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.7.pdf) - Official function signatures, event parameters
- [Qt 5.15 QAxWidget Documentation](https://doc.qt.io/qt-5/qaxwidget.html) - QAxWidget API, dynamicCall usage
- [PyQt5 QAxWidget API Reference](https://doc.bccnsoft.com/docs/PyQt5/api/qaxwidget.html) - Python binding specifics

### Secondary (MEDIUM confidence)
- [WikiDocs: 퀀트투자를 위한 키움증권 API](https://wikidocs.net/book/1173) - SetRealReg usage, FID codes, login flow
- [WikiDocs: 주식체결 실시간 데이터](https://wikidocs.net/91556) - FID code details for stock execution
- [KOAPY Rate Limit Discussion](https://github.com/elbakramer/koapy/discussions/31) - Throttling strategies, 230ms delay analysis
- [stockOpenAPI GitHub README](https://github.com/me2nuk/stockOpenAPI) - Error codes, API function reference
- [Kiwoom API Default Dev Guide (jackerlab)](https://blog.jackerlab.com/kiwoom-api-default-dev-guide-get-data) - Real-time data handling patterns

### Tertiary (LOW confidence)
- FID code exact numbers for 호가 (orderbook) -- partially verified, need KOA Studio confirmation
- SetRealReg total registration limit (~200-300) -- community reports only, not officially documented

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python 3.10 32-bit + PyQt5 5.15.x is the only viable combination, well-documented
- Architecture: MEDIUM-HIGH - COM STA model and QAxWidget patterns are well-established; reconnection strategy is custom but follows proven patterns
- Pitfalls: HIGH - TR rate limits, main thread blocking, and subscription loss are extensively documented in Korean dev community
- FID codes: MEDIUM - Core FIDs verified across multiple sources; complete list requires KOA Studio verification

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (Kiwoom API is stable, changes infrequently)
