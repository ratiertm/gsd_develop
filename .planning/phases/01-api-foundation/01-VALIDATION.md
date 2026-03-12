---
phase: 1
slug: api-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CONN-01 | integration (manual, needs OCX) | Manual on Windows with Kiwoom installed | No — W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | CONN-01 | unit (mock API) | `python -m pytest tests/test_session_manager.py -x` | No — W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | CONN-01 | unit (mock API) | `python -m pytest tests/test_session_manager.py::test_restore_subscriptions -x` | No — W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | CONN-01 | unit (mock API) | `python -m pytest tests/test_session_manager.py::test_heartbeat -x` | No — W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | CONN-02 | unit | `python -m pytest tests/test_tr_queue.py::test_interval -x` | No — W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | CONN-02 | unit | `python -m pytest tests/test_tr_queue.py::test_fifo -x` | No — W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | CONN-02 | unit | `python -m pytest tests/test_tr_queue.py::test_empty_stop -x` | No — W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | CONN-03 | integration (needs OCX) | Manual on Windows | No — W0 | ⬜ pending |
| 01-03-02 | 03 | 1 | CONN-03 | unit | `python -m pytest tests/test_event_handler.py -x` | No — W0 | ⬜ pending |
| 01-03-03 | 03 | 1 | CONN-03 | unit | `python -m pytest tests/test_real_data.py -x` | No — W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pytest.ini` — pytest configuration with Python path
- [ ] `tests/conftest.py` — shared fixtures (mock KiwoomAPI, mock QAxWidget)
- [ ] `tests/test_session_manager.py` — stubs for CONN-01 (login, reconnect, heartbeat, subscription restore)
- [ ] `tests/test_tr_queue.py` — stubs for CONN-02 (interval, FIFO, empty stop)
- [ ] `tests/test_event_handler.py` — stubs for CONN-03 (event routing)
- [ ] `tests/test_real_data.py` — stubs for CONN-03 (data parsing)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Login flow completes with err_code=0 | CONN-01 | Requires Windows + Kiwoom OCX installed | 1. Run app on Windows 2. Check login callback returns err_code=0 3. Verify session maintained |
| SetRealReg registers and receives OnReceiveRealData | CONN-03 | Requires live OCX connection | 1. Login to Kiwoom 2. Register symbol via SetRealReg 3. Verify OnReceiveRealData fires with correct FID values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
