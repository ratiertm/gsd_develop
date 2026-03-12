# Roadmap: KiwoomDayTrader

## Overview

KiwoomDayTrader is built bottom-up from its hardest constraint: the Kiwoom OpenAPI+ COM/OCX layer that dictates threading, event handling, and rate limits. Phase 1 establishes a stable, rate-limit-compliant API connection. Phase 2 builds order execution and risk management together (risk guards must exist before any automated order fires). Phase 3 adds indicator calculation and the strategy condition engine, completing the automated trading loop. Phase 4 delivers the full GUI dashboard and notification system for monitoring live operations. Phase 5 adds the backtest engine to validate strategies against historical data.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: API Foundation** - Kiwoom OCX connectivity, event routing, TR throttling, real-time data reception (completed 2026-03-12)
- [ ] **Phase 2: Order Execution & Risk Management** - Automated order lifecycle, stop-loss/trailing stop, position limits, market-hours controls
- [ ] **Phase 3: Data Pipeline & Strategy Engine** - Technical indicator calculation, composite condition engine for automated entry/exit
- [ ] **Phase 4: Monitoring & Operations** - PyQt5 GUI dashboard, real-time charts, strategy config UI, notifications
- [ ] **Phase 5: Backtest & Validation** - Historical data replay, strategy simulation, performance analytics and visualization

## Phase Details

### Phase 1: API Foundation
**Goal**: A stable, rate-limit-compliant Kiwoom API connection that can log in, receive real-time market data, and survive disconnections
**Depends on**: Nothing (first phase)
**Requirements**: CONN-01, CONN-02, CONN-03
**Success Criteria** (what must be TRUE):
  1. System logs into Kiwoom OpenAPI+ and maintains session; if connection drops, it reconnects automatically without user intervention
  2. TR requests are queued and dispatched at compliant intervals (3.6s+) -- rapid-fire requests never reach the server
  3. Real-time price, volume, and orderbook data streams into the application for registered symbols via SetRealReg events
  4. Project structure, logging infrastructure, and configuration management are operational
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffolding, config, logging, constants, and test infrastructure
- [ ] 01-02-PLAN.md — KiwoomAPI wrapper, event handler registry, and session manager
- [ ] 01-03-PLAN.md — TR throttle queue, real-time data manager, and main.py wiring

### Phase 2: Order Execution & Risk Management
**Goal**: Orders execute reliably with full lifecycle tracking, and risk guards prevent uncontrolled losses before any strategy runs
**Depends on**: Phase 1
**Requirements**: TRAD-03, TRAD-04, RISK-01, RISK-02, RISK-03, RISK-04
**Success Criteria** (what must be TRUE):
  1. Market and limit orders submit correctly, and every order is tracked through its lifecycle (submitted -> accepted -> partial fill -> filled / cancelled / rejected)
  2. Stop-loss and take-profit triggers fire automatically when price thresholds are hit, closing positions without manual intervention
  3. Trailing stop dynamically adjusts the stop level as price moves favorably, locking in gains
  4. Position sizing enforces per-symbol weight limits, total capital limits, and daily loss caps -- orders exceeding limits are rejected before submission
  5. Trading is restricted to configured market hours; orders outside allowed time windows (including auction periods) are blocked
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Data Pipeline & Strategy Engine
**Goal**: Technical indicators feed a condition engine that automatically generates buy/sell signals, completing the end-to-end automated trading loop
**Depends on**: Phase 2
**Requirements**: TRAD-01, TRAD-02
**Success Criteria** (what must be TRUE):
  1. SMA, EMA, RSI, MACD, and Bollinger Bands compute correctly on live streaming data using incremental calculation (not full recomputation per tick)
  2. The condition engine evaluates composite rules (indicator thresholds + price/volume conditions) and emits entry/exit signals that flow through the Risk Manager to the Order Manager
  3. A complete automated trading loop runs in paper trading: data reception -> indicator calculation -> condition evaluation -> risk validation -> order execution -> fill confirmation
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Monitoring & Operations
**Goal**: Users can observe and control the running system through a full GUI dashboard with real-time charts, configure strategies without code changes, and receive notifications on key events
**Depends on**: Phase 3
**Requirements**: GUI-01, GUI-02, GUI-03, NOTI-01, NOTI-02, NOTI-03
**Success Criteria** (what must be TRUE):
  1. Dashboard main screen shows current positions, pending orders, realized/unrealized P&L, and system connection status in real time
  2. Real-time candlestick chart displays live price data with selectable technical indicator overlays (MA, RSI, MACD, Bollinger Bands)
  3. Strategy parameters (entry/exit conditions, indicator settings, risk thresholds) can be created, saved, and loaded through the GUI without editing config files
  4. Trade executions and critical system events trigger GUI popup alerts, are written to rotating log files, and are sent to a configured Discord channel via webhook
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Backtest & Validation
**Goal**: Users can test strategies against historical data before risking real capital, with realistic cost modeling and comprehensive performance metrics
**Depends on**: Phase 3
**Requirements**: BACK-01, BACK-02, BACK-03
**Success Criteria** (what must be TRUE):
  1. The backtest engine replays historical OHLCV data through the same Strategy Engine and Risk Manager used in live trading, via the abstract DataSource interface
  2. Performance statistics (total return, MDD, win rate, profit factor, Sharpe ratio) are computed and displayed after each backtest run
  3. Backtest results are visualized with equity curves, drawdown charts, and trade markers on price charts
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. API Foundation | 1/3 | Complete    | 2026-03-12 |
| 2. Order Execution & Risk Management | 0/0 | Not started | - |
| 3. Data Pipeline & Strategy Engine | 0/0 | Not started | - |
| 4. Monitoring & Operations | 0/0 | Not started | - |
| 5. Backtest & Validation | 0/0 | Not started | - |
