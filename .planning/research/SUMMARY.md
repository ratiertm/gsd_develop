# Project Research Summary

**Project:** 키움증권 OpenAPI+ 주식 데이트레이딩 자동매매 시스템
**Domain:** Korean Stock Automated Day-Trading (Windows Desktop, COM/OCX)
**Researched:** 2026-03-13
**Confidence:** MEDIUM

## Executive Summary

This is a Windows-only desktop application for automated day-trading Korean stocks via Kiwoom Securities' OpenAPI+, a 32-bit COM/OCX control. The system must be built around PyQt5's QApplication event loop — this is not a design choice but a hard requirement. Kiwoom's OCX uses COM Single-Threaded Apartment (STA) model, meaning all API calls must originate from the main thread that created the COM control. Every architectural decision flows from this constraint: indicator calculations and strategy evaluation go to worker threads (QThread), but order submission and real-time data registration must execute on the main thread via pyqtSignal/Slot. There is no alternative; asyncio and plain threading will cause deadlocks or silent crashes.

The recommended approach is to build in strict phase order, starting with the Kiwoom connectivity layer (OCX wrapper + TR request queue with 4-second throttle) before touching any trading logic. The TR rate limit (3.6 seconds between requests) is a server-enforced constraint that will get the connection banned if violated during live trading. Real-time price data should be received via `SetRealReg` event subscriptions rather than TR polling — this is both more efficient and avoids burning rate limit budget. Risk management components (stop-loss, position sizing, kill switch) must be built before the strategy engine, not after, because placing money at risk without guards in place is unacceptable regardless of how simple the initial strategy is.

The primary risks are: (1) violating API rate limits during initial data loading, (2) treating `SendOrder()` return value as fill confirmation instead of submission acknowledgement, leading to duplicate orders, and (3) blocking the Qt event loop with synchronous computations, causing missed fill events and connection drops. All three are preventable by architecture — the TR request queue, an explicit order state machine, and QThread-based data processing respectively. The stack is constrained and well-established in the Korean developer community: 32-bit Python 3.10.x, PyQt5 5.15.x, pykiwoom as a reference (but direct QAxWidget subclassing is preferred for production), pandas + `ta` library, SQLite, and loguru.

---

## Key Findings

### Recommended Stack

The stack is non-negotiable at the connectivity layer. **32-bit Python 3.10.x** is mandatory — 64-bit Python cannot load the 32-bit OCX. **PyQt5 5.15.x** is the only Python GUI framework that supports `QAxWidget` for COM hosting; PyQt6 dropped this capability. For everything else, there is flexibility, but the community has converged on a standard set that minimizes friction.

**Core technologies:**
- **Python 3.10.x (32-bit, Windows):** Runtime — 32-bit is a hard requirement for Kiwoom OCX; 3.10 is the safest version for COM compatibility
- **PyQt5 5.15.x:** COM bridge and GUI framework — `QAxWidget` is the only way to host the OCX; also provides the `QApplication` event loop the API requires
- **pykiwoom 0.1.x:** Reference and prototyping wrapper — useful for understanding TR patterns; for production, subclass `QAxWidget` directly for full event control
- **pandas 2.1.x + numpy 1.26.x:** OHLCV data handling, indicator inputs/outputs — industry standard for time-series financial data
- **ta 0.11.x:** Technical indicator library — pure Python, no C build dependency; use over TA-Lib for easier Windows installation
- **SQLite (built-in):** Persistence layer — zero-config, sufficient for single-user desktop app trade logs and candle cache
- **loguru 0.7.x:** Structured logging with rotation — trade audit logs are non-negotiable; loguru's rotation and formatting justify the dependency
- **pyqtgraph 0.13.x:** Real-time charting — significantly faster than matplotlib for live candlestick updates
- **schedule 1.2.x + pyyaml 6.0.x:** Market-hours scheduling and strategy configuration

**Critical version constraint:** Do NOT use PyQt6 (removed QAxWidget), Python 64-bit, Python 3.11+ (COM compatibility issues reported), backtrader (unmaintained since 2021), or asyncio for API interaction.

