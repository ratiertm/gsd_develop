# Phase 4: Monitoring & Operations - Research

**Researched:** 2026-03-14
**Domain:** PyQt5 GUI Dashboard, pyqtgraph Charts, Notification Systems (GUI toast, Discord webhook, loguru)
**Confidence:** HIGH

## Summary

Phase 4 builds a PyQt5 GUI dashboard with three main tabs (Dashboard, Chart, Strategy Settings), a toast notification system, and Discord webhook integration. The project already has a robust PyQt5 foundation with pyqtSignal/Slot patterns, config.json-driven architecture, and loguru multi-sink logging. All data sources exist: PositionTracker, OrderManager, CandleAggregator, MarketHoursManager, StrategyManager, and PaperTrader.

The chart component uses pyqtgraph with a custom CandlestickItem (GraphicsObject subclass using QPicture pre-rendering). The candlestick pattern is well-documented in pyqtgraph's own examples. Toast notifications can be built as a lightweight custom QWidget with QPropertyAnimation for fade-in/out -- no external library needed given the simple requirements. Discord webhooks use stdlib `urllib.request` to avoid adding `requests` as a dependency (the project currently has no HTTP library dependency).

**Primary recommendation:** Use pyqtgraph 0.13.7 (compatible with PyQt5), custom CandlestickItem from pyqtgraph's canonical example pattern, hand-built toast widget (QLabel + QPropertyAnimation), and raw urllib.request for Discord webhooks. Structure GUI as `kiwoom_trader/gui/` package with separate modules per tab/widget.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Tab-based layout: top tabs for Dashboard/Chart/Strategy Settings. Each tab is an independent screen.
- Data updates via pyqtSignal push -- events immediately reflected in UI.
- Order status: pending + filled combined, tab-separated.
- Bottom log panel on dashboard tab: real-time scrolling system/trade log.
- Window: fixed minimum size, resizable.
- pyqtgraph-based candlestick chart.
- Indicator overlay: MA/Bollinger/VWAP on price chart, RSI/MACD/OBV as sub-charts below.
- Indicator toggle: checkbox ON/OFF with immediate chart update.
- Watchlist in chart tab: click to switch chart to selected stock.
- Trade markers: buy (green triangle up) / sell (red triangle down) on chart.
- Form-based strategy editing: select strategy, edit parameters via input fields.
- New strategy creation: name + indicator dropdown + operator dropdown + value input + AND/OR combination.
- Save immediately applies: write config.json + reload StrategyManager. Hot-swap during market hours.
- Watchlist GUI management: add/remove stock codes + assign strategies per stock.
- Strategy copy/delete with confirmation dialog.
- Storage: config.json strategies section, reuse existing Settings pattern.
- Toast notification: bottom-right, 3-5 seconds, auto-dismiss. Non-blocking.
- Alert events: trade execution, strategy signal, system error -- 3 levels covered.
- Per-channel toggle: GUI popup, log file, Discord each independently ON/OFF in config.json.
- Discord webhook: Embed format with structured card (code/name/price/pnl). Buy=green, Sell=red color.
- Discord webhook URL in .env (per Phase 1 convention).
- Failure handling: log error and continue. Notifications never block trading logic.
- Log file: extend existing loguru trade sink. Use Phase 1's trade-YYYY-MM-DD.log pattern.

