# Feature Research

**Domain:** 주식 데이트레이딩 자동매매 시스템 (Korean Stock Day-Trading Automation)
**Researched:** 2026-03-13
**Confidence:** MEDIUM (training data only -- web search/fetch unavailable for live verification)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 키움 OpenAPI+ 로그인/접속 관리 | API 연동 없이 아무것도 안 됨. 자동 재접속, 세션 유지 포함 | MEDIUM | COM/OCX 기반이라 PyQt5 QAxWidget 필수. 모의투자/실계좌 전환 지원해야 함 |
| 실시간 시세 수신 | 자동매매의 전제 조건. 체결가, 호가, 거래량 실시간 수신 | MEDIUM | SetRealReg 이벤트 기반. 종목 등록 수 100개 제한 고려. OnReceiveRealData 핸들링 |
| 자동 주문 실행 (매수/매도) | 핵심 가치 자체. 시장가/지정가 주문, 정정/취소 | HIGH | SendOrder API. 주문번호 추적, 체결 확인(OnReceiveChejanData), 미체결 관리 필수 |
| 계좌 잔고/보유종목 조회 | 현재 포지션 파악 없이 매매 판단 불가 | LOW | OPW00018(계좌평가잔고) TR 호출. 3.6초 제한 준수 필요 |
| 기본 기술적 지표 (이동평균, RSI, MACD) | 매매 조건의 기본 구성 요소. 지표 없이 자동매매 무의미 | MEDIUM | 자체 계산 구현. ta-lib 또는 pandas-ta 활용. 실시간 데이터로 지표 갱신 |
| 매매 조건 엔진 | 지표 기반 진입/청산 조건 설정 및 평가 | HIGH | 복합 조건(AND/OR), 다중 지표 조합. 조건 평가 루프 성능 중요 |
| 손절/익절 설정 | 리스크 관리 기본. 없으면 큰 손실 위험 | MEDIUM | 고정 비율(%), 고정 금액 기반. 주문 즉시 실행 보장 필요 |
| 매매 시간대 관리 | 장 시작(09:00)/종료(15:30) 제어, 동시호가 회피 | LOW | 장 시작 전 준비, 장 마감 전 청산 로직. 공휴일/반일 거래일 처리 |
| 거래 로그 기록 | 모든 매매 기록 보존. 사후 분석/세금 신고 필수 | LOW | 주문/체결/잔고 변경 이벤트 로깅. CSV/DB 저장 |
| 기본 GUI 대시보드 | 시스템 상태 확인, 수동 개입 필요 시 조작 | HIGH | PyQt5 기반. 보유종목, 주문현황, 수익률 표시. 실시간 업데이트 |
| 긴급 정지 기능 (Kill Switch) | 시스템 오류/급락 시 즉시 매매 중단, 전 포지션 청산 | LOW | 버튼 하나로 자동매매 중단 + 미체결 취소 + 보유종목 시장가 매도 |
| 종목별/전체 투자 비중 제한 | 한 종목에 올인 방지. 리스크 관리 기본 | LOW | 종목당 최대 비중(%), 총 투자금 대비 한도 설정 |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 백테스트 엔진 | 실전 투입 전 전략 검증으로 신뢰도 향상. 대부분의 개인 자동매매 시스템은 백테스트 미지원 | HIGH | 과거 분봉 데이터 필요(키움 API opt10080 또는 외부). 슬리피지/수수료 반영. 성과 지표(승률, MDD, 샤프비율) |
| 트레일링 스탑 | 수익 극대화. 고정 손절보다 유연한 리스크 관리 | MEDIUM | 최고가 대비 하락 비율로 청산점 자동 조정. 실시간 가격 추적 필수 |
| 분할 매수/매도 | 평균 단가 관리, 리스크 분산. 전문 트레이더 기법 | MEDIUM | N분할 균등/비균등 매수. 단계별 조건(가격 하락 %, 시간 간격) |
| Discord/Telegram 알림 | 자리 비울 때도 매매 상황 즉시 파악 | LOW | 웹훅 기반. 매수/매도 체결, 손익, 시스템 오류 알림 |
| 전략 파라미터 프리셋 관리 | 여러 전략 저장/전환으로 시장 상황별 대응 | LOW | JSON/YAML 기반 설정 파일. 전략 비교 용이 |
| 실시간 차트 표시 | 매매 시점 시각적 확인, 지표 오버레이 | HIGH | PyQt5 + pyqtgraph 또는 matplotlib. 캔들차트, 지표 선, 매매 마커 |
| 일별/월별 성과 리포트 | 전략 성과 추적, 개선점 발견 | MEDIUM | 일별 수익률, 누적 수익률, 거래 횟수, 승률 자동 집계 |
| 볼린저밴드/스토캐스틱 등 확장 지표 | 다양한 전략 구사 가능 | LOW | pandas-ta로 대부분 커버. 사용자 정의 지표 프레임워크까지 가면 MEDIUM |
| 거래량 급증 감지 | 데이트레이딩 핵심 시그널. 거래량 이상 급등 종목 포착 | MEDIUM | 평균 거래량 대비 N배 이상 감지. 실시간 모니터링 종목 자동 추가 |
| 조건검색식 실시간 수신 | 키움 HTS 조건검색식을 API로 실시간 수신하여 종목 자동 편입 | MEDIUM | SendCondition/OnReceiveRealCondition API. 키움 HTS에서 조건식 먼저 작성 필요 |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| 초고빈도매매(HFT) 지원 | "빠를수록 좋다" 인식 | 키움 API는 초당 5회 주문 제한, TR 3.6초 제한. HFT 물리적으로 불가. 무리하면 계정 정지 | 분단위 데이트레이딩에 집중. 1분봉/틱 기반 전략 |
| AI/ML 기반 가격 예측 | "AI가 수익 낸다" 기대 | 개인 수준 데이터/인프라로 유의미한 예측 불가. 과적합 위험 극히 높음. 검증 없이 실전 투입 시 큰 손실 | 검증된 기술적 지표 조합. 통계적으로 유의미한 룰 기반 전략 |
| 다중 증권사 동시 지원 | 확장성/유연성 | 각 증권사 API 완전히 다름(키움 COM, 이베스트 DLL, 대신 COM). 추상화 레이어 유지보수 비용 막대 | 키움 전용으로 깊이 있게 구현. 추후 필요 시 어댑터 패턴 |
| 모바일 앱 | 외출 중 모니터링 | 키움 API가 Windows COM 전용이라 서버 아키텍처 필요. 복잡도 급증 | Discord/Telegram 알림으로 모바일 모니터링 대체 |
| 자동 종목 발굴 (스크리닝) | "좋은 종목 알아서 찾아줘" | 스크리닝 로직 자체가 하나의 복잡한 시스템. 매매 엔진과 혼합 시 복잡도 폭발 | 키움 조건검색식 연동으로 종목 필터링 위임. 매매 엔진은 주어진 종목 리스트에 집중 |
| 실시간 뉴스/공시 기반 매매 | 뉴스 선반영 기대 | 자연어 처리 복잡도, 뉴스 지연(이미 반영됨), 오탐 위험 | 가격/거래량 기반 이상 감지로 간접 포착 |
| 무한 종목 동시 모니터링 | "전 종목 감시" | 키움 API 실시간 등록 종목 수 제한(약 100개). 과도한 등록 시 데이터 지연/누락 | 조건검색식으로 후보 축소 후 20-50개 집중 모니터링 |
| 파생상품(선물/옵션) | 레버리지 수익 기대 | 완전히 다른 API 체계, 리스크 관리 복잡도 급증, 증거금 관리 필요 | KOSPI/KOSDAQ 보통주 집중. 파생은 별도 프로젝트 |

