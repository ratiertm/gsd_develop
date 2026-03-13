---
status: complete
phase: 05-backtest-validation
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md]
started: 2026-03-14T05:00:00Z
updated: 2026-03-14T05:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Backtest Button Visible in Strategy Tab
expected: Navigate to the Strategy tab. A "Backtest" button should be visible next to the "Save Strategy" button in the strategy editor area.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요 (macOS에서 GUI 실행 불가)

### 2. Backtest Input Dialog Opens
expected: Click the "Backtest" button. A dialog titled "Backtest Settings" should appear with 4 input fields: Stock Code, Start Date, End Date, Initial Capital.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요

### 3. Backtest Input Validation
expected: Leave the stock code empty and click OK. A warning message "Stock code is required." should appear.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요

### 4. Backtest Progress Dialog
expected: Enter a valid stock code, date range, capital, then click OK. A "Backtest Running" progress dialog should appear.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요

### 5. BacktestDialog Summary Table
expected: After backtest completes, a "Backtest Results" dialog should appear with 11 metric rows.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요

### 6. Equity Curve Chart Tab
expected: In the BacktestDialog, click the "Equity Curve" tab. A line chart should display capital over time.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요

### 7. Drawdown Chart Tab
expected: Click the "Drawdown" tab. A chart should display percentage drawdown over time.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요

### 8. Price + Trades Chart Tab
expected: Click the "Price + Trades" tab. Candlestick chart with BUY/SELL trade markers.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요

### 9. Monthly Returns Chart Tab
expected: Click the "Monthly Returns" tab. Bar chart showing monthly aggregated returns.
result: skipped
reason: Windows + Kiwoom OpenAPI 환경에서 테스트 필요

### 10. Full Test Suite Passes
expected: Run `python -m pytest tests/ -x -q`. All tests pass (369+ passed, some skipped for PyQt5 CI compat).
result: pass

## Summary

total: 10
passed: 1
issues: 0
pending: 0
skipped: 9

## Gaps

[none yet]
