# PDCA Check: Phase 6~10 E2E Team Check

**Date**: 2026-03-15
**Iteration**: 1/5

## Team 검증 결과

| Agent | 발견 이슈 |
|-------|----------|
| Code Reviewer | 5 Critical, 5 Warning, 2 Info |
| Test Runner | 386/393 pass, 7 failed |
| Pipeline Tracer | 6/6 paths CONNECTED |
| Risk Auditor | 6 Critical, 8 Warning, 3 Info |

## Critical 이슈 및 수정 결과

| # | 이슈 | 수정 내용 | 테스트 |
|---|------|----------|--------|
| 1 | QTimer GC (market_state_timer, dashboard_timer) | main()스코프 변수 + main_window에 저장 | 17/17 pass |
| 2 | StrategyManager None 체크 없음 | _execute_signal()에 None 가드 추가 | 22/22 pass |
| 3 | session_restored 시 잔고 미동기화 | _on_session_restored → _select_account 연결 | 24/24 pass |
| 4 | OrderManager 레이스컨디션 | threading.RLock 추가, _handle_order_chejan lock | 17/17 pass |
| 5 | total_capital=0 ZeroDivisionError | RiskManager.__init__에 ValueError 방어 | 41/41 pass |
| 6 | KIWOOM_ACCOUNT_NO 빈 문자열 | _select_account + submit_order에 가드 추가 | 17/17 pass |

## Test 실패 수정

| 테스트 파일 | 실패 수 | 원인 | 수정 |
|------------|---------|------|------|
| test_order_manager.py | 4 | get_order/get_active_orders가 _pending_orders 미검색 | _pending_orders도 포함하도록 수정 |
| test_backtest_dialog.py | 3 | test_chart_widgets가 sys.modules에서 PyQt5 차단 후 미복원 | 모듈 레벨 import 후 즉시 복원 |

## 최종 테스트 결과

**393/393 passed** (64-bit Python 3.14)

## 변경된 파일

- `kiwoom_trader/main.py` — QTimer GC, session_restored, 계좌 검증
- `kiwoom_trader/core/strategy_manager.py` — None 체크
- `kiwoom_trader/core/order_manager.py` — RLock, 계좌 검증, pending_orders 검색
- `kiwoom_trader/core/risk_manager.py` — total_capital 검증
- `kiwoom_trader/core/position_tracker.py` — clear_all() 추가
- `tests/test_chart_widgets.py` — sys.modules 복원
