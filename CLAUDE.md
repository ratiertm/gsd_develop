# KiwoomDayTrader

키움증권 OpenAPI+를 활용한 Python 주식 데이트레이딩 자동매매 시스템.

## Quick Reference

- **Language**: Python 3.10 (32-bit 필수 — 키움 OpenAPI+ COM 제약)
- **GUI**: PyQt5
- **Chart**: pyqtgraph
- **Logging**: loguru
- **Test**: pytest
- **Platform**: Windows 전용 (키움 OpenAPI+ COM 기반)

## Runtime Environment

- **32-bit Python**: `C:\Users\Mindbuild\Python310-32\python.exe`
- **가상환경**: `.venv32/` (32-bit, PyQt5/loguru/pyqtgraph/python-dotenv)
- **인증 정보**: `.env` 파일 (커밋 금지, `.gitignore`에 등록됨)
- **설정**: `config.json` (watchlist, 전략, 리스크 파라미터)

## Project Structure

```
kiwoom_trader/
  api/              # Phase 1: 키움 API 연동 (OCX, 이벤트, TR 큐, 세션)
  config/           # 설정 (constants, settings - config.json + .env)
  core/             # Phase 2-3: 매매 엔진 (주문, 리스크, 인디케이터, 전략, 포지션)
  gui/              # Phase 4: PyQt5 GUI (대시보드, 차트, 전략탭, 알림)
    widgets/        # 재사용 위젯 (캔들스틱, 인디케이터 차트, 토스트)
    notification/   # 알림 시스템 (Notifier, Discord 웹훅)
  backtest/         # Phase 5: 백테스트 (DataSource, 비용모델, 엔진, 성과분석, QThread)
    replay_engine.py  # 틱 리플레이 엔진 (수집 데이터 → 라이브 파이프라인 재생)
  utils/            # 로깅 설정
  main.py           # 진입점 - 모든 컴포넌트 와이어링 (Phase 1~10)
scripts/
  collector.py      # 데이터 수집기 (분봉 TR 조회 + 실시간 틱 수집 → SQLite/CSV)
  replay.py         # 리플레이 CLI (수집 DB → ReplayEngine → 성과 분석)
  realtime_collector.py  # 실시간 수집 전용 (collector.py 이전 버전)
  fetch_minute_candles.py  # 분봉 조회 전용
data/               # 수집 데이터 (realtime_{date}.db, 체결/호가 CSV 등)
tests/              # pytest 테스트
  test_live_simulation.py  # Phase 7~9 샘플 데이터 E2E 시뮬레이션 (17건)
  test_live_order.py       # Phase 8 모의투자 주문 테스트 (장중 실행용)
  test_replay_engine.py    # ReplayEngine 단위 테스트
docs/               # 설계 문서 (collector-spec.md, replay-engine-spec.md)
.planning/          # GSD 워크플로우 (로드맵, 요구사항, 페이즈별 계획/검증)
```

## Commands

```bash
# 앱 실행 (32-bit Python 필수)
.venv32\Scripts\python.exe -m kiwoom_trader.main

# 데이터 수집 (32-bit 필수 — 키움 COM 사용)
.venv32\Scripts\python.exe scripts/collector.py
.venv32\Scripts\python.exe scripts/collector.py --interval 3 --days 5
.venv32\Scripts\python.exe scripts/collector.py --skip-history --types 체결,호가

# 틱 리플레이 (64-bit 가능 — COM 불필요)
python scripts/replay.py data/realtime_20260317.db
python scripts/replay.py data/realtime_20260317.db --codes 005930 --capital 50000000

# 테스트 실행 (32-bit)
.venv32\Scripts\python.exe -m pytest tests/test_live_simulation.py -v

# 테스트 실행 (64-bit — COM 불필요한 단위 테스트)
python -m pytest tests/ -x -q --ignore=tests/test_live_order.py
```

## Architecture Patterns

- **PyQt5 try/except fallback**: 모든 Qt import는 `try/except ImportError`로 감싸서 macOS에서도 import 가능. `_HAS_PYQT5` 플래그로 분기.
- **Config-driven**: 모든 파라미터는 `config.json`으로 관리. `Settings` 클래스가 읽기/쓰기 담당. 인증 정보는 `.env`.
- **Observer pattern**: callback 등록 방식 (RealDataManager, CandleAggregator, MarketHoursManager).
- **Phase-based wiring**: `main.py`에서 Phase 1~10 순서로 컴포넌트 생성 및 시그널 연결.
- **GSD + PDCA 하이브리드**: v2.0부터 GSD 로드맵 + PDCA 실행 방식. 각 Phase에 Gate Condition 필수.

## Key Conventions