## Feature Dependencies

```
[키움 OpenAPI+ 로그인/접속]
    |
    +--requires--> [계좌 잔고 조회]
    |                   |
    |                   +--requires--> [종목별 투자 비중 제한]
    |
    +--requires--> [실시간 시세 수신]
    |                   |
    |                   +--requires--> [기술적 지표 계산]
    |                   |                   |
    |                   |                   +--requires--> [매매 조건 엔진]
    |                   |                                       |
    |                   |                                       +--requires--> [자동 주문 실행]
    |                   |                                       |                   |
    |                   |                                       |                   +--enhances--> [거래 로그 기록]
    |                   |                                       |                   |
    |                   |                                       |                   +--enhances--> [알림 시스템]
    |                   |                                       |
    |                   |                                       +--requires--> [손절/익절]
    |                   |                                       |
    |                   |                                       +--enhances--> [트레일링 스탑]
    |                   |                                       |
    |                   |                                       +--enhances--> [분할 매수/매도]
    |                   |
    |                   +--requires--> [실시간 차트 표시]
    |                   |
    |                   +--requires--> [거래량 급증 감지]
    |
    +--requires--> [자동 주문 실행]
    |
    +--requires--> [매매 시간대 관리]

[기술적 지표 계산] + [과거 데이터]
    +--requires--> [백테스트 엔진]
                        +--enhances--> [성과 리포트]

[키움 HTS 조건검색식]
    +--requires--> [조건검색식 실시간 수신]
                        +--enhances--> [매매 조건 엔진]

[GUI 대시보드]
    +--requires--> [키움 OpenAPI+ 로그인/접속]
    +--requires--> [실시간 시세 수신]
    +--enhances--> [실시간 차트 표시]
    +--enhances--> [긴급 정지 기능]
```

