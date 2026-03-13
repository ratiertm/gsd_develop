# Requirements: KiwoomDayTrader

**Defined:** 2026-03-13
**Core Value:** 설정한 전략 조건에 따라 장중 자동으로 매수·매도가 실행되고, 정교한 리스크 관리로 손실을 통제하는 것

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### API/연결

- [x] **CONN-01**: 키움 OpenAPI+ OCX 로그인 및 세션 유지, 연결 끊김 시 자동 재접속
- [x] **CONN-02**: TR 요청 스로틀링 큐 (3.6초/건 제한 준수, QTimer 기반)
- [x] **CONN-03**: 실시간 시세 이벤트 수신 (호가, 체결, 거래량 — SetRealReg 기반)

### 매매 엔진

- [x] **TRAD-01**: 기술적 지표 계산 — 이동평균(SMA/EMA), RSI, MACD, 볼린저밴드
- [x] **TRAD-02**: 복합 매매 조건 엔진 — 기술지표 + 가격/거래량 조합 조건 평가
- [x] **TRAD-03**: 자동 주문 실행 — 시장가/지정가 매수·매도, 주문 상태 머신(접수→체결→완료)
- [x] **TRAD-04**: 매매 시간대 관리 — 장 시작/종료 시간, 동시호가 제외, 사용자 구간 설정

### 리스크 관리

- [x] **RISK-01**: 기본 손절/익절 — % 기반 손절매, 목표가 매도
- [x] **RISK-02**: 트레일링 스탑 — 최고가 대비 하락폭으로 동적 손절
- [x] **RISK-03**: 분할 매수/매도 — 여러 번에 나눠 진입/청산
- [x] **RISK-04**: 포지션 제한 — 종목별 비중 한도, 총 투자 한도, 일일 손실 한도

### GUI

- [x] **GUI-01**: 대시보드 메인 화면 — 보유종목, 주문현황, 수익률, 시스템 상태 표시
- [x] **GUI-02**: 실시간 분봉차트 — pyqtgraph 기반 + 기술지표 오버레이
- [x] **GUI-03**: 전략 설정 UI — 매매 조건/파라미터를 GUI에서 설정·저장·불러오기

### 알림/로깅

- [x] **NOTI-01**: GUI 팝업 알림 — 매매 체결, 조건 충족 신호 발생 시 팝업
- [x] **NOTI-02**: 로그 파일 기록 — 매매 내역, 오류, 시스템 상태를 파일로 저장
- [x] **NOTI-03**: Discord 웹훅 알림 — 매매 체결/주요 이벤트 Discord 전송

### 백테스트

- [ ] **BACK-01**: 전략 시뮬레이션 엔진 — 과거 데이터로 전략 실행, DataSource 추상화로 실전과 코드 공유
- [ ] **BACK-02**: 성과 분석 — 수익률, MDD, 승률, 손익비, 샤프비율 등 통계
- [ ] **BACK-03**: 결과 시각화 — 백테스트 결과 차트/그래프 (수익곡선, 드로다운 등)

## v2 Requirements

### 고급 전략

- **STRT-01**: AI/ML 기반 매매 신호 예측
- **STRT-02**: 멀티 전략 동시 실행 및 포트폴리오 관리
- **STRT-03**: 전략 최적화 (파라미터 그리드 서치/유전 알고리즘)

### 운영

- **OPER-01**: 모의투자 → 소액 실전 → 본격 운영 3단계 전환 모드
- **OPER-02**: 원격 모니터링 (웹 대시보드)
- **OPER-03**: 자동 시작/종료 스케줄링

### 확장

- **EXTD-01**: ETF/ETN 레버리지 트레이딩
- **EXTD-02**: 선물/옵션 파생상품 지원

## Out of Scope

| Feature | Reason |
|---------|--------|
| HFT(초고빈도매매) | 키움 API 속도 한계, 분단위 데이트레이딩에 집중 |
| 멀티 증권사 지원 | 키움증권 전용 시스템으로 복잡도 억제 |
| 모바일 앱 | 데스크톱 PyQt5 GUI 우선 |
| AI/ML 예측 | v1은 규칙 기반 전략, ML은 v2에서 검토 |
| 해외 주식 | 국내 KOSPI/KOSDAQ만 대상 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONN-01 | Phase 1 | Complete |
| CONN-02 | Phase 1 | Complete |
| CONN-03 | Phase 1 | Complete |
| TRAD-01 | Phase 3 | Complete |
| TRAD-02 | Phase 3 | Complete |
| TRAD-03 | Phase 2 | Complete |
| TRAD-04 | Phase 2 | Complete |
| RISK-01 | Phase 2 | Complete |
| RISK-02 | Phase 2 | Complete |
| RISK-03 | Phase 2 | Complete |
| RISK-04 | Phase 2 | Complete |
| GUI-01 | Phase 4 | Complete |
| GUI-02 | Phase 4 | Complete |
| GUI-03 | Phase 4 | Complete |
| NOTI-01 | Phase 4 | Complete |
| NOTI-02 | Phase 4 | Complete |
| NOTI-03 | Phase 4 | Complete |
| BACK-01 | Phase 5 | Pending |
| BACK-02 | Phase 5 | Pending |
| BACK-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 after roadmap creation*
