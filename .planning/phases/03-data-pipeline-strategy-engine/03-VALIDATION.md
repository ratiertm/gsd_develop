---
phase: 3
slug: data-pipeline-strategy-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | None (uses defaults) |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/ -x -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TRAD-01a | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_sma -x` | No -- Wave 0 | pending |
| 03-01-02 | 01 | 1 | TRAD-01b | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_ema -x` | No -- Wave 0 | pending |
| 03-01-03 | 01 | 1 | TRAD-01c | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_rsi -x` | No -- Wave 0 | pending |
| 03-01-04 | 01 | 1 | TRAD-01d | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_macd -x` | No -- Wave 0 | pending |
| 03-01-05 | 01 | 1 | TRAD-01e | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_bollinger -x` | No -- Wave 0 | pending |
| 03-01-06 | 01 | 1 | TRAD-01f | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_vwap -x` | No -- Wave 0 | pending |
| 03-01-07 | 01 | 1 | TRAD-01g | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_obv -x` | No -- Wave 0 | pending |
| 03-01-08 | 01 | 1 | TRAD-01h | unit | `.venv/bin/python -m pytest tests/test_indicators.py::test_warmup -x` | No -- Wave 0 | pending |
| 03-02-01 | 02 | 1 | TRAD-01i | unit | `.venv/bin/python -m pytest tests/test_candle_aggregator.py -x` | No -- Wave 0 | pending |
| 03-03-01 | 03 | 2 | TRAD-02a | unit | `.venv/bin/python -m pytest tests/test_condition_engine.py -x` | No -- Wave 0 | pending |
| 03-03-02 | 03 | 2 | TRAD-02b | unit | `.venv/bin/python -m pytest tests/test_strategy_manager.py::test_load_presets -x` | No -- Wave 0 | pending |
| 03-03-03 | 03 | 2 | TRAD-02c | unit | `.venv/bin/python -m pytest tests/test_strategy_manager.py::test_priority -x` | No -- Wave 0 | pending |
| 03-03-04 | 03 | 2 | TRAD-02d | unit | `.venv/bin/python -m pytest tests/test_strategy_manager.py::test_cooldown -x` | No -- Wave 0 | pending |
| 03-04-01 | 04 | 3 | TRAD-02e | unit | `.venv/bin/python -m pytest tests/test_paper_trader.py -x` | No -- Wave 0 | pending |
| 03-04-02 | 04 | 3 | TRAD-02f | integration | `.venv/bin/python -m pytest tests/test_strategy_integration.py -x` | No -- Wave 0 | pending |

---

## Wave 0 Requirements

- [ ] `tests/test_indicators.py` — stubs for TRAD-01a through TRAD-01h
- [ ] `tests/test_candle_aggregator.py` — stubs for TRAD-01i
- [ ] `tests/test_condition_engine.py` — stubs for TRAD-02a
- [ ] `tests/test_strategy_manager.py` — stubs for TRAD-02b, TRAD-02c, TRAD-02d
- [ ] `tests/test_paper_trader.py` — stubs for TRAD-02e
- [ ] `tests/test_strategy_integration.py` — stubs for TRAD-02f

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live tick → candle aggregation | TRAD-01i | Requires Windows + Kiwoom OCX real-time data | Subscribe to stock, verify candle OHLCV matches chart |
| Live signal → order execution | TRAD-02f | Requires Windows + Kiwoom OCX + live market | Run in paper mode, verify signal log and virtual P&L |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