### Claude's Discretion
- Position table column composition (day-trading appropriate)
- System status display items (day-trading operation appropriate)
- Window minimum size exact value
- Chart x-axis range and scroll behavior
- Toast notification exact display time and animation
- Strategy edit form detail layout and validation approach

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUI-01 | Dashboard main screen -- positions, orders, P&L, system status | PositionTracker.get_all_positions(), OrderManager.get_active_orders(), PositionTracker.get_daily_pnl(), MarketHoursManager.get_market_state() as data sources. QTableWidget for tables, QLabel for status. pyqtSignal push for real-time updates. |
| GUI-02 | Real-time candlestick chart with indicator overlays | pyqtgraph 0.13.7 CandlestickItem (custom GraphicsObject + QPicture). PlotWidget for main chart + linked sub-chart PlotWidgets for RSI/MACD/OBV. CandleAggregator callback for live data. indicators.py classes for overlay data. |
| GUI-03 | Strategy settings UI -- create/edit/save/load without config files | Settings._config["strategies"] as data source. QFormLayout for parameter editing. QComboBox for indicator/operator selection. JSON write to config.json + StrategyManager re-init for hot-swap. |
| NOTI-01 | GUI popup alerts on trade execution and critical events | Custom ToastWidget (QLabel subclass) with QPropertyAnimation opacity fade. Positioned bottom-right of main window. Timer-based auto-dismiss (4 seconds). |
| NOTI-02 | Log file recording of trades, errors, system status | Already exists via loguru multi-sink (Phase 1). trade-YYYY-MM-DD.log + system/error logs. Notification events use `logger.bind(log_type="trade").info()` pattern. No new sink needed. |
| NOTI-03 | Discord webhook alerts for trade execution and key events | urllib.request POST to Discord webhook URL from .env. Embed JSON with color-coded cards (green=0x00FF00 for buy, red=0xFF0000 for sell). Async via QThread worker to avoid blocking UI. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt5 | 5.15.10 | GUI framework | Already in requirements.txt. Provides QTabWidget, QTableWidget, QFormLayout, signals/slots |
| pyqtgraph | 0.13.7 | Real-time charting | Fast NumPy-backed plotting. Custom GraphicsObject for candlesticks. Compatible with PyQt5.15. Already proven pattern in financial apps |
| loguru | (existing) | Logging | Already configured with multi-sink. Extend for notification events |
| python-dotenv | (existing) | Environment variables | Already used for .env loading (Discord webhook URL) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | latest | Chart data arrays | pyqtgraph dependency. Use for candlestick data arrays and indicator plot data |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyqtgraph | matplotlib | matplotlib is slower for real-time updates; pyqtgraph is designed for live data |
| Custom toast | pyqt-toast-notification | External dependency for a simple feature; custom widget is ~50 lines |
| urllib.request | requests library | requests adds a dependency; urllib.request is stdlib and sufficient for simple POST |
| Custom toast | QSystemTrayIcon.showMessage | OS-level notification, not in-app. Less control over styling |

**Installation:**
```bash
pip install pyqtgraph==0.13.7 numpy
```

## Architecture Patterns

### Recommended Project Structure
```
kiwoom_trader/
├── gui/
│   ├── __init__.py
│   ├── main_window.py          # QMainWindow with QTabWidget
│   ├── dashboard_tab.py        # GUI-01: positions, orders, P&L, status, log panel
│   ├── chart_tab.py            # GUI-02: candlestick chart + indicator overlays
│   ├── strategy_tab.py         # GUI-03: strategy editor, watchlist manager
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── candlestick_item.py # Custom pyqtgraph CandlestickItem
│   │   ├── toast_widget.py     # Toast notification overlay
│   │   └── indicator_chart.py  # Sub-chart widget for RSI/MACD/OBV
│   └── notification/
│       ├── __init__.py
│       ├── notifier.py         # Central notification dispatcher (routes to channels)
│       └── discord_sender.py   # Discord webhook sender (QThread worker)
```

### Pattern 1: CandlestickItem (pyqtgraph Custom GraphicsObject)
**What:** Pre-rendered candlestick chart item using QPicture for fast paint().
**When to use:** Displaying OHLCV candlestick data in pyqtgraph PlotWidget.
**Example:**
```python
# Source: pyqtgraph/examples/customGraphicsItem.py (canonical example)
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui

class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        """data: list of (time, open, close, low, high) tuples"""
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.picture = QtGui.QPicture()
        self._generate_picture()

    def _generate_picture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        if len(self.data) < 2:
            p.end()
            return
        w = (self.data[1][0] - self.data[0][0]) / 3.0
        for (t, open_, close, low, high) in self.data:
            p.drawLine(QtCore.QPointF(t, low), QtCore.QPointF(t, high))
            if open_ > close:
                p.setBrush(pg.mkBrush('#EF5350'))  # red (down)
            else:
                p.setBrush(pg.mkBrush('#26A69A'))  # green (up)
            p.drawRect(QtCore.QRectF(t - w, open_, w * 2, close - open_))
        p.end()

    def set_data(self, data):
        """Update with new data and redraw."""
        self.data = data
        self._generate_picture()
        self.informViewBoundsChanged()
        self.update()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())
```