### Expected Features

The feature set is well-understood for this domain. The core automated trading loop (login → real-time data → indicator calculation → condition evaluation → order execution → fill confirmation) is the entire value proposition and must work flawlessly before adding anything else. Risk management is co-equal with execution, not an add-on.

**Must have (v1 table stakes):**
- Kiwoom OpenAPI+ login/session management with auto-reconnect
- Real-time quote reception (price, volume) via `SetRealReg`
- Account balance and position inquiry
- Technical indicators: moving averages, RSI (minimum viable set)
- Condition engine: entry/exit rule evaluation
- Automated order execution: market and limit orders
- Fixed stop-loss and take-profit
- Per-symbol position size limit and total capital limit
- Market-hours management (09:00 open, 15:30 close, pre/post auction handling)
- Trade log persistence (SQLite or CSV)
- Emergency stop (kill switch): halt trading + cancel pending + market-sell all positions
- Basic status dashboard (even minimal console UI is acceptable for v1)

**Should have (v1.x, after core is stable):**
- Full PyQt5 GUI dashboard with real-time portfolio and order status
- Trailing stop
- Scaled entry/exit (split orders)
- Extended indicators: MACD, Bollinger Bands, Stochastic
- Discord/Telegram webhook notifications
- Strategy parameter preset management
- Kiwoom condition search integration (`SendCondition`)
- Volume spike detection

**Defer to v2+:**
- Backtesting engine (requires separate historical data pipeline, high complexity)
- Real-time candlestick chart with indicator overlay
- Daily/monthly performance reports
- Complex condition engine (AND/OR/NOT nesting)
- Custom indicator framework

**Anti-features to reject:** HFT (Kiwoom enforces 5 orders/second hard limit), AI/ML price prediction (insufficient data/infra for meaningful results), multi-broker support (each broker has incompatible API), mobile app (Windows COM cannot serve mobile), derivatives/futures (entirely different API system).

### Architecture Approach

The architecture is event-driven, centered on the `QApplication` event loop. The main thread owns COM calls, GUI rendering, and the QTimer-based TR request throttle. Worker threads (QThread) own indicator calculation and strategy evaluation. All cross-thread communication must use `pyqtSignal/Slot` — direct cross-thread GUI or COM access causes Qt crashes. The TR Request Queue (4-second interval, QTimer-driven) is an infrastructure component, not a feature; it must be built before any TR call is made elsewhere in the system.

**Major components:**
1. **KiwoomAPI (QAxWidget subclass)** — COM OCX wrapper; login, TR dispatch, real-time registration, order submission; runs on main thread only
2. **Event Router** — routes OCX callback events (OnReceiveTrData, OnReceiveRealData, OnReceiveChejanData) to registered handlers via registry pattern
3. **TR Request Queue** — rate limiter; QTimer-based dequeue at 4-second intervals; all TR calls go through this
4. **Data Processor (QThread)** — receives market data via queue, computes indicators incrementally, emits processed data via signal
5. **Risk Manager** — validates order requests before execution; enforces stop-loss, position limits, daily loss cap
6. **Order Manager** — maintains order state machine (Submitted → Accepted → Partial Fill → Filled / Cancelled / Rejected); runs on main thread for SendOrder calls
7. **Strategy Engine (QThread)** — evaluates entry/exit conditions; emits order requests to main thread via signal
8. **Scheduler (QTimer)** — manages market-hours logic; triggers pre-open data loading, post-close cleanup
9. **GUI Dashboard** — subscribes to signals from all components; never touches COM or worker thread data directly
10. **Logger/Notifier** — async file I/O and Discord webhooks in separate thread

**Key patterns:** TR Handler Registry (not giant if-elif), Observer/Dispatcher for real-time data, State Machine for order lifecycle, abstract DataSource interface for strategy engine (enables backtest/live swap without strategy code changes), QEventLoop for login synchronization (not `time.sleep()`).

