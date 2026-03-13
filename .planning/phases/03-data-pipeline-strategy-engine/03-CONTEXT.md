# Phase 3: Data Pipeline & Strategy Engine - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

기술적 지표(SMA, EMA, RSI, MACD, Bollinger Bands, VWAP, OBV)가 실시간 분봉 데이터를 처리하고, 조건 엔진이 복합 규칙(AND/OR 조합)을 평가하여 매수/매도 신호를 생성하며, 이 신호가 RiskManager → OrderManager를 거쳐 자동 체결되는 완전한 자동매매 루프를 구현한다. 페이퍼 트레이딩 모드를 포함하여 실계좌 투입 전 전략 검증이 가능하다. GUI(Phase 4)와 백테스트(Phase 5)는 이후 페이즈에서 다룬다.

</domain>

<decisions>
## Implementation Decisions

### 인디케이터 계산 방식
- 분봉 기반 계산 — 틱 데이터를 실시간으로 분봉 OHLCV로 집계 (TR 요청 없음)
- 분봉 주기는 config.json에서 설정 가능 (기본값 제공)
- 인디케이터 업데이트는 분봉 완성 시점에만 (진행 중 봉에서는 재계산 안 함)
- 장 시작 시 워밍업: 충분한 분봉 수집될 때까지 신호 없음 (예: SMA(20)이면 20분봉 후 첫 신호)
- 증분 계산 (incremental) — 전체 윈도우 재계산이 아닌 새 봉 추가 시 업데이트
- 7개 인디케이터: SMA, EMA, RSI, MACD, Bollinger Bands, VWAP, OBV

### 인디케이터 파라미터 관리
- 전략별 내장 — 각 전략 프리셋에 해당 전략이 사용하는 인디케이터 + 파라미터 포함
- 예: RSI역발 전략 = {indicator: RSI, period: 14, oversold: 30, overbought: 70}

### 전략 규칙 설계
- AND/OR 복합 조건 조합 — 여러 조건을 AND/OR로 조합하여 전략 구성
- 진입(entry) + 청산(exit) 조건을 하나의 전략에 통합 정의
- 기본 프리셋 2개 제공:
  1. RSI 역발 전략: RSI < 30 매수, RSI > 70 매도
  2. 이동평균 교차 전략: 단기 EMA > 장기 EMA 매수 (골든크로스), 역전 시 매도
- 가격/거래량 조건 포함 가능 (예: 거래량 > 20일 평균 200%)
- 전략 설정은 config.json 내 strategies 섹션에 저장

### 멀티 전략 & 종목 관리
- 종목당 여러 전략 동시 적용 가능
- 신호 충돌 시 전략별 priority 설정으로 우선순위 결정
- 감시 종목 목록은 config.json에서 설정 (종목별 적용 전략 지정)
- 전략별 enabled 플래그로 장 중 개별 on/off 제어 가능

### 신호 발생 및 실행 흐름
- 신호 발생 → RiskManager.validate_order() → OrderManager.submit_order() 즉시 실행
- 동일 종목 중복 신호: 쿨다운 적용 (포지션 보유 중 동일 방향 신호 무시, 시간 기반 쿨다운 config 설정)
- 기본 주문 유형: 시장가 (데이트레이딩 체결 속도 우선)

### 페이퍼 트레이딩 모드
- 실제 주문 없이 전략 신호만 기록하는 모드 포함 (실계좌 투입 전 필수)
- 가상 손익 계산: 신호 발생 시점의 현재가를 가상 체결가로 사용
- 거래 기록: CSV 파일 (trades.csv)에 기록 — 분석 용이
- config.json에서 mode: "paper" / "live" 전환

### Claude's Discretion
- IndicatorEngine 클래스 설계 및 증분 계산 알고리즘 구현
- CandleAggregator 틱→분봉 변환 내부 구현
- ConditionEngine 규칙 평가 엔진 아키텍처
- StrategyManager 전략 로드/관리 구조
- 분봉 주기 기본값 (1분/3분/5분 중 선택)
- 쿨다운 시간 기본값
- CSV 파일 컬럼 구조

</decisions>

<specifics>
## Specific Ideas

- 데이트레이딩 특성상 빠른 반응이 중요하지만, 분봉 완성 시점에만 계산하여 whipsaw 방지
- VWAP은 데이트레이더의 핵심 기준선 — 가격이 VWAP 위/아래인지가 중요한 진입 필터
- 페이퍼 트레이딩은 실전 투입 전 안전장치 — Phase 3 Success Criteria에도 명시됨
- 전략 프리셋은 "바로 사용 가능한 기본값"이지만, 사용자가 자유롭게 조건 조합 가능
- 기존 RealDataManager의 observer 패턴을 그대로 활용 — CandleAggregator가 구독자로 등록

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RealDataManager`: 실시간 체결가 수신, observer 패턴으로 subscriber 등록 가능 — CandleAggregator가 "주식체결" 구독
- `RiskManager.validate_order()`: 6-check pre-trade validation gate — 전략 신호가 이 게이트를 통과해야 주문 실행
- `OrderManager.submit_order()`: 주문 실행 경로 — 전략 엔진의 최종 출력
- `RiskManager.on_price_update()`: 실시간 가격 트리거 — 전략 엔진과 병렬로 동작
- `PositionTracker`: 보유 포지션 추적 — 중복 신호 필터링, 포지션 존재 여부 확인에 활용
- `Settings`: config.json 로딩 패턴 — strategies 섹션 추가 로딩
- `constants.py`: FID 코드 — 틱 데이터에서 가격/거래량 추출

### Established Patterns
- PyQt5 try/except fallback: macOS 개발 환경 호환 — 새 모듈도 동일 패턴 적용
- pyqtSignal/Slot: 컴포넌트 간 통신 — IndicatorEngine → ConditionEngine → StrategyManager 시그널 체인
- Observer 패턴: RealDataManager subscribers — CandleAggregator도 동일 패턴
- Config-driven: 모든 파라미터 config.json에서 설정 — 전략/인디케이터도 동일
- TDD: RED→GREEN 패턴 — Phase 2에서 확립

### Integration Points
- `RealDataManager.register_subscriber("주식체결", candle_aggregator.on_tick)` — 틱 데이터 수신
- `RiskManager.validate_order()` → 전략 신호 검증 게이트
- `OrderManager.submit_order()` → 전략 신호 실행
- `main.py` → StrategyEngine 와이어링 추가
- `config.json` → strategies 섹션, indicators 섹션, watchlist 섹션

</code_context>

<deferred>
## Deferred Ideas

- 전략 자동 최적화 (파라미터 그리드 서치/유전 알고리즘) — v2 STRT-03
- 전체 시장 스캔으로 조건 충족 종목 자동 탐색 — v2 범위
- 멀티 타임프레임 분석 (1분봉 + 5분봉 동시) — 복잡도 높음, v2 검토

</deferred>

---

*Phase: 03-data-pipeline-strategy-engine*
*Context gathered: 2026-03-14*
