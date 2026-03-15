---
name: pdca
description: |
  PDCA 사이클 실행 — Phase 내부에서 Plan→Do→Check→Act 반복 개선.
  각 단계별 커맨드: /pdca plan, /pdca do, /pdca check, /pdca act, /pdca status
  인자 없이 호출하면 현재 상태를 파악하고 다음 액션을 제안한다.
argument-hint: "[plan|do|check|act|status] [phase-number] [feature-name]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
  - TodoWrite
  - AskUserQuestion
---

<objective>
GSD Phase 내부에서 PDCA(Plan-Do-Check-Act) 사이클을 실행한다.
각 Phase의 Gate Condition 달성을 목표로, 반복 개선 루프를 돈다.
</objective>

<context>
Arguments: $ARGUMENTS
Project root: $PROJECT_ROOT
PDCA state file: .planning/pdca/PDCA_STATE.json
</context>

<pdca_cycle>

## PDCA 사이클 개요

```
┌─────────────────────────────────────────────────────┐
│                   PDCA Cycle                        │
│                                                     │
│   Plan ────► Do ────► Check ────► Act ──┐           │
│     ▲                                   │           │
│     └──────── Improvement Loop ◄────────┘           │
│                                                     │
│   Gate Condition 달성 시 → 사이클 종료               │
└─────────────────────────────────────────────────────┘
```

각 Phase마다 하나의 PDCA 사이클을 실행한다.
Check에서 Gate Condition 미달 시 → Act에서 원인 분석 → 다시 Plan으로 돌아간다.
최대 5회 반복 후에도 미달이면 사용자에게 판단을 요청한다.

</pdca_cycle>

<phases>

### Plan (계획)

목표: Phase의 Gate Condition을 확인하고 작업 계획을 수립한다.

1. ROADMAP.md에서 해당 Phase의 Goal과 Gate Condition을 읽는다.
2. 현재 코드 상태를 파악한다 (구현된 것 vs 미구현).
3. Gate Condition 달성을 위한 구체적 작업 항목을 도출한다.
4. 작업 항목을 TodoWrite로 등록한다.
5. `.planning/pdca/phase-{N}/plan.md`에 계획을 기록한다.

출력 형식:
```
[Plan] → Design → Do → Check → Act

## Phase {N}: {Phase Name}

### Gate Conditions
- [ ] Gate 1: ...
- [ ] Gate 2: ...

### 작업 계획
1. ...
2. ...

### 예상 리스크
- ...
```

### Do (실행)

목표: Plan에서 수립한 작업을 실행한다.

1. `.planning/pdca/phase-{N}/plan.md`의 작업 항목을 순서대로 실행한다.
2. 코드를 작성/수정한다.
3. 각 작업 완료 시 TodoWrite로 완료 체크한다.
4. 변경 내용을 `.planning/pdca/phase-{N}/do.md`에 기록한다.

출력 형식:
```
Plan → [Do] → Check → Act

## 실행 현황

### 완료된 작업
- [x] ...

### 변경된 파일
- `file.py`: 변경 내용 요약

### 미완료 작업
- [ ] ...
```

### Check (검증)

목표: Gate Condition 달성 여부를 검증한다.

1. ROADMAP.md의 Gate Condition을 하나씩 검증한다.
2. 각 조건에 대해:
   - 코드 레벨: 구현 존재 여부, 로직 정확성 확인
   - 테스트 레벨: 관련 테스트 실행 (`pytest`)
   - 런타임 레벨: 장중 실행이 필요한 조건은 '장중 검증 필요'로 표시
3. Gate 통과율을 계산한다 (통과/전체).
4. 결과를 `.planning/pdca/phase-{N}/check.md`에 기록한다.

출력 형식:
```
Plan → Do → [Check] → Act

## Gate Condition 검증 결과

| # | Gate Condition | 상태 | 근거 |
|---|---------------|------|------|
| 1 | ... | ✅ Pass | 코드 확인: file.py:123 |
| 2 | ... | ❌ Fail | 미구현 |
| 3 | ... | ⏳ 장중 검증 필요 | SetRealReg 호출 확인 필요 |

### 통과율: {passed}/{total} ({percentage}%)

### 미달 항목 분석
- Gate 2: 원인 분석...
```

### Act (개선)

목표: Check 결과를 바탕으로 개선 조치를 수행한다.

1. Check에서 미달된 Gate Condition을 분석한다.
2. 각 미달 항목의 근본 원인을 파악한다.
3. 개선 방안을 도출한다:
   - 코드 수정으로 해결 가능 → 즉시 수정
   - 환경/런타임 문제 → 검증 절차 기록
   - 설계 변경 필요 → 다음 Plan 사이클에 반영
