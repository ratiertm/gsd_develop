# Phase 5: Backtest & Validation - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

과거 OHLCV 데이터로 전략을 시뮬레이션하여 성과 지표(수익률, MDD, 승률, 손익비, 샤프비율 등)를 산출하고 시각화한다. DataSource 추상화로 실전 StrategyManager/RiskManager 코드를 그대로 재사용한다. 실시간 매매(Phase 1-3), GUI 대시보드(Phase 4)는 이미 완료.

</domain>

<decisions>
## Implementation Decisions

### 데이터 소스 & 리플레이
- 키움 API opt10081(일봉)/opt10080(분봉) TR 조회로 과거 데이터 다운로드. 기존 TRRequestQueue 재사용 (3.6초 제한 준수)
- DataSource ABC (추상 클래스) 정의: get_candles(code, start_date, end_date) → list[Candle]. KiwoomDataSource 구현. 향후 CSVDataSource 등 확장 가능
- 봉별 리플레이: 과거 봉 데이터를 시간순으로 하나씩 인디케이터/전략에 피딩. CandleAggregator 없이 직접 Candle 객체를 StrategyManager에 전달
- 백테스트 구간: 사용자가 시작일 ~ 종료일 직접 지정

### 비용 모델링 & 실전 반영도
- 수수료 + 거래세 반영: 매수 수수료 %, 매도 수수료 %, 거래세 0.18%(매도시). 모두 config.json에서 설정 가능
- 고정 슬리페이지: 체결가 = close ± 고정 bp. config.json에서 설정 가능 (기본값은 Claude 재량)
- 실전 RiskManager 룰 그대로 적용: 손절/익절/트레일링스톱/포지션 제한/일일 손실 한도 동일 로직
- 초기 자본금: 사용자 입력 (기본값 1천만원)

### 성과 지표 & 분석
- 핵심 5개: 총 수익률, MDD(최대낙폭), 승률, Profit Factor(손익비), Sharpe Ratio
- 추가 지표: 평균 손익, 최대 연속 손실, 총 거래 횟수, 평균 보유 기간 등 부가 통계
- 결과 표시: 백테스트 완료 후 QDialog로 성과 요약 테이블 + 차트 표시
- 진행 상황: QProgressBar로 다운로드/시뮬레이션 진행률 + 예상 잔여시간 표시

### 결과 시각화
- pyqtgraph 사용 (Phase 4 ChartTab과 동일 라이브러리, CandlestickItem 재사용 가능)
- 핵심 3개: Equity curve(자본 변화), Drawdown chart(드로다운 %), 가격차트+매매마커
- 추가 차트: 월별 수익 막대차트, 거래 분포 등
- 별도 BacktestDialog (QDialog): 성과 요약 테이블 + 차트들을 하나의 창에 배치
- 백테스트 실행: StrategyTab에 "백테스트 실행" 버튼 추가. 클릭 시 기간/종목/자본금 입력 팝업 → 실행 → BacktestDialog 표시

### Claude's Discretion
- BacktestEngine 클래스 설계 및 리플레이 루프 구현
- KiwoomDataSource opt10080/opt10081 파싱 세부사항
- PerformanceCalculator 내부 지표 계산 알고리즘
- BacktestDialog 레이아웃 (차트 배치, 테이블 컬럼)
- 슬리페이지 기본값 (합리적 수준)
- 추가 지표/차트의 정확한 항목 선택
- QThread 기반 백테스트 실행 (UI 블로킹 방지)

</decisions>

<specifics>
## Specific Ideas

- 데이트레이딩 전략 검증이 핵심 — 실계좌 투입 전 반드시 백테스트로 확인
- 수수료/슬리페이지 없으면 낙관적 결과 → 비용 반영이 현실적 백테스트의 핵심
- RiskManager 동일 적용으로 "백테스트에서 잘 됐는데 실전에서 안 되는" 문제 최소화
- 키움 API TR 제한(3.6초)으로 대량 데이터 다운로드 시 시간 소요 → 진행률 표시 필수
- StrategyTab에서 전략 편집 → 바로 백테스트 실행 → 결과 확인 워크플로우

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `StrategyManager`: 전략 로드 + 인디케이터 관리 + 조건 평가. 백테스트에서 동일 코드로 신호 생성
- `ConditionEngine`: AND/OR 복합 규칙 평가. 백테스트에서 그대로 재사용
- `PaperTrader`: 가상 매매 실행 + CSV 기록. 백테스트 실행 엔진의 기반이 될 수 있음 (확장 또는 참조)
- `RiskManager`: 6-check pre-trade validation. 백테스트에서 동일 리스크 룰 적용
- `PositionTracker`: 보유종목 + P&L 추적. 백테스트 중 포지션 관리에 재사용
- `indicators.py`: 7개 인디케이터 (SMA, EMA, RSI, MACD, Bollinger, VWAP, OBV). 백테스트에서 동일 계산
- `Candle` dataclass: OHLCV 데이터 구조. DataSource 출력 및 인디케이터 입력 형식
- `Signal`, `TradeRecord` dataclass: 매매 신호 및 거래 기록 구조
- `CandlestickItem`: pyqtgraph 캔들스틱 위젯. BacktestDialog 가격차트에 재사용
- `TRRequestQueue`: TR 스로틀링 큐. KiwoomDataSource 데이터 다운로드에 재사용
- `Settings`: config.json 관리. 백테스트 비용 설정(수수료/슬리페이지) 추가

### Established Patterns
- PyQt5 try/except fallback: macOS 호환. 백테스트 모듈도 동일 패턴
- Config-driven: 모든 파라미터 config.json 관리. 비용 모델 설정도 동일
- Observer 패턴: callback 등록. 백테스트 진행 상황 알림에 활용 가능
- TDD: RED→GREEN 패턴. Phase 2-3에서 확립

### Integration Points
- `StrategyTab`: "백테스트 실행" 버튼 추가 → BacktestDialog 연결
- `config.json`: backtest 섹션 (수수료, 슬리페이지, 기본 자본금) 추가
- `KiwoomAPI`: opt10080/opt10081 TR 요청 메서드 추가 필요
- `main.py`: BacktestDialog 와이어링 (StrategyTab 버튼 → 백테스트 엔진 → 결과 다이얼로그)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-backtest-validation*
*Context gathered: 2026-03-14*