- 키움 API 가격 데이터는 `abs(int(raw.strip() or "0"))` 패턴으로 파싱 (부호 규약 처리)
- TR 요청은 반드시 `TRRequestQueue`를 통해 (3.6초 제한 준수)
- `Candle` dataclass가 모든 봉 데이터의 표준 형식
- `Signal` dataclass가 매매 신호의 표준 형식
- 리스크 파라미터는 `RiskConfig` dataclass로 통합 관리
- 백테스트/리플레이 비용: 매수 수수료 + 매도 수수료 + 거래세 0.18%(매도) + 슬리피지
- ReplayEngine은 raw tick → CandleAggregator → StrategyManager (라이브와 동일 코드 경로)
- collector.py: Phase1(분봉 TR) → Phase2(실시간 틱) → SQLite/CSV 이중 저장, 18시 자동 종료
- 수집 DB(체결 테이블)의 fid_* 컬럼이 ReplayEngine의 입력 데이터
- ConditionEngine: `value`(고정값) 또는 `value_ref`(인디케이터 참조) 중 하나로 비교
- 튜플 인디케이터 서브컴포넌트: `bollinger_upper/middle/lower`, `macd_line/signal/histogram`
- 전략 설정 JSON: `docs/condition-engine-enhancement-spec.md` 참조
- market_context: 전일 OHLCV/패턴(`prev_close`, `prev_body_pct` 등) + 시장 지수(`kospi_pct`)
- context 내장 키: `price`, `volume`, `hour`, `minute` + 인디케이터 + 서브컴포넌트 + 전일 + 시장
- 전략 시뮬레이션 결과/비용 분석: `docs/strategy-simulation-review.md`
- chejan = 체결/잔고. `OnReceiveChejanData`의 gubun=0은 체결, gubun=1은 잔고
- 주문번호 매핑: submit_order()는 임시번호(ORD_*), chejan에서 실제 거래소 번호로 전환
- OrderManager는 `threading.RLock`으로 chejan 이벤트 동시 접근 보호
- 계좌 전환/모드 전환 시 `BalanceQuery` → `PositionTracker` 자동 재동기화
- 세션 복구(`session_restored`) 시 잔고 자동 재조회
- RiskManager 시그널(손절/익절/트레일링/일일손실) → Notifier 3채널 알림 연결
- `total_capital > 0` 검증 (RiskManager), 빈 계좌번호 주문 차단 (OrderManager)

## Phase Status

### v1.0 (Complete)

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | API Foundation (OCX, 이벤트, TR 큐, 실시간) | Complete |
| 2 | Order Execution & Risk Management | Complete |
| 3 | Data Pipeline & Strategy Engine | Complete |
| 4 | Monitoring & Operations (GUI) | Complete |
| 5 | Backtest & Validation | Complete |

### v2.0 — API 실연동 (Active)

| Phase | Description | Status |
|-------|-------------|--------|
| 6 | 로그인/접속 + 계좌 관리 | Complete |
| 7 | 실시간 시세 (SetRealReg) | 코드 완료, 장중 Gate 검증 필요 |
| 8 | 주문 실행 (모의투자) | 코드 완료, 장중 Gate 검증 필요 |
| 9 | 잔고/포지션 동기화 | 코드 완료 (PDCA Check 통과) |
| 10 | E2E 통합 | 코드 완료 (장중 30분 라이브 러닝 필요) |

### v3.0 — 전략 엔진 고도화 (Planned)

| Phase | Description | Status |
|-------|-------------|--------|
| 11 | ConditionEngine value_ref — 인디케이터 간 비교 지원 | Complete |
| 12 | 튜플 인디케이터 서브컴포넌트 (Bollinger/MACD) | Complete |
| 13 | GUI 전략 편집기 value_ref 지원 | Planned |
| 14 | 레퍼런스 전략 (볼린저, MACD 크로스, VWAP) | Complete |
| 15 | 시장 컨텍스트 (전일 데이터 + 지수 필터) | Complete |
| 16 | 전략 시뮬레이션 검토 (6종 전략, 봉 간격, 비용 분석) | Complete |

**설계 문서:**
- `docs/condition-engine-enhancement-spec.md` — value_ref 설계
- `docs/strategy-simulation-review.md` — 전략 시뮬레이션 검토 (비용/필터/봉 간격/일봉 패턴)

## Testing Notes

- 32-bit venv(`.venv32`)로 실행해야 COM 관련 테스트 통과
- `test_live_simulation.py`: 샘플 데이터 E2E (13건, COM 불필요)
- `test_live_order.py`: 장중 모의투자 실주문 테스트 (수동 실행)
- PyQt5 의존 테스트는 `pytest.importorskip("PyQt5")` 또는 `@pytest.mark.skipif`로 CI 호환
- 성과 지표(performance.py)는 순수 함수 — stdlib만 사용
