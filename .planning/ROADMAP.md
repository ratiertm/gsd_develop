# Roadmap: KiwoomDayTrader

## Milestone: v1.0 (Complete)

v1.0은 전체 시스템의 코드 기반을 완성했다. API 래퍼, 주문/리스크 엔진, 전략 엔진, GUI, 백테스트가 모의 환경에서 검증됨.
Phase 1~5 완료 (18/18 plans). 상세 내역은 git history 참조.

---

## Milestone: v2.0 — API 실연동 (Active)

### Overview

v1.0 코드를 실제 키움 OpenAPI+ 환경에 연결하는 마일스톤.
신규 코드보다 **설정/디버깅/검증** 비중이 크므로, GSD로 방향을 잡고 각 Stage 내부는 **PDCA 사이클**로 빠르게 반복한다.

**전략**: 단계별 게이트 — 이전 Stage 게이트를 통과해야 다음으로 진행.

### Requirements

- **INTG-01**: COM/OCX 실제 연결 및 로그인 (모의투자)
- **INTG-02**: 실시간 시세 수신 검증 (SetRealReg → 체결/호가 데이터)
- **INTG-03**: 모의투자 주문 실행 및 체결 확인
- **INTG-04**: 잔고/포지션 실시간 동기화
- **INTG-05**: E2E 통합 — 시세 수신 → 전략 신호 → 주문 → 체결 → 포지션 반영

## Phases

- [x] **Phase 6: 로그인/접속** — COM 연결, OpenAPI 로그인, 접속 상태 콜백 확인 (completed 2026-03-14)
- [ ] **Phase 7: 실시간 시세** — SetRealReg로 종목 등록, 체결/호가 데이터 수신 검증
- [ ] **Phase 8: 주문 실행** — 모의투자 시장가/지정가 주문, 체결 콜백(OnReceiveChejanData) 확인
- [ ] **Phase 9: 잔고/포지션 동기화** — 잔고 조회 TR, ChejanData 잔고 업데이트, PositionTracker 매핑
- [ ] **Phase 10: E2E 통합** — 전체 플로우 연결, GUI 연동, 모의투자 라이브 테스트

## Phase Details

### Phase 6: 로그인/접속
**Goal**: 키움 OpenAPI+ COM에 실제 연결하고 모의투자 로그인이 완료되는 것
**Depends on**: v1.0 완료
**Requirements**: INTG-01
**Gate Condition** (다음 Stage로 가려면):
  1. `CommConnect()` 호출 → 로그인 다이얼로그 표시 → 로그인 성공
  2. `OnEventConnect` 콜백에서 errCode=0 수신
  3. `GetLoginInfo("ACCNO")` 로 계좌번호 정상 조회
  4. `.env`에서 인증 정보 로드 동작 확인

**PDCA 사이클 예시**:
- P: CommConnect 호출 구현
- D: 실행, 로그인 다이얼로그 확인
- C: OnEventConnect 콜백 수신 여부 확인
- A: 실패 시 COM 등록/OCX 경로 등 환경 문제 수정

### Phase 7: 실시간 시세
**Goal**: 등록한 종목의 실시간 체결/호가 데이터가 앱으로 들어오는 것
**Depends on**: Phase 6
**Requirements**: INTG-02
**Gate Condition**:
  1. `SetRealReg`로 종목 등록 성공
  2. `OnReceiveRealData` 콜백으로 실시간 체결가/거래량 수신
  3. 수신 데이터가 `CandleAggregator`를 통해 Candle로 변환
  4. 10분 이상 안정적 수신 (연결 끊김 없음)

### Phase 8: 주문 실행
**Goal**: 모의투자에서 매수/매도 주문이 정상 체결되는 것
**Depends on**: Phase 7
**Requirements**: INTG-03
**Gate Condition**:
  1. `SendOrder` 시장가 매수 → 체결 확인
  2. `SendOrder` 지정가 매수 → 접수/체결/미체결 확인
  3. `OnReceiveChejanData` 콜백으로 주문 상태 변경 수신
  4. `OrderManager` 상태 머신이 실제 체결 데이터와 동기화

### Phase 9: 잔고/포지션 동기화
**Goal**: 실제 보유 잔고와 앱 내 PositionTracker가 일치하는 것
**Depends on**: Phase 8
**Requirements**: INTG-04
**Gate Condition**:
  1. 잔고 조회 TR (opw00018) 요청 → 보유 종목 목록 수신
  2. 체결 시 ChejanData(gubun=1) 잔고 변동 실시간 반영
  3. `PositionTracker`의 포지션과 실제 키움 잔고 일치
  4. GUI 대시보드에 실시간 잔고 표시

### Phase 10: E2E 통합
**Goal**: 시세 수신 → 전략 판단 → 주문 → 체결 → 잔고 반영까지 전체 파이프라인이 자동으로 동작
**Depends on**: Phase 9
**Requirements**: INTG-05
**Gate Condition**:
  1. 전략 조건 충족 시 자동 매수 주문 실행
  2. 리스크 관리(손절/익절/트레일링) 실제 동작
  3. GUI에서 전체 플로우 실시간 모니터링
  4. 30분 이상 모의투자 라이브 러닝 안정 확인

## Progress

**Execution Order:**
Phase 6 -> 7 -> 8 -> 9 -> 10 (순차, 게이트 통과 필수)

| Phase | Status | Gate Passed |
|-------|--------|-------------|
| 6. 로그인/접속 | Complete | 2026-03-14 |
| 7. 실시간 시세 | Pending | - |
| 8. 주문 실행 | Pending | - |
| 9. 잔고/포지션 동기화 | Pending | - |
| 10. E2E 통합 | Pending | - |
