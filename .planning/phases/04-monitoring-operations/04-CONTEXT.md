# Phase 4: Monitoring & Operations - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

PyQt5 GUI 대시보드로 실시간 모니터링(보유종목, 주문현황, 수익률, 시스템 상태), 실시간 분봉차트(pyqtgraph + 기술지표 오버레이), 전략 설정 UI(생성/편집/저장/불러오기), 알림 시스템(GUI 토스트, 로그 파일, Discord 웹훅)을 구현한다. 백테스트(Phase 5)는 이후 페이즈에서 다룬다.

</domain>

<decisions>
## Implementation Decisions

### 대시보드 레이아웃
- 탭 기반 구조: 상단 탭으로 대시보드/차트/전략설정 전환. 각 탭이 독립적 화면.
- 데이터 업데이트: 실시간 푸시 — 체결/주문 이벤트 발생 시 pyqtSignal로 즉시 UI 반영. 기존 pyqtSignal/Slot 패턴 활용.
- 주문현황: 미체결 주문 + 당일 체결내역 함께 표시. 탭으로 구분.
- 하단 로그 패널: 대시보드 탭 하단에 시스템/매매 로그 실시간 스크롤 표시.
- 윈도우: 고정 최소 크기 설정 (리사이즈 가능, 최소값 보장)

### 실시간 차트
- pyqtgraph 기반 분봉 캔들스틱 차트
- 지표 배치: MA/볼린저/VWAP은 가격 차트 위 오버레이, RSI/MACD/OBV는 차트 아래 서브차트
- 지표 선택: 체크박스 토글로 ON/OFF — 즉시 반영
- 종목 전환: 차트 탭에 감시종목(watchlist) 목록 표시, 클릭으로 차트 전환
- 매매 마커: 매수(▲ 초록)/매도(▼ 빨간) 마커를 차트 위에 표시. 전략 동작 시각적 확인.

### 전략 설정 UI
- 폼 기반 편집: 전략 선택 후 입력필드로 파라미터 수정
- 새 전략 생성 가능: 전략명 입력 + 지표 드롭다운 선택 + 연산자 드롭다운 + 값 입력 + AND/OR 조합 버튼
- 저장 시 즉시 반영: config.json 쓰기 + StrategyManager 재로드. 장 중 핫스왑 가능.
- 감시종목(watchlist) GUI 관리: 종목코드 추가/제거 + 종목별 적용 전략 선택
- 전략 복사/삭제: 기존 전략 복사해서 변형 만들기 + 불필요 전략 삭제 (삭제 시 확인 대화상자)
- 저장 방식: config.json strategies 섹션에 통합 저장. 기존 Settings 패턴 재사용.

### 알림 시스템
- GUI 팝업: 토스트 알림 — 화면 우하단에 3-5초 표시 후 자동 사라짐. 작업 방해 없음.
- 알림 대상 이벤트: 매매 체결, 전략 신호 발생, 시스템 오류 — 3가지 레벨 모두 커버.
- 채널별 토글: GUI 팝업, 로그 파일, Discord 각각 독립적으로 ON/OFF. config.json에서 설정.
- Discord 웹훅: Embed 형식 — 매매코드/종목명/가격/수익률 등 구조화된 카드. 매수=초록, 매도=빨간 색상 구분.
- Discord 웹훅 URL: .env 환경변수에 저장 (Phase 1에서 민감정보는 .env 사용 결정)
- 전송 실패 처리: error 로그에 기록하고 넘어감. 매매 로직에 영향 없음. 알림은 부가기능.
- 로그 파일: 기존 loguru trade 싱크 확장. Phase 1에서 확립한 trade-YYYY-MM-DD.log 패턴 활용. 별도 싱크 추가 불필요.

### Claude's Discretion
- 보유종목 테이블 컬럼 구성 (데이트레이딩에 적합한 수준)
- 시스템 상태 표시 항목 (데이트레이딩 운영에 적합한 수준)
- 윈도우 최소 크기 정확한 값
- 차트 x축 범위 및 스크롤 동작
- 토스트 알림 정확한 표시 시간 및 애니메이션
- 전략 편집 폼의 세부 레이아웃 및 유효성 검사 방식

</decisions>

<specifics>
## Specific Ideas

- 탭 기반은 HTS보다 단순하지만 데이트레이딩 운영에 필요한 정보를 빠르게 전환 가능
- 매매 마커 표시는 전략 동작을 시각적으로 검증하는 데 필수 — 페이퍼 트레이딩 단계에서 특히 유용
- 새 전략 생성 기능으로 사용자가 자유롭게 조건 조합 가능 — 프리셋에 의존하지 않음
- Discord Embed 형식은 카카오톡 알림보다 구조적이고 색상 구분으로 한눈에 파악 가능
- 알림 실패가 매매 로직을 블로킹하면 안 됨 — 알림은 부가기능, 매매가 핵심

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyqtSignal/Slot 패턴`: 전 Phase에서 확립. KiwoomAPI → EventHandler → 비즈니스 로직 통신. GUI 위젯에 동일 패턴 적용.
- `Settings`: config.json 로딩/저장. strategy_config 프로퍼티 있음. GUI에서 수정 후 저장 시 재활용.
- `StrategyManager`: strategies 로드 + 인디케이터 관리. GUI에서 config 변경 → StrategyManager 재초기화로 핫스왑.
- `PositionTracker`: 보유종목 + P&L 추적. 대시보드 보유종목 테이블의 데이터 소스.
- `OrderManager`: 주문 상태 머신. 주문현황 테이블의 데이터 소스.
- `MarketHoursManager`: 장 상태(MarketState). 시스템 상태 표시용.
- `loguru multi-sink`: system/trade/error 날짜별 로테이션. 알림 이벤트도 기존 trade 싱크에 기록.
- `CandleAggregator`: 분봉 데이터 실시간 생성. 차트의 데이터 소스.
- `indicators.py`: 7개 인디케이터 클래스. 차트 오버레이 데이터 소스.
- `PaperTrader`: 페이퍼 매매 기록. 대시보드 체결내역 소스(페이퍼 모드).

### Established Patterns
- PyQt5 try/except fallback: macOS 개발 환경 호환. GUI 모듈도 동일 패턴 적용.
- Observer 패턴: RealDataManager subscribers. 차트/대시보드 위젯도 구독 가능.
- Config-driven: 모든 파라미터 config.json 관리. 알림 채널 토글, Discord 설정도 동일.
- .env 환경변수: 민감 정보 (Discord 웹훅 URL).

### Integration Points
- `main.py`: GUI 위젯 생성 + 데이터 소스 연결 와이어링 추가
- `config.json`: notification 섹션 (채널 토글, Discord 설정) 추가
- `.env`: DISCORD_WEBHOOK_URL 추가
- `StrategyManager`: GUI에서 config 변경 시 재로드 메서드 필요
- `CandleAggregator`: 차트 위젯에 분봉 데이터 콜백 등록
- `PositionTracker/OrderManager`: 대시보드 위젯에 데이터 제공

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-monitoring-operations*
*Context gathered: 2026-03-14*
