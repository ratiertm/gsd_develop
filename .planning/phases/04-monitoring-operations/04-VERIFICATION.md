---
phase: 04-monitoring-operations
verified: 2026-03-14T00:00:00Z
status: passed
score: 17/17 must-haves verified
re_verification: false
---

# Phase 4: Monitoring & Operations Verification Report

**Phase Goal:** Real-time monitoring dashboard, candlestick charts with indicators, strategy settings UI, and notification system (toast + Discord)
**Verified:** 2026-03-14
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Notification dispatcher routes events to enabled channels (GUI toast, log, Discord) | VERIFIED | `Notifier.notify()` checks `log_enabled`, `gui_popup_enabled`, `discord_enabled` independently in notifier.py:47-65 |
| 2  | Toast widget appears bottom-right and auto-dismisses after ~4 seconds | VERIFIED | `ToastWidget` with `duration_ms=4000`, `QTimer.timeout -> _fade_out_and_close()`, positioned via `MainWindow.show_toast()` at `x = self.width() - toast.width() - margin` |
| 3  | Discord webhook sends color-coded Embed (green=buy, red=sell) via background thread | VERIFIED | `build_trade_embed()` color=0x26A69A for BUY, color=0xEF5350 for SELL; `DiscordSendWorker(threading.Thread)` |
| 4  | Notification failures never block or crash the system | VERIFIED | All channel sends wrapped in `try/except Exception: pass`; `DiscordSendWorker.run()` catches all exceptions |
| 5  | Each channel can be independently toggled ON/OFF via config | VERIFIED | `_config.get("gui_popup_enabled")`, `_config.get("log_enabled")`, `_config.get("discord_enabled")` — each checked independently |
| 6  | Dashboard shows current positions with 8 columns and color-coded P&L | VERIFIED | `DashboardTab.POSITION_COLUMNS` has 8 entries; `pnl_color()` returns red for positive (#EF5350), blue for negative (#42A5F5) — Korean convention |
| 7  | Dashboard shows pending/filled orders in separate sub-tabs | VERIFIED | `split_orders()` separates by `OrderState`; `update_orders()` populates both `_pending_table` and `_filled_table` |
| 8  | Dashboard shows system status and log panel (max 500 lines) | VERIFIED | `update_status()` and `append_log()` methods exist; `_MAX_LOG_LINES = 500` enforced with trim |
| 9  | Candlestick chart renders OHLCV with green/red candles | VERIFIED | `CandlestickItem._generate_picture()` uses `COLOR_UP = "#26A69A"` and `COLOR_DOWN = "#EF5350"` |
| 10 | MA/Bollinger/VWAP overlay, RSI/MACD/OBV in sub-charts | VERIFIED | Overlay `PlotDataItem` instances for sma/ema/bollinger/vwap; sub-charts via `create_rsi_plot`, `create_macd_plot`, `create_obv_plot` |
| 11 | Indicator checkboxes toggle overlays ON/OFF immediately | VERIFIED | `toggle_indicator()` sets `_visible_indicators`, calls `setVisible()` for price overlays, `setMaximumHeight(0/100)` for sub-charts |
| 12 | Watchlist click switches chart to selected stock | VERIFIED | `QListWidget.currentTextChanged.connect(self.switch_chart)` in chart_tab.py:93; `switch_chart()` sets `_current_code` and calls `_refresh_chart()` |
| 13 | Trade markers appear as colored triangles (green up=buy, red down=sell) | VERIFIED | `_draw_trade_markers()` uses `symbol='t'` + brush `#26A69A` for BUY, `symbol='t1'` + brush `#EF5350` for SELL via `ScatterPlotItem` |
| 14 | User can CRUD strategies with validation, save writes config and hot-swaps StrategyManager | VERIFIED | `validate_strategy()`, `form_to_strategy_dict()`, `StrategyTab._on_save()` calls `settings.save()` then `_on_strategy_reload()`; `_reload_strategies()` in main.py re-creates StrategyManager |
| 15 | Watchlist management: add/remove stock codes, assign strategies | VERIFIED | `watchlist_add_code()`, `watchlist_remove_code()`, `watchlist_assign_strategy()` pure functions; UI buttons in `StrategyTab._on_add_stock/remove_stock` |
| 16 | All GUI tabs wired to live data sources in main.py | VERIFIED | main.py Phase 4 section: QTimer polls PositionTracker, `order_filled.connect()` bridges to dashboard and chart, CandleAggregator callback wired to ChartTab, loguru sink added to `dashboard.append_log` |
| 17 | 120-candle sliding window for chart performance | VERIFIED | `MAX_CANDLES = 120`; `on_new_candle()` trims `buf[-MAX_CANDLES:]`; CandlestickItem also enforces `data[-self._max_visible:]` |

**Score:** 17/17 truths verified

---

## Required Artifacts

| Artifact | Min Lines | Actual Lines | Status | Notes |
|----------|-----------|-------------|--------|-------|
| `kiwoom_trader/gui/main_window.py` | 50 | 144 | VERIFIED | QMainWindow with QTabWidget (3 real tabs), `show_toast()`, toast stacking |
| `kiwoom_trader/gui/widgets/toast_widget.py` | 40 | 88 | VERIFIED | `ToastWidget(QLabel)` with QPropertyAnimation fade-in/out, auto-dismiss |
| `kiwoom_trader/gui/notification/notifier.py` | — | 103 | VERIFIED | Exports `Notifier`; routes to 3 channels with rate limiting |
| `kiwoom_trader/gui/notification/discord_sender.py` | — | 91 | VERIFIED | Exports `DiscordSendWorker`, `build_trade_embed`; `threading.Thread` background send |
| `kiwoom_trader/gui/dashboard_tab.py` | 150 | 405 | VERIFIED | DashboardTab with 5 public update methods, pure functions `pnl_color`, `build_position_rows`, `split_orders` |
| `tests/test_dashboard_tab.py` | — | 144 | VERIFIED | 8 tests covering data binding logic |
| `kiwoom_trader/gui/widgets/candlestick_item.py` | 40 | 145 | VERIFIED | `CandlestickItem(pg.GraphicsObject)` with QPicture pre-rendering, stub fallback |
| `kiwoom_trader/gui/chart_tab.py` | 200 | 312 | VERIFIED | ChartTab with price plot, sub-charts, indicator toggles, watchlist, trade markers |
| `kiwoom_trader/gui/widgets/indicator_chart.py` | 30 | 106 | VERIFIED | `create_rsi_plot`, `create_macd_plot`, `create_obv_plot` factory functions |
| `tests/test_chart_widgets.py` | — | 152 | VERIFIED | 8 tests for data conversion, sliding window, toggles, markers |
| `kiwoom_trader/gui/strategy_tab.py` | 200 | 725 | VERIFIED | StrategyTab with CRUD, validation, serialization, watchlist operations |
| `kiwoom_trader/main.py` | — | 381 | VERIFIED | Contains `MainWindow`, `Notifier`, `get_active_orders` bridging, Phase 4 wiring section |
| `tests/test_strategy_tab.py` | — | 200 | VERIFIED | 15 tests for validation, serialization, copy, watchlist |
| `kiwoom_trader/config/settings.py` | — | 159 | VERIFIED | `notification` section in `_default_config()`, `save()` method, `notification_config` property |

---

## Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `notifier.py` | `toast_widget.py` | `main_window.show_toast()` | WIRED | notifier.py:59 — `self._main_window.show_toast(title, message, event_type)` |
| `notifier.py` | loguru | `logger.bind(log_type='trade')` | WIRED | notifier.py:50 — `logger.bind(log_type="trade").info(...)` |
| `discord_sender.py` | Discord webhook URL | `os.getenv('DISCORD_WEBHOOK_URL')` | WIRED | discord_sender.py:76 — `os.getenv("DISCORD_WEBHOOK_URL", "")` |
| `dashboard_tab.py` | `position_tracker.py` | `update_positions()` method call | WIRED | main.py:281-288 — QTimer polls `position_tracker.positions`, calls `dashboard.update_positions()` |
| `dashboard_tab.py` | `order_manager.py` | `get_active_orders()` bridging | WIRED | main.py:295-298 — `order_filled.connect(lambda: dashboard.update_orders(order_manager.get_active_orders()))` |
| `dashboard_tab.py` | `market_hours.py` | `register_state_callback` | WIRED | main.py:312-327 — `market_hours.register_state_callback(_on_market_state_for_dashboard)` |
| `chart_tab.py` | `candlestick_item.py` | `CandlestickItem.set_data()` | WIRED | chart_tab.py:274 — `self._candlestick_item.set_data(buf)` |
| `chart_tab.py` | `candle_aggregator.py` | `on_candle_complete callback` | WIRED | main.py:332-333 — `candle_aggregator.register_callback(chart_tab.on_new_candle)` |
| `strategy_tab.py` | `settings.py` | `Settings.save()` | WIRED | strategy_tab.py:688 — `self._settings.save()` (and lines 489, 714, 724) |
| `strategy_tab.py` | `strategy_manager.py` | `on_strategy_reload` hot-swap | WIRED | main.py:231-248 — `_reload_strategies()` re-creates `StrategyManager`, re-wires `candle_aggregator._callbacks` |
| `main.py` | `main_window.py` | `MainWindow` instantiation | WIRED | main.py:53-54 import; main.py:251-254 — `MainWindow(settings, on_strategy_reload=...)` |
| `main.py` | `notifier.py` | `Notifier` instantiation | WIRED | main.py:263-266 — `Notifier(config=settings.notification_config, main_window=main_window)` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| GUI-01 | 04-02 | 대시보드 메인 화면 — 보유종목, 주문현황, 수익률, 시스템 상태 표시 | SATISFIED | `DashboardTab` with positions (8 columns), orders (pending+filled tabs), P&L summary (daily+unrealized+invested), system status (connection/market/strategy/mode), log panel |
| GUI-02 | 04-03 | 실시간 분봉차트 — pyqtgraph 기반 + 기술지표 오버레이 | SATISFIED | `ChartTab` with `CandlestickItem` (pyqtgraph QPicture), overlay indicators (SMA/EMA/Bollinger/VWAP), sub-chart indicators (RSI/MACD/OBV), watchlist, trade markers |
| GUI-03 | 04-04 | 전략 설정 UI — 매매 조건/파라미터를 GUI에서 설정·저장·불러오기 | SATISFIED | `StrategyTab` with CRUD editor, `validate_strategy()`, `Settings.save()` on form submit, `_reload_strategies()` hot-swap callback |
| NOTI-01 | 04-01 | GUI 팝업 알림 — 매매 체결, 조건 충족 신호 발생 시 팝업 | SATISFIED | `ToastWidget` with fade animation, `Notifier` routes to `main_window.show_toast()` when `gui_popup_enabled=True` |
| NOTI-02 | 04-01 | 로그 파일 기록 — 매매 내역, 오류, 시스템 상태를 파일로 저장 | SATISFIED | `Notifier` calls `logger.bind(log_type="trade").info()` when `log_enabled=True`; loguru routes to file sinks per Phase 1 setup |
| NOTI-03 | 04-01 | Discord 웹훅 알림 — 매매 체결/주요 이벤트 Discord 전송 | SATISFIED | `DiscordSendWorker(threading.Thread)` sends via `urllib.request`; `build_trade_embed()` produces color-coded embeds; rate limiting prevents webhook flooding |

All 6 requirements (GUI-01, GUI-02, GUI-03, NOTI-01, NOTI-02, NOTI-03) SATISFIED.
No orphaned requirements found — all Phase 4 requirements are claimed by plans.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `gui/dashboard_tab.py` | 248 | `""  # name placeholder -- resolved by code-name mapping` | Info | Stock names show blank in positions table. Requires code-to-name lookup (not in scope for Phase 4) |

No blocker or warning anti-patterns found. The single info-level placeholder (stock name column shows empty string) is a known architectural gap noted inline — requires a code-name mapping source not available in Phase 4 scope.

---

## Test Results

All Phase 4 tests pass: **43/43 tests passed (0.05s)**

| Test File | Count | Status |
|-----------|-------|--------|
| `tests/test_notifier.py` | 6 | PASS |
| `tests/test_discord_sender.py` | 5 | PASS |
| `tests/test_toast_widget.py` | 1 | PASS |
| `tests/test_dashboard_tab.py` | 8 | PASS |
| `tests/test_chart_widgets.py` | 8 | PASS |
| `tests/test_strategy_tab.py` | 15 | PASS |

---

## Human Verification Required

### 1. Toast Notification Visual Appearance

**Test:** Launch application, trigger a trade fill, observe toast notification
**Expected:** Bottom-right overlay appears with correct border color (green for trade), fades in over 300ms, displays title + message, auto-dismisses after 4 seconds, multiple toasts stack vertically
**Why human:** Animation timing, visual stacking behavior, and readability cannot be verified without a running Qt instance

### 2. Candlestick Chart Real-Time Update

**Test:** With live Kiwoom connection in paper mode, observe the Chart tab while a monitored stock receives tick data
**Expected:** New candles appear in real-time, chart auto-scrolls to latest candle, trade markers appear as green/red triangles on fill events
**Why human:** Real-time rendering behavior, auto-scroll correctness, and visual marker appearance require live data and a display

### 3. Strategy Hot-Swap Under Load

**Test:** While paper trading is active (StrategyManager running), open Strategy tab, modify an RSI threshold, click Save
**Expected:** Config writes to config.json immediately, StrategyManager re-initializes with new config without interrupting the candle feed, no missed candles during reload
**Why human:** Thread-safety and timing behavior during hot-swap cannot be verified statically

### 4. Discord Webhook Integration

**Test:** Set `discord_enabled: true` in config and `DISCORD_WEBHOOK_URL` in .env, trigger a trade fill
**Expected:** Discord message arrives in channel with correct green/red embed color, fields show code/price/qty/strategy/pnl_pct
**Why human:** Requires live Discord webhook URL and external network access

---

## Gaps Summary

No gaps found. All 17 observable truths are verified, all 14 required artifacts pass all three levels (exists, substantive, wired), all 12 key links are confirmed wired, and all 6 requirements are satisfied.

The only notable deviation from plan specifications was:
- `dashboard_tab.py` derives `current_price` from `avg_price + unrealized_pnl // qty` because the `Position` dataclass lacks a `current_price` field — this was documented as an auto-fixed deviation in the SUMMARY
- `strategy_tab.py` defines `OPERATORS` locally instead of importing from `condition_engine` — also documented and correct

Both deviations are functionally equivalent to the plan's intent and all tests pass.

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