### Pattern 2: Notification Dispatcher (Observer)
**What:** Central notifier that routes events to multiple channels (GUI toast, log, Discord).
**When to use:** When any trade execution, strategy signal, or system error occurs.
**Example:**
```python
from loguru import logger

class Notifier:
    """Routes notification events to enabled channels."""

    def __init__(self, config: dict, main_window=None):
        self._config = config.get("notification", {})
        self._main_window = main_window
        self._discord_sender = None  # Lazy init

    def notify(self, event_type: str, title: str, message: str, data: dict = None):
        """Dispatch notification to all enabled channels.

        Args:
            event_type: "trade", "signal", "error"
            title: Short title for the notification
            message: Detailed message
            data: Optional structured data (code, price, pnl, etc.)
        """
        # Always log (NOTI-02 -- uses existing loguru trade sink)
        if self._config.get("log_enabled", True):
            logger.bind(log_type="trade").info(f"[{event_type.upper()}] {title}: {message}")

        # GUI toast (NOTI-01)
        if self._config.get("gui_popup_enabled", True) and self._main_window:
            self._main_window.show_toast(title, message, event_type)

        # Discord (NOTI-03)
        if self._config.get("discord_enabled", False):
            self._send_discord(event_type, title, message, data)
```

### Pattern 3: QThread Worker for Discord Webhook
**What:** Non-blocking HTTP POST to Discord via QThread to prevent UI freeze.
**When to use:** Every Discord notification send.
**Example:**
```python
import json
import os
import urllib.request
from PyQt5.QtCore import QThread

class DiscordSendWorker(QThread):
    """Send Discord webhook in background thread."""

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self._payload = payload
        self._webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")

    def run(self):
        if not self._webhook_url:
            return
        try:
            data = json.dumps(self._payload).encode("utf-8")
            req = urllib.request.Request(
                self._webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            from loguru import logger
            logger.error(f"Discord webhook failed: {e}")
```

### Pattern 4: Toast Widget with Fade Animation
**What:** Non-blocking bottom-right overlay notification.
**When to use:** GUI popup alerts (NOTI-01).
**Example:**
```python
from PyQt5.QtCore import QPropertyAnimation, QTimer, Qt
from PyQt5.QtWidgets import QLabel, QGraphicsOpacityEffect

class ToastWidget(QLabel):
    """Self-dismissing toast notification."""

    def __init__(self, parent, title: str, message: str, duration_ms: int = 4000):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setText(f"<b>{title}</b><br>{message}")
        self.setStyleSheet(
            "background: #323232; color: white; padding: 12px; "
            "border-radius: 8px; font-size: 13px;"
        )
        self.setFixedWidth(300)
        self.adjustSize()

        # Opacity effect for fade animation
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)

        # Fade in
        self._fade_in = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_in.setDuration(300)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)

        # Auto dismiss after duration
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out_and_close)
        self._timer.start(duration_ms)

        self._fade_in.start()

    def _fade_out_and_close(self):
        fade_out = QPropertyAnimation(self._opacity, b"opacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(self.deleteLater)
        fade_out.start()
        self._fade_out_ref = fade_out  # prevent GC
```

### Pattern 5: Strategy Hot-Swap via Config Rewrite
**What:** GUI edits strategy -> writes config.json -> StrategyManager re-initializes.
**When to use:** Strategy create/edit/save from GUI-03.
**Example:**
```python
def save_strategy(self, strategy_dict: dict):
    """Save strategy to config.json and reload StrategyManager."""
    # Update in-memory config
    strategies = self._settings._config.get("strategies", [])
    # Find and replace or append
    found = False
    for i, s in enumerate(strategies):
        if s["name"] == strategy_dict["name"]:
            strategies[i] = strategy_dict
            found = True
            break
    if not found:
        strategies.append(strategy_dict)

    self._settings._config["strategies"] = strategies

    # Write to disk
    import json
    with open(self._settings._config_path, "w", encoding="utf-8") as f:
        json.dump(self._settings._config, f, indent=2, ensure_ascii=False)

    # Reload StrategyManager (hot-swap)
    # StrategyManager.__init__ re-parses strategies from config
```

