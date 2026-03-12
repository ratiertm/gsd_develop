# KiwoomDayTrader

## What This Is

키움증권 OpenAPI+를 활용한 Python 기반 주식 데이트레이딩 자동매매 시스템. 기술적 지표와 가격/거래량 복합 조건으로 KOSPI/KOSDAQ 종목을 자동 매수·매도하며, GUI 대시보드로 실시간 모니터링하고 백테스트로 전략을 검증할 수 있다.

## Core Value

설정한 전략 조건에 따라 장중 자동으로 매수·매도가 실행되고, 정교한 리스크 관리로 손실을 통제하는 것.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 키움 OpenAPI+ 연동 및 로그인/접속 관리
- [ ] 실시간 시세 데이터 수신 (호가, 체결, 거래량)
- [ ] 기술적 지표 계산 (이동평균, RSI, MACD, 볼린저밴드 등)
- [ ] 복합 매매 조건 엔진 (기술지표 + 가격/거래량 조합)
- [ ] 자동 주문 실행 (시장가/지정가 매수·매도)
- [ ] 리스크 관리 — 트레일링 스탑, 분할 매수/매도, 종목별 비중 제한
- [ ] 매매 시간대 설정 (장 시작/종료 시간, 특정 구간 제한)
- [ ] GUI 대시보드 — 실시간 차트, 보유종목, 주문현황, 수익률
- [ ] 백테스트 엔진 — 과거 데이터로 전략 시뮬레이션 및 성과 분석
- [ ] 알림 시스템 — GUI 팝업, 로그 파일 기록, Discord 웹훅
- [ ] 전략 설정 관리 — 전략 파라미터 저장/불러오기

### Out of Scope

- 선물/옵션 파생상품 — 현물 주식 데이트레이딩에 집중
- ETF/ETN 레버리지 트레이딩 — v1에서는 KOSPI/KOSDAQ 보통주 대상
- 모바일 앱 — 데스크톱 GUI 우선
- HFT(초고빈도매매) — 키움 API 속도 한계, 분단위 데이트레이딩 수준
- 멀티 증권사 지원 — 키움증권 전용

## Context

- 키움증권 OpenAPI+는 Windows 전용 COM 기반 API로, Python에서는 PyQt5를 통해 연동
- pykiwoom 등 래퍼 라이브러리 활용 가능하나, 직접 OCX 컨트롤 방식도 고려
- 키움 API는 초당 요청 제한이 있어 (TR 3.6초 제한 등) 이를 고려한 설계 필요
- 실시간 데이터는 SetRealReg를 통한 이벤트 기반 수신
- 장중 09:00~15:30 운영, 동시호가 시간 고려 필요
- 백테스트용 과거 데이터는 키움 API 일봉/분봉 조회 또는 외부 데이터 소스 활용

## Constraints

- **플랫폼**: Windows 전용 — 키움 OpenAPI+ COM 제한
- **언어**: Python + PyQt5 — 키움 API 연동 및 GUI
- **API 제한**: 키움 TR 요청 제한 (3.6초/건) 준수 필요
- **보안**: 실계좌 비밀번호, API 키 등 민감 정보 안전 관리

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + PyQt5 | 키움 API 연동 생태계가 가장 풍부, GUI도 PyQt5로 통합 | — Pending |
| KOSPI/KOSDAQ 보통주만 | 파생상품 복잡도 배제, 핵심 기능에 집중 | — Pending |
| 완전 자동매매 | 수동 개입 없이 전략 기반 자동 실행이 핵심 가치 | — Pending |

---
*Last updated: 2026-03-13 after initialization*