4. 결과를 `.planning/pdca/phase-{N}/act.md`에 기록한다.
5. Gate 전체 통과 시 → ROADMAP.md 상태 업데이트, 사이클 종료.
6. 미달 시 → 다음 사이클 Plan으로 회귀 (iteration +1).

출력 형식:
```
Plan → Do → Check → [Act]

## 개선 조치

### 즉시 수정
- [x] Gate 2: file.py 수정 — 내용

### 다음 사이클 이월
- Gate 3: 장중 검증 필요 — 검증 절차 문서화

### 사이클 결과
- Iteration: {N}/5
- Gate 통과율: {passed}/{total}
- 상태: {완료 | 다음 사이클 진행 | 사용자 판단 필요}
```

</phases>

<state_management>

## 상태 관리

PDCA 상태는 `.planning/pdca/PDCA_STATE.json`에 저장한다:

```json
{
  "active_phase": 9,
  "current_step": "check",
  "iteration": 1,
  "max_iterations": 5,
  "gate_results": {
    "1": "pass",
    "2": "fail",
    "3": "pending_runtime"
  },
  "history": [
    {
      "iteration": 1,
      "step": "check",
      "pass_rate": "2/4",
      "timestamp": "2026-03-14T10:00:00"
    }
  ]
}
```

</state_management>

<process>

## 실행 프로세스

### 인자가 없는 경우 (`/pdca`)
1. PDCA_STATE.json을 읽어 현재 상태를 파악한다.
2. 상태가 없으면 ROADMAP.md에서 다음 미완료 Phase를 찾는다.
3. 현재 단계와 다음 액션을 제안한다.

### `/pdca plan [phase-number]`
1. 해당 Phase의 PDCA Plan 단계를 실행한다.
2. 상태를 `current_step: "plan"`으로 업데이트한다.

### `/pdca do`
1. 현재 활성 Phase의 Plan을 기반으로 Do를 실행한다.
2. 상태를 `current_step: "do"`로 업데이트한다.

### `/pdca check`
1. Gate Condition 검증을 실행한다.
2. 상태를 `current_step: "check"`로 업데이트한다.
3. 결과를 gate_results에 저장한다.

### `/pdca act`
1. Check 결과 기반 개선 조치를 실행한다.
2. 전체 통과 시 Phase 완료 처리.
3. 미달 시 iteration +1, `current_step: "plan"`으로 회귀.

### `/pdca status`
1. 현재 PDCA 상태를 표시한다.
2. 전체 Phase 진행 현황과 현재 사이클 위치를 보여준다.

### `/pdca team [phase-number]`

병렬 에이전트 팀으로 Check 단계를 수행한다.
대규모 변경이나 E2E 검증이 필요한 Phase에서 사용한다.

**팀 구성:**

| 역할 | Agent Type | 담당 |
|------|-----------|------|
| Code Reviewer | Explore | 코드 품질, 누락된 연결, 미사용 코드 탐색 |
| Test Runner | general-purpose | pytest 실행, 테스트 커버리지 확인 |
| Pipeline Tracer | Explore | E2E 시그널 흐름 추적 (tick → order → position) |
| Risk Auditor | Explore | 리스크 관리 로직 검증, 엣지 케이스 탐색 |

**실행 흐름:**
1. 4개 에이전트를 병렬로 스폰한다.
2. 각 에이전트는 독립적으로 Gate Condition을 자신의 관점에서 검증한다.
3. 모든 에이전트 결과를 종합하여 Check 리포트를 생성한다.
4. 발견된 이슈를 우선순위별로 정리한다:
   - Critical: 기능 결함, 시그널 미연결, 주문 실패 가능성
   - Warning: 알림 누락, 로깅 부족, 에러 핸들링 미비
   - Info: 코드 스타일, 최적화 가능 지점

**출력 형식:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase {N}: {Phase Name} | Team Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Team 검증 결과

| Agent | 상태 | 발견 이슈 |
|-------|------|----------|
| Code Reviewer | Done | 2 warnings |
| Test Runner | Done | 13/13 pass |
| Pipeline Tracer | Done | 1 critical |
| Risk Auditor | Done | 0 issues |

## Gate Condition 종합

| # | Gate | Code | Test | Pipeline | Risk | 최종 |
|---|------|------|------|----------|------|------|
| 1 | ... | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | ... | ✅ | ⏳ | ❌ | ✅ | ❌ |

## 이슈 목록 (우선순위순)
1. [Critical] ...
2. [Warning] ...
```

</process>

<output_style>

## 출력 스타일

모든 응답 시작에 PDCA 상태 배지를 표시한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase {N}: {Phase Name} | Iteration {I}/5
[Plan] → Do → Check → Act     (현재 단계 강조)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Gate Condition 달성 시:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase {N}: {Phase Name} | COMPLETE
Gate: {passed}/{total} (100%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</output_style>
