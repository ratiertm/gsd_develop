---
phase: 05
slug: backtest-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 05 — Validation Strategy

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
| 05-01-01 | 01 | 1 | BACK-01 | unit | `pytest tests/test_data_source.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | BACK-01 | unit | `pytest tests/test_backtest_engine.py -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | BACK-02 | unit | `pytest tests/test_performance.py -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | BACK-03 | unit | `pytest tests/test_backtest_dialog.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_data_source.py` — stubs for BACK-01 (DataSource ABC, KiwoomDataSource candle parsing)
- [ ] `tests/test_backtest_engine.py` — stubs for BACK-01 (replay loop, cost model, risk integration)
- [ ] `tests/test_performance.py` — stubs for BACK-02 (metric calculation accuracy)
- [ ] `tests/test_backtest_dialog.py` — stubs for BACK-03 (dialog creation, chart data binding)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Equity curve visual correctness | BACK-03 | Requires visual inspection of chart rendering | Run backtest, verify equity curve and drawdown chart display correctly |
| Trade markers on price chart | BACK-03 | Requires visual inspection of marker positioning | Run backtest, verify buy/sell markers appear at correct candle positions |
| QProgressBar animation | BACK-01 | Requires visual observation during data download | Start backtest with multi-day range, verify progress bar updates smoothly |
| Kiwoom TR data download | BACK-01 | Requires live Kiwoom API connection | Connect to Kiwoom, run backtest, verify opt10081/opt10080 data is received |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