**Package structure:** `api/` (OCX wrapper, event router, TR queue), `core/` (strategy, risk, order, scheduler, indicators), `data/` (market data, processor, storage), `gui/` (main window, widgets), `notification/`, `backtest/`, `config/`, `utils/`.

### Critical Pitfalls

1. **TR rate limit violation causes connection ban** — Implement `TRRequestQueue` with 4-second QTimer in Phase 1, before any other TR call exists. Use `SetRealReg` for real-time data; reserve TR for historical/account queries. Load historical data before market open, not during live trading.

2. **SendOrder() ≠ fill confirmation** — `SendOrder()` returning 0 means the order was submitted, not executed. Track every order by `sOrderNo` in an explicit state machine. All position and balance state must only update on `OnReceiveChejanData` events. Periodic reconciliation via opt10075 (pending orders query) as a safety net.

3. **Main thread blocking kills the system** — Never call `time.sleep()` on the main thread. Never run heavy computation (indicator calculation, backtest) on the main thread. Use QThread for all CPU work; use `QEventLoop` for synchronous-style waiting where needed (login flow). Blocking the main thread causes missed fill events, heartbeat failure, and connection drops.

4. **Risk management deferred until "later"** — Stop-loss and position limits must be built before the strategy engine, not after. A strategy that works without risk guards in paper trading will destroy a live account in an adverse market move. Risk Manager is a dependency of Order Manager, which is a dependency of Strategy Engine.

5. **Paper trading overconfidence before live deployment** — Kiwoom's simulation server grants instant fills with no slippage. Real execution has partial fills, spread costs, VI circuit breakers, and auction-period behaviors. Implement a 3-stage rollout: simulation → minimal live (1-share lots for one week) → full operation. Store server (live vs. simulation) in config, not in code.

---

## Implications for Roadmap

Based on research, the architecture's dependency graph maps directly to a 5-phase build order. Each phase must be stable and tested before the next begins — there is no parallelism here because every layer depends on the one below it.

### Phase 1: Foundation — API Connectivity and Infrastructure

**Rationale:** The COM OCX wrapper, event routing, TR throttle, logging, and configuration management are prerequisites for every other component. Building anything else first means rebuilding it later when the real constraints become apparent. Session management (auto-reconnect, SetRealReg restoration after disconnect) must also be here — a fragile connection makes everything built on top of it unreliable.

**Delivers:** A stable, rate-limit-compliant Kiwoom API connection with event routing, structured logging, and YAML-based configuration. The system can log in, receive real-time data for a watchlist, query account balance, and reconnect automatically.

**Addresses (from FEATURES.md):** Login/session management, real-time quote reception, account balance/position query, market-hours management (Scheduler skeleton), trade log infrastructure.

**Avoids (from PITFALLS.md):** TR rate limit violation (Pitfall 1), session management failure (Pitfall 6), event loop blocking (Pitfall 3 — architecture is established here).

**Needs research-phase:** No — COM/STA threading model and PyQt5 QAxWidget patterns are well-documented. TR throttling pattern is standard.

---

### Phase 2: Order Execution and Risk Management

**Rationale:** Order submission and risk enforcement must be complete and tested together before any automated strategy runs. The order state machine (Pitfall 2) and risk guards (Pitfall 4) are co-equal concerns that share the same data (positions, balances). Building strategy logic before order management is proven reliable is how automated systems lose money.

**Delivers:** A fully functional order execution layer with state machine tracking (submitted/accepted/partial/filled/cancelled/rejected), Risk Manager enforcing per-symbol and total capital limits plus stop-loss, emergency kill switch, and market-hours order controls (auction period handling, pre-close position cleanup).

**Addresses (from FEATURES.md):** Automated order execution (market/limit), fixed stop-loss/take-profit, position size limits, kill switch, market-hours management (complete implementation), pending order management.

**Avoids (from PITFALLS.md):** Async order processing failure (Pitfall 2), risk management absence (Pitfall 4), auction-period mis-handling (Pitfall 7).

