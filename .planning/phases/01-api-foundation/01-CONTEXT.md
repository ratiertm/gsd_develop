# Phase 1: API Foundation - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

키움 OpenAPI+ OCX에 연결하여 로그인, 세션 유지, 자동 재접속을 처리하고, TR 요청 스로틀링 큐를 구현하며, 실시간 시세 데이터(호가, 체결, 거래량)를 이벤트 기반으로 수신하는 기반 인프라를 구축한다. 주문 실행, 전략 엔진, GUI는 이후 페이즈에서 다룬다.

</domain>

<decisions>
## Implementation Decisions

### 프로젝트 구조
- 기능별 모듈 분리: api/, strategy/, risk/, gui/, backtest/ 등 기능 도메인별 폴더
- 설정 파일 형식: JSON (config.json)
- 로그 관리: 용도별 + 날짜 로테이션 복합 방식 (trade-2026-03-13.log, system-2026-03-13.log, error-2026-03-13.log)
- 민감 정보: .env 환경변수로 관리, .gitignore에 추가

### Claude's Discretion
- API 래핑 방식 — pykiwoom 래퍼 활용 vs 직접 QAxWidget OCX 컨트롤 (리서치에서 프로덕션용 직접 래핑 추천, 최종 판단은 구현 시)
- 세션 관리 및 재접속 전략 상세 (재시도 횟수, 간격, 장중/장외 동작 차이)
- 실시간 데이터 수신 시 버퍼링/큐잉 방식
- TR 스로틀링 큐 구현 상세 (QTimer 간격, 큐 우선순위)
- 이벤트 라우터 설계 (COM 이벤트 → 내부 시그널 변환 방식)
- 스레딩 모델 상세 (메인 스레드 COM 호출 vs QThread 워커 분리)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. 리서치 결과에서 다음 핵심 제약을 반영:
- 32-bit Python 3.10.x 필수 (키움 COM/OCX 32비트 전용)
- PyQt5 5.15.x 필수 (PyQt6은 QAxWidget 미지원)
- COM STA 모델 — 모든 키움 API 호출은 OCX를 생성한 메인 스레드에서 실행
- TR 요청 3.6초 제한 준수 필수

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- 없음 (그린필드 프로젝트)

### Established Patterns
- 없음 — Phase 1에서 기본 패턴을 확립

### Integration Points
- 키움 OpenAPI+ OCX (외부 COM 컴포넌트)
- PyQt5 이벤트 루프 (QApplication)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-api-foundation*
*Context gathered: 2026-03-13*