### Anti-Patterns to Avoid
- **Blocking UI thread with HTTP requests:** Discord webhook MUST use QThread. Never call urllib.urlopen on main thread.
- **Tight coupling between GUI and business logic:** GUI tabs should only know about data interfaces (PositionTracker, OrderManager), not internal Kiwoom API details.
- **Recreating CandlestickItem on every tick:** Use set_data() to update existing item. Regenerate QPicture only when needed (on new candle, not on every tick).
- **Storing Discord webhook URL in config.json:** Must go in .env per Phase 1 convention for sensitive data.
- **Notification blocking trade logic:** All notification sends must be fire-and-forget with try/except. Never let notification failure propagate.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Real-time chart rendering | Custom QPainter canvas | pyqtgraph PlotWidget + custom CandlestickItem | pyqtgraph handles axis scaling, viewbox, mouse interaction, cross-hair, zoom/pan |
| Indicator math | GUI-layer calculations | Existing indicators.py classes | 7 indicator classes already built and tested in Phase 3 |
| Order state tracking | GUI-level order state | OrderManager.get_active_orders() | State machine already handles all transitions |
| Log rotation | Custom file rotation | loguru with existing multi-sink setup | Phase 1 configured daily rotation + retention |
| Config serialization | Custom format | json.dump to config.json | Settings class already handles load/save |
| Form validation | Manual string parsing | QIntValidator, QDoubleValidator | Qt built-in validators prevent invalid input at widget level |

**Key insight:** Phase 4 is primarily a UI layer over existing business logic. Almost all data sources and processing logic exist from Phases 1-3. The GUI should be a thin presentation layer that subscribes to existing signals and reads from existing managers.

## Common Pitfalls

### Pitfall 1: pyqtgraph Thread Safety
**What goes wrong:** Updating pyqtgraph widgets from non-GUI threads causes crashes or silent corruption.
**Why it happens:** pyqtgraph (like all Qt widgets) is not thread-safe. Data arrives via Kiwoom callbacks which may be on different threads.
**How to avoid:** All chart updates MUST go through pyqtSignal. CandleAggregator already uses callbacks, but ensure the callback -> GUI update path uses signal/slot crossing thread boundaries.
**Warning signs:** Random segfaults, blank chart areas, "QObject::connect: cannot queue arguments" warnings.

### Pitfall 2: QPicture Regeneration Performance
**What goes wrong:** Regenerating the entire candlestick QPicture on every new candle causes lag when history grows large.
**Why it happens:** QPainter iterates all candles in generatePicture().
**How to avoid:** Keep a sliding window of visible candles (e.g., last 120 candles for 2-hour view). Only regenerate QPicture for the visible window. Use viewRange changes to trigger window updates.
**Warning signs:** Dashboard becoming sluggish after 2+ hours of trading.

### Pitfall 3: Config.json Write Conflicts
**What goes wrong:** GUI writes config.json while another component reads it, causing JSON decode errors.
**Why it happens:** No file locking on config.json; Settings._load_config reads at startup.
**How to avoid:** Use Settings object as single source of truth. GUI modifies Settings._config dict in memory, then Settings handles writing. Add a `save()` method to Settings class.
**Warning signs:** "JSONDecodeError" in logs after strategy save.

### Pitfall 4: Discord Rate Limiting
**What goes wrong:** Rapid trade signals flood Discord webhook, hitting 30 requests/minute limit.
**Why it happens:** Multiple strategy signals can fire in quick succession during volatile markets.
**How to avoid:** Implement a simple queue with rate limiting (minimum 2-second interval between sends). Drop or batch messages if queue exceeds threshold.
**Warning signs:** HTTP 429 responses from Discord API.

