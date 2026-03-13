---
phase: 2
slug: order-execution-risk-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (already installed from Phase 1) |
| **Config file** | pytest.ini (existing) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | TRAD-03 | unit | `python -m pytest tests/test_order_manager.py::test_send_order -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | TRAD-03 | unit | `python -m pytest tests/test_order_manager.py::test_state_transitions -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | TRAD-03 | unit | `python -m pytest tests/test_order_manager.py::test_chejan_parsing -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | RISK-01 | unit | `python -m pytest tests/test_risk_manager.py::test_stop_loss -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | RISK-02 | unit | `python -m pytest tests/test_risk_manager.py::test_trailing_stop -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | RISK-03 | unit | `python -m pytest tests/test_risk_manager.py::test_split_order -x` | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 1 | RISK-04 | unit | `python -m pytest tests/test_risk_manager.py::test_position_limits -x` | ❌ W0 | ⬜ pending |
| 02-02-05 | 02 | 1 | RISK-04 | unit | `python -m pytest tests/test_risk_manager.py::test_daily_loss_limit -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | TRAD-04 | unit | `python -m pytest tests/test_market_hours.py::test_state_transitions -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | TRAD-04 | unit | `python -m pytest tests/test_market_hours.py::test_order_blocking -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_order_manager.py` — stubs for TRAD-03 (SendOrder wrapper, order state machine, ChejanData parsing)
- [ ] `tests/test_risk_manager.py` — stubs for RISK-01, RISK-02, RISK-03, RISK-04 (stop-loss, trailing stop, split orders, position limits, daily loss)
- [ ] `tests/test_market_hours.py` — stubs for TRAD-04 (market hours enforcement, state transitions, auction period blocking)
- [ ] `tests/test_position_tracker.py` — stubs for RISK-04 (position tracking, P&L calculation)
- [ ] `tests/conftest.py` — extend with mock_order_manager, mock_risk_config, mock_position_tracker fixtures

*Existing infrastructure: pytest.ini, tests/conftest.py with Phase 1 fixtures*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SendOrder actually submits to Kiwoom | TRAD-03 | Requires Windows + Kiwoom OCX + live/demo account | Login → submit test order via demo account → verify in Kiwoom HTS |
| ChejanData live event parsing | TRAD-03 | Requires live order execution | Submit order → monitor OnReceiveChejanData → verify FID extraction |
| Real-time stop-loss trigger | RISK-01 | Requires live price feed + position | Hold position → wait for price drop → verify auto-sell triggers |
| Market hours detection from FID 215 | TRAD-04 | Requires live market status feed | Run during market open/close → verify MarketState transitions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