### Dependency Notes

- **매매 조건 엔진 requires 기술적 지표 계산:** 지표가 계산되어야 매매 조건 평가 가능
- **자동 주문 실행 requires 매매 조건 엔진:** 조건 충족 시 주문 트리거
- **백테스트 엔진 requires 기술적 지표 계산 + 과거 데이터:** 동일한 지표 계산 로직을 과거 데이터에 적용
- **트레일링 스탑 enhances 매매 조건 엔진:** 청산 조건의 고급 버전
- **조건검색식 수신 enhances 매매 조건 엔진:** 종목 선정을 키움 HTS에 위임하여 매매 대상 자동 갱신
- **GUI 대시보드는 독립 구현 가능하나**, 실시간 데이터/주문 모듈과 연동 필요

## MVP Definition

### Launch With (v1)

Minimum viable product -- 자동매매 핵심 루프가 동작하는 최소 구성.

- [ ] 키움 OpenAPI+ 로그인/접속 관리 -- 모든 기능의 전제 조건
- [ ] 실시간 시세 수신 (체결가, 거래량) -- 매매 판단 데이터
- [ ] 계좌 잔고/보유종목 조회 -- 현재 상태 파악
- [ ] 기본 기술적 지표 (이동평균, RSI) -- 매매 신호 생성
- [ ] 매매 조건 엔진 (기본 AND 조건) -- 진입/청산 조건 평가
- [ ] 자동 주문 실행 (시장가/지정가) -- 매수/매도 실행
- [ ] 고정 손절/익절 -- 최소한의 리스크 관리
- [ ] 종목별 투자 비중 제한 -- 과도 집중 방지
- [ ] 매매 시간대 관리 -- 장 시간 외 주문 방지
- [ ] 거래 로그 기록 (파일) -- 매매 이력 보존
- [ ] 긴급 정지 기능 -- 안전장치 필수
- [ ] 기본 콘솔/간이 GUI -- 상태 확인용 (풀 대시보드 아님)

### Add After Validation (v1.x)

핵심 매매 루프가 안정적으로 동작한 후 추가.

- [ ] GUI 대시보드 (보유종목, 주문현황, 수익률) -- 편의성 대폭 향상
- [ ] 트레일링 스탑 -- 수익 극대화
- [ ] 분할 매수/매도 -- 평균단가 관리
- [ ] MACD, 볼린저밴드 등 확장 지표 -- 전략 다양화
- [ ] Discord/Telegram 알림 -- 원격 모니터링
- [ ] 전략 프리셋 관리 (저장/불러오기) -- 운영 편의
- [ ] 조건검색식 실시간 수신 -- 종목 자동 편입
- [ ] 거래량 급증 감지 -- 모멘텀 트레이딩

### Future Consideration (v2+)

MVP 및 v1.x 안정화 후 검토.

- [ ] 백테스트 엔진 -- 구현 복잡도 높음, 별도 데이터 파이프라인 필요
- [ ] 실시간 차트 + 지표 오버레이 -- GUI 복잡도 높음
- [ ] 일별/월별 성과 리포트 -- 충분한 거래 데이터 축적 후 의미
- [ ] 복합 조건 엔진 (AND/OR/NOT 중첩) -- v1 단순 조건으로 충분히 시작 가능
- [ ] 사용자 정의 지표 프레임워크 -- 고급 사용자 대상

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 키움 API 로그인/접속 | HIGH | MEDIUM | P1 |
| 실시간 시세 수신 | HIGH | MEDIUM | P1 |
| 계좌 잔고 조회 | HIGH | LOW | P1 |
| 기술적 지표 계산 (기본) | HIGH | MEDIUM | P1 |
| 매매 조건 엔진 (기본) | HIGH | HIGH | P1 |
| 자동 주문 실행 | HIGH | HIGH | P1 |
| 손절/익절 | HIGH | MEDIUM | P1 |
| 투자 비중 제한 | HIGH | LOW | P1 |
| 매매 시간대 관리 | HIGH | LOW | P1 |
| 거래 로그 기록 | HIGH | LOW | P1 |
| 긴급 정지 기능 | HIGH | LOW | P1 |
| GUI 대시보드 | MEDIUM | HIGH | P2 |
| 트레일링 스탑 | MEDIUM | MEDIUM | P2 |
| 분할 매수/매도 | MEDIUM | MEDIUM | P2 |
| Discord/Telegram 알림 | MEDIUM | LOW | P2 |
| 전략 프리셋 관리 | MEDIUM | LOW | P2 |
| 조건검색식 수신 | MEDIUM | MEDIUM | P2 |
| 거래량 급증 감지 | MEDIUM | MEDIUM | P2 |
| 확장 기술적 지표 | LOW | LOW | P2 |
| 백테스트 엔진 | MEDIUM | HIGH | P3 |
| 실시간 차트 | LOW | HIGH | P3 |
| 성과 리포트 | LOW | MEDIUM | P3 |
| 사용자 정의 지표 | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch -- 자동매매 핵심 루프 동작에 필수
- P2: Should have, add when possible -- 안정성 확보 후 운영 품질 향상
- P3: Nice to have, future consideration -- 시스템 성숙 후 고도화