### Pitfall 5: Toast Notification Stacking
**What goes wrong:** Multiple toasts overlap in the same position, becoming unreadable.
**Why it happens:** Multiple events fire within the toast display duration.
**How to avoid:** Track active toasts and offset Y position. New toast appears above existing ones. Remove from stack on dismiss.
**Warning signs:** Overlapping text blobs in bottom-right corner.

### Pitfall 6: Strategy Validation Edge Cases
**What goes wrong:** User creates strategy with invalid operator/indicator combos or empty conditions.
**Why it happens:** Free-form strategy builder allows arbitrary combinations.
**How to avoid:** Validate before save: at least one entry condition, at least one exit condition, indicator type exists in INDICATOR_CLASSES, operator exists in ConditionEngine's operator map. Show validation errors in GUI before allowing save.
**Warning signs:** StrategyManager crashes or silently ignores strategies on reload.

## Code Examples

### Discord Webhook Embed (Buy Trade)
```python
# Source: Discord API Embed Object documentation
def build_trade_embed(trade_data: dict, side: str) -> dict:
    """Build Discord embed for trade notification."""
    color = 0x26A69A if side == "BUY" else 0xEF5350  # green / red
    return {
        "embeds": [{
            "title": f"{'매수' if side == 'BUY' else '매도'} 체결",
            "color": color,
            "fields": [
                {"name": "종목코드", "value": trade_data["code"], "inline": True},
                {"name": "가격", "value": f"{trade_data['price']:,}원", "inline": True},
                {"name": "수량", "value": str(trade_data["qty"]), "inline": True},
                {"name": "전략", "value": trade_data["strategy"], "inline": True},
                {"name": "수익률", "value": f"{trade_data.get('pnl_pct', 0):.2f}%", "inline": True},
            ],
            "timestamp": trade_data["timestamp"],
        }]
    }
```

### Chart Tab with Linked Sub-Charts
```python
# Source: pyqtgraph documentation - linked views
import pyqtgraph as pg

class ChartTab(QWidget):
    def _setup_charts(self):
        layout = pg.GraphicsLayoutWidget()

        # Main price chart (row 0)
        self.price_plot = layout.addPlot(row=0, col=0)
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)

        # RSI sub-chart (row 1, linked X axis)
        self.rsi_plot = layout.addPlot(row=1, col=0)
        self.rsi_plot.setXLink(self.price_plot)
        self.rsi_plot.setMaximumHeight(120)

        # MACD sub-chart (row 2, linked X axis)
        self.macd_plot = layout.addPlot(row=2, col=0)
        self.macd_plot.setXLink(self.price_plot)
        self.macd_plot.setMaximumHeight(120)
```

### Strategy Form Builder
```python
# Pattern for dynamic condition rows
OPERATORS = ["gt", "lt", "gte", "lte", "cross_above", "cross_below"]
INDICATOR_TYPES = ["sma", "ema", "rsi", "macd", "bollinger", "vwap", "obv"]

def _build_condition_row(self) -> QHBoxLayout:
    row = QHBoxLayout()
    indicator_combo = QComboBox()
    indicator_combo.addItems(INDICATOR_TYPES)
    operator_combo = QComboBox()
    operator_combo.addItems(OPERATORS)
    value_input = QLineEdit()
    value_input.setValidator(QDoubleValidator())
    row.addWidget(indicator_combo)
    row.addWidget(operator_combo)
    row.addWidget(value_input)
    return row
```

