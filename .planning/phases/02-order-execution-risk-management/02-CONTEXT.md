# Phase 2: Order Execution & Risk Management - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

자동 주문 실행(시장가/지정가), 주문 상태 머신(접수→체결→완료), 손절/익절 트리거, 트레일링 스탑, 분할 매수/매도, 포지션 제한, 매매 시간대 관리를 구현한다. 전략 엔진(Phase 3)과 GUI(Phase 4)는 이후 페이즈에서 다룬다.

</domain>

<decisions>
## Implementation Decisions

### 손절/익절 기준
- 기본 손절: -2% (매수가 대비)
- 기본 익절: +3% (매수가 대비, 손익비 1:1.5)
- 트레일링 스탑: 최고가 대비 -1.5% 하락 시 동적 손절
- 모든 비율은 config.json에서 사용자 수정 가능 (기본값 제공)
- 실시간 체결가(RealDataManager) 이벤트로 트리거

### 분할 매수/매도 전략
- 기본 분할 횟수: 3회
- 배분 방식: 균등 분할 (33% + 33% + 34%)
- 매도도 매수와 동일 방식 (3회 균등 분할)
- 추가 진입 조건: 시간 간격 기반 (1차 매수 후 일정 시간 경과 후 조건 재확인 시 2차 진입)
- 시간 간격 기본값은 config에서 설정 가능

### 포지션 한도 & 일일 손실
- 종목별 최대 투자 비중: 총 투자금의 20%
- 동시 보유 최대 종목 수: 5종목
- 일일 최대 손실 한도: 총 투자금의 -3%
- 일일 손실 한도 도달 시: 전 포지션 시장가 청산 + 당일 신규 매수 차단
- 모든 한도는 config.json에서 수정 가능

### 매매 시간대 관리
- 매매 시작: 09:05 (장 시작 후 5분, 동시호가 종료 후 안정화 대기)
- 신규 매수 중단 + 보유 종목 청산 시작: 15:15 (장 종료 15분 전)
- 점심시간: 정상 매매 계속 (한국 주식시장 점심 휴장 없음)
- 동시호가 시간대(08:30~09:00, 15:20~15:30): 모든 주문 완전 차단
- 시간 설정은 config.json에서 수정 가능

### Claude's Discretion
- SendOrder API 래핑 및 주문 상태 머신 구현 상세
- OnReceiveChejanData 이벤트 파싱 및 주문 상태 추적 방식
- 리스크 매니저와 주문 매니저 간 인터페이스 설계
- 분할 매수 시간 간격 기본값 (30초~60초 범위에서 결정)
- 일일 손실 계산 방식 (실현손익 vs 평가손익 포함 여부)
- 포지션 청산 시 주문 우선순위 및 순서

</decisions>

<specifics>
## Specific Ideas

- 데이트레이딩 특성상 당일 전량 청산이 원칙 — 오버나잇 포지션 없음
- 손절은 빠르게(-2%), 익절은 여유 있게(+3%) — 비대칭 손익비로 승률 50%에도 수익
- 트레일링 스탑(-1.5%)은 수익 구간에서 이익 보호 역할
- 일일 손실 한도(-3%) 도달 시 강제 청산은 "최악의 날"을 제한하는 안전장치

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `KiwoomAPI`: SendOrder/OnReceiveChejanData/GetChejanData 메서드 추가 필요 — 기존 dynamicCall 패턴 그대로 확장
- `EventHandlerRegistry`: chejan(체결잔고) 핸들러 등록 패턴 추가 가능
- `RealDataManager`: 실시간 체결가 수신 — 손절/익절/트레일링 스탑 트리거 소스로 활용
- `TRRequestQueue`: 주문 관련 TR 요청(잔고 조회 등) 스로틀링에 재사용
- `SessionManager`: 주문 중 연결 끊김 감지 — 미체결 주문 상태 복구 로직 필요
- `Settings`: config.json 로딩 — 리스크 파라미터 설정값 로딩에 활용
- `constants.py`: SCREEN 번호 체계, FID 코드 — 주문용 SCREEN/FID 추가

### Established Patterns
- pyqtSignal/Slot: 크로스컴포넌트 통신 (KiwoomAPI → EventHandler → 비즈니스 로직)
- COM STA: 모든 키움 API 호출은 메인 스레드에서 — SendOrder도 동일
- QTimer: 비동기 타이머 작업 (재접속, TR 스로틀) — 매매 시간대 체크에도 활용 가능
- Observer 패턴: RealDataManager의 실시간 데이터 배포 — 리스크 매니저도 옵저버로 등록

### Integration Points
- `KiwoomAPI.ocx.OnReceiveChejanData` → 새로운 chejan_data_received 시그널 필요
- `EventHandlerRegistry` → chejan 핸들러 라우팅 추가
- `main.py` → OrderManager, RiskManager 와이어링 추가
- `config.json` → risk 섹션 (손절/익절/트레일링/포지션 한도/시간대 설정)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-order-execution-risk-management*
*Context gathered: 2026-03-13*