**Needs research-phase:** Possibly — Kiwoom `SendOrder` parameter codes (호가구분, sHogaGb) and `OnReceiveChejanData` gubun field values are underdocumented in community sources. Verify against official Kiwoom OpenAPI+ guide before implementation.

---

### Phase 3: Data Pipeline and Strategy Engine

**Rationale:** With a reliable API connection (Phase 1) and proven order execution (Phase 2), the strategy engine can be built with confidence that its outputs will be handled correctly. The Data Processor (QThread, incremental indicator calculation) feeds the Strategy Engine (QThread, condition evaluation), which emits order requests back to the main thread through the Risk Manager gate established in Phase 2.

**Delivers:** A working automated trading loop — real-time data flows from Kiwoom OCX through Data Processor (MA, RSI indicators), into Strategy Engine (configurable entry/exit conditions), through Risk Manager validation, to Order Manager execution. Paper-trading validated end-to-end.

**Addresses (from FEATURES.md):** Technical indicators (MA, RSI), condition engine (basic AND logic), YAML strategy parameter configuration, full v1 MVP.

**Avoids (from PITFALLS.md):** Performance traps — incremental indicator calculation (not full recalculation per tick), fixed-size deque for in-memory data (not growing DataFrame append), pre-market historical data load (not intraday TR calls).

**Needs research-phase:** No — indicator calculation patterns with `ta` library and pandas are well-documented. Strategy condition evaluation is domain logic, not a research question.

---

### Phase 4: Monitoring and Operations

**Rationale:** Once the automated trading loop is validated in paper trading, operational quality features become the priority. A system running real money needs observable state, remote monitoring when away from the desk, and runtime configurability without restarts.

**Delivers:** Full PyQt5 GUI dashboard (portfolio, orders, P&L, system status), Discord/Telegram webhook notifications (fills, errors, daily summary), strategy preset management (save/load YAML configs), runtime parameter adjustment, connection status heartbeat display.

**Addresses (from FEATURES.md):** GUI dashboard, Discord/Telegram alerts, strategy preset management, extended indicators (MACD, Bollinger Bands).

**Avoids (from PITFALLS.md):** UX pitfalls — no-alert failure modes, absence of kill switch in GUI, inability to adjust strategy without restart.

**Needs research-phase:** No — PyQt5 widget patterns and Discord webhook integration are well-documented standard patterns.

---

### Phase 5: Validation and Backtest Engine

**Rationale:** The backtest engine is architecturally independent but strategically valuable only after the live trading loop has accumulated enough real-trade data to validate against. The abstract `DataSource` interface (established in Phase 3) makes this a matter of implementing `BacktestDataSource` without touching strategy code. Historical candle data acquisition via Kiwoom opt10080 should be addressed here.

**Delivers:** Backtest engine replaying historical OHLCV data through the same Strategy Engine used in live trading, with slippage/commission/tax modeling, and performance metrics (win rate, MDD, Sharpe ratio). Performance reports (daily/monthly). Simulation → live deployment workflow documentation.

**Addresses (from FEATURES.md):** Backtest engine, performance reports, Kiwoom condition search (`SendCondition`) integration for dynamic watchlist.

**Avoids (from PITFALLS.md):** Paper-trading overconfidence (Pitfall 5) — backtest includes realistic cost modeling; live rollout uses minimal share quantities first.

**Needs research-phase:** Yes — Kiwoom historical data API (opt10080, opt10081) has documented limitations on lookback period and minimum request intervals. Verify data availability and structure before designing the data loader.

---

### Phase Ordering Rationale

- **COM infrastructure before everything:** No component can be tested without a working Kiwoom connection. Discovering threading or rate-limit constraints during Phase 3 strategy work would require rebuilding Phase 1-2 components.
- **Order management before strategy:** An automated strategy that can place orders but cannot track fill status will produce duplicate orders and corrupted position state within minutes of live operation.
- **Risk manager co-built with order manager:** These two components share position state and must be developed as a unit. Risk validation is a gate in the order execution path, not a wrapper around it.
- **GUI deferred to Phase 4:** The trading loop is operational without a full GUI. Building GUI in parallel with core trading logic adds coordination overhead and PyQt5 signal-plumbing complexity at the worst time.
- **Backtest last:** The backtest engine reuses strategy and indicator code from Phase 3. Building it first would require mocking the entire live data stack, which is wasted effort.