### Config Notification Section Schema
```python
# To be added to Settings._default_config()
"notification": {
    "gui_popup_enabled": True,
    "log_enabled": True,
    "discord_enabled": False,
    "discord_rate_limit_sec": 2,
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| matplotlib for finance charts | pyqtgraph for real-time; mplfinance for static | 2020+ | pyqtgraph 10-100x faster for live updates |
| QMessageBox for notifications | Toast/snackbar overlay widgets | 2019+ | Non-blocking, better UX for trading apps |
| discord.py bot for webhooks | Raw HTTP POST to webhook URL | Always available | No bot token needed, simpler for one-way notifications |
| pyqtgraph QPicture full redraw | Incremental update with sliding window | Best practice | Prevents performance degradation over time |

**Deprecated/outdated:**
- pyqtgraph < 0.12: Missing important bug fixes for PyQt5 compatibility
- QDesktopWidget: Deprecated in Qt5.15; use QScreen for positioning calculations

## Open Questions

1. **Window Minimum Size**
   - What we know: Decision says "fixed minimum size, resizable"
   - What's unclear: Exact pixel dimensions depend on tab content complexity
   - Recommendation: Start with 1200x800 (common for trading dashboards). Adjust during implementation.

2. **Chart X-axis Visible Range**
   - What we know: Candlestick chart with live updates
   - What's unclear: How many candles to show by default, scroll/zoom behavior
   - Recommendation: Default 120 candles (2 hours of 1-min data). Mouse wheel zoom. Drag to scroll. Auto-scroll when at right edge (latest data).

3. **pyqtgraph on macOS Development**
   - What we know: Project uses try/except PyQt5 fallback pattern for macOS dev
   - What's unclear: pyqtgraph rendering may differ on macOS vs Windows
   - Recommendation: Apply same try/except import pattern for gui/ modules. Tests mock GUI components.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | tests/conftest.py (existing shared fixtures) |
| Quick run command | `pytest tests/ -x -q --tb=short` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUI-01 | Dashboard data binding (positions, orders, P&L, status) | unit | `pytest tests/test_dashboard_tab.py -x` | Wave 0 |
| GUI-02 | CandlestickItem set_data + indicator overlay data | unit | `pytest tests/test_chart_widgets.py -x` | Wave 0 |
| GUI-03 | Strategy form serialize/deserialize + config save/reload | unit | `pytest tests/test_strategy_tab.py -x` | Wave 0 |
| NOTI-01 | ToastWidget creation and auto-dismiss timer | unit | `pytest tests/test_toast_widget.py -x` | Wave 0 |
| NOTI-02 | Notification dispatched to loguru trade sink | unit | `pytest tests/test_notifier.py -x` | Wave 0 |
| NOTI-03 | Discord embed payload construction + error handling | unit | `pytest tests/test_discord_sender.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q --tb=short`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dashboard_tab.py` -- covers GUI-01 (data binding, not actual rendering)
- [ ] `tests/test_chart_widgets.py` -- covers GUI-02 (CandlestickItem data, indicator plot data)
- [ ] `tests/test_strategy_tab.py` -- covers GUI-03 (strategy dict serialization, validation)
- [ ] `tests/test_toast_widget.py` -- covers NOTI-01 (widget creation, timer behavior)
- [ ] `tests/test_notifier.py` -- covers NOTI-02 (dispatch routing, log sink verification)
- [ ] `tests/test_discord_sender.py` -- covers NOTI-03 (embed construction, error handling)
- [ ] pyqtgraph install: `pip install pyqtgraph==0.13.7 numpy`

**Note:** GUI widget tests should test data transformation and signal wiring logic, not visual rendering. Use MagicMock for QWidget internals where PyQt5 is unavailable (macOS dev pattern).

## Sources

### Primary (HIGH confidence)
- pyqtgraph examples/customGraphicsItem.py -- CandlestickItem canonical pattern (verified via GitHub raw source)
- pyqtgraph 0.13.7 on PyPI -- version compatibility with PyQt5.15
- Discord API Embed Object documentation -- webhook payload structure
- Existing codebase: PositionTracker, OrderManager, CandleAggregator, StrategyManager, indicators.py, Settings, loguru setup

### Secondary (MEDIUM confidence)
- pyqt-toast-notification library (pyqttoast) -- referenced for API design patterns, but we build custom to avoid dependency
- Discord webhook gists -- verified payload format matches official docs

### Tertiary (LOW confidence)
- None. All findings verified against primary sources or existing codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pyqtgraph is the established choice for PyQt5 real-time charting, all other libraries already in project
- Architecture: HIGH -- follows established project patterns (pyqtSignal, config.json, .env, try/except fallback)
- Pitfalls: HIGH -- thread safety and QPicture performance are well-documented pyqtgraph concerns; Discord rate limiting is documented in Discord API docs
- Code examples: HIGH -- CandlestickItem from canonical pyqtgraph example; Discord embed from official API format

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable libraries, no rapid-changing APIs)
