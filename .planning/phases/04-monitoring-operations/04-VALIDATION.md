---
phase: 04
slug: monitoring-operations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | tests/conftest.py (existing shared fixtures) |
| **Quick run command** | `pytest tests/ -x -q --tb=short` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | GUI-01 | unit | `pytest tests/test_dashboard_tab.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | NOTI-01 | unit | `pytest tests/test_toast_widget.py -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | NOTI-02 | unit | `pytest tests/test_notifier.py -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | NOTI-03 | unit | `pytest tests/test_discord_sender.py -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | GUI-02 | unit | `pytest tests/test_chart_widgets.py -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | GUI-03 | unit | `pytest tests/test_strategy_tab.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard_tab.py` — stubs for GUI-01 (data binding, not actual rendering)
- [ ] `tests/test_chart_widgets.py` — stubs for GUI-02 (CandlestickItem data, indicator plot data)
- [ ] `tests/test_strategy_tab.py` — stubs for GUI-03 (strategy dict serialization, validation)
- [ ] `tests/test_toast_widget.py` — stubs for NOTI-01 (widget creation, timer behavior)
- [ ] `tests/test_notifier.py` — stubs for NOTI-02 (dispatch routing, log sink verification)
- [ ] `tests/test_discord_sender.py` — stubs for NOTI-03 (Discord embed payload, error handling)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GUI rendering correctness | GUI-01 | Requires visual inspection of widget layout | Launch app, verify dashboard tab shows positions/orders/P&L tables |
| Chart visual correctness | GUI-02 | Requires visual inspection of candle rendering | Launch app, load stock data, verify candle display and indicator overlays |
| Toast animation | NOTI-01 | Requires visual observation of fade/dismiss | Trigger a trade, verify toast appears and auto-dismisses |
| Discord message delivery | NOTI-03 | Requires live Discord webhook | Configure webhook, trigger trade, verify embed in Discord channel |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