### Research Flags

**Phases likely needing `/gsd:research-phase` during planning:**
- **Phase 2:** Kiwoom `SendOrder` API details — `sHogaGb` codes, `OnReceiveChejanData` gubun values, and edge cases for partial fills/cancellations are inconsistently documented in community sources. Verify against the official Kiwoom OpenAPI+ developer guide PDF before implementing the order state machine.
- **Phase 5:** Kiwoom historical data API — `opt10080`/`opt10081` TR codes have undocumented limits on lookback depth and mandatory request intervals. Research data acquisition strategy (how many candles per request, how to paginate, whether to cache to SQLite on first run) before designing the backtest data loader.

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** COM/STA threading + PyQt5 QAxWidget is a solved, well-documented problem. TR request throttling is a standard queue pattern.
- **Phase 3:** pandas + `ta` library indicator calculation is thoroughly documented. Strategy condition evaluation is business logic.
- **Phase 4:** PyQt5 widget layout and Discord webhook HTTP calls are straightforward standard patterns.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core stack (Python 32-bit, PyQt5, pykiwoom) is community consensus with years of use. Version numbers need PyPI verification before install. WebSearch was unavailable during research. |
| Features | MEDIUM | Kiwoom API feature boundaries (TR codes, real-time FID codes, rate limits) are stable since ~2015. Community resources are abundant. Anti-features analysis is solid. |
| Architecture | MEDIUM-HIGH | COM/STA threading model is Microsoft-documented and well-understood. PyQt5 signal/slot patterns are Qt-documented. The layer structure and data flow reflect established Korean quant community conventions. |
| Pitfalls | MEDIUM | All 7 critical pitfalls are validated by community experience (blogs, GitHub issues, books on Korean automated trading). Specific recovery details may vary by Kiwoom API version. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Exact Kiwoom API version and recent changes:** Kiwoom periodically updates OpenAPI+. Verify current TR codes, error codes, and rate limits against the official developer guide before Phase 1 implementation. The API has been stable since ~2015 but minor changes occur.
- **Python 3.10 32-bit COM compatibility:** Reports of issues with Python 3.11+ in 32-bit COM contexts exist in community sources but are not formally documented by Kiwoom. Test the exact Python 3.10.x + PyQt5 5.15.x combination on the target Windows machine before full development.
- **Real-time registration limit (100 symbols):** The ~100 symbol limit for `SetRealReg` is community-reported, not officially documented. Validate this limit in paper trading environment before designing watchlist management logic.
- **Historical data depth via opt10080/opt10081:** Maximum lookback period and candle count per request are not clearly documented. This gap blocks backtest data pipeline design and should be resolved before Phase 5.

---

## Sources

### Primary (MEDIUM confidence — training data, well-established domain)
- Kiwoom Securities OpenAPI+ official developer guide (training data basis, verify current version)
- Qt/PyQt5 threading documentation — COM STA model, QThread, pyqtSignal/Slot patterns
- pykiwoom library (github.com/sharebook-kr/pykiwoom) — API wrapper patterns and TR usage examples

### Secondary (MEDIUM confidence)
- Korean quant developer community (wikidocs.net, tistory blogs, 파이썬으로 배우는 알고리즘 트레이딩 book) — pitfalls, rate limits, threading patterns
- KRX (Korea Exchange) market rules — trading hours, VI mechanism, auction periods

### Tertiary (LOW confidence — needs validation before relying on)
- Real-time registration symbol count limit (~100) — community-reported, not officially stated
- Python 3.11+ COM issues in 32-bit context — anecdotal community reports
- Competitor API comparison (CybosPlus, xingAPI) — may not reflect current API versions

---
*Research completed: 2026-03-13*
*Ready for roadmap: yes*