## Competitor Feature Analysis

| Feature | 대신증권 CybosPlus | 이베스트 xingAPI | 키움 OpenAPI+ (본 프로젝트) |
|---------|-------------------|-----------------|---------------------------|
| API 방식 | COM 기반 | DLL/COM 기반 | COM(OCX) 기반 |
| Python 생태계 | 보통 (공식 미지원) | 보통 | 풍부 (pykiwoom 등 다수) |
| 실시간 데이터 | 지원 | 지원 | 지원 (SetRealReg) |
| 조건검색식 | 미지원 또는 제한적 | 지원 | 지원 (SendCondition) |
| 주문 제한 | 유사 | 유사 | 초당 5회, TR 3.6초 |
| 모의투자 | 지원 | 지원 | 지원 |
| 커뮤니티/자료 | 적음 | 보통 | 가장 풍부 (블로그, 유튜브, 서적 다수) |
| 수수료 | 유사 | 유사 | 업계 최저 수준 |
| 동시 종목 수 | 제한 있음 | 제한 있음 | 약 100개 (실시간 등록) |

**분석:** 키움증권은 한국 개인투자자 자동매매 생태계에서 사실상 표준. Python 래퍼 라이브러리, 커뮤니티 자료, 관련 서적이 압도적으로 많아 개발 생산성 측면에서 최적. 본 프로젝트가 키움 전용으로 가는 것은 올바른 판단.

## Key Insights

### 데이트레이딩 자동매매에서 가장 중요한 것은 "안전장치"

개인 자동매매 시스템에서 수익 극대화보다 손실 통제가 더 중요하다. 많은 개인 프로젝트가 매매 로직에만 집중하고 리스크 관리를 소홀히 하여 실전에서 큰 손실을 본다. 긴급 정지, 손절, 비중 제한은 P1 중에서도 최우선.

### 키움 API 제한이 아키텍처를 결정한다

TR 3.6초 제한, 실시간 등록 종목 수 제한, 초당 주문 수 제한이 시스템 설계 전체를 지배한다. 이 제한을 무시한 설계는 반드시 실패한다. 요청 큐잉, 우선순위 관리, 레이트 리미팅이 인프라 수준에서 필요.

### 모의투자 먼저, 실전은 나중에

키움 OpenAPI+는 모의투자 서버를 제공한다. 모든 기능을 모의투자에서 충분히 검증한 후 실전 전환하는 워크플로우를 시스템에 내장해야 한다. 모의투자/실전 전환이 설정 하나로 가능해야 함.

## Sources

- 키움증권 OpenAPI+ 공식 개발 가이드 (training data 기반, MEDIUM confidence)
- pykiwoom 라이브러리 문서 및 사용 패턴 (training data 기반, MEDIUM confidence)
- 한국 주식 자동매매 커뮤니티 일반 지식 (training data 기반, LOW-MEDIUM confidence)
- 대신증권 CybosPlus, 이베스트 xingAPI 비교는 training data 기반 (LOW confidence -- 최신 변경사항 미반영 가능)

**Note:** WebSearch 및 WebFetch가 비활성화되어 모든 내용이 training data(2025년 5월까지)에 기반합니다. 키움 API 최신 변경사항, 신규 라이브러리 등은 별도 검증이 필요합니다.

---
*Feature research for: 키움증권 OpenAPI+ 주식 데이트레이딩 자동매매 시스템*
*Researched: 2026-03-13*
