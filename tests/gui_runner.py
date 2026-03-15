"""Mock GUI launcher for visual testing.

Launches the full MainWindow with rich sample data:
- Dashboard: 5 positions, pending/filled orders, P&L, logs
- Chart: 3 stocks with 120 candles each, trade markers, indicator overlays ON
- Strategy: 3 sample strategies pre-loaded

Usage:
    python -m tests.gui_runner
"""

import math
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from kiwoom_trader.config.settings import Settings
from kiwoom_trader.core.models import (
    Candle, Order, OrderSide, OrderState, Position, RiskConfig,
)
from kiwoom_trader.core.position_tracker import PositionTracker
from kiwoom_trader.gui.main_window import MainWindow

random.seed(42)

# ------------------------------------------------------------------ #
# Stock profiles for realistic price simulation
# ------------------------------------------------------------------ #

STOCKS = {
    "005930": {"name": "삼성전자", "base": 72000, "volatility": 600},
    "000660": {"name": "SK하이닉스", "base": 165000, "volatility": 2000},
    "035720": {"name": "카카오", "base": 52000, "volatility": 800},
    "005380": {"name": "현대차", "base": 238000, "volatility": 3000},
    "051910": {"name": "LG화학", "base": 380000, "volatility": 5000},
}

# ------------------------------------------------------------------ #
# Sample strategies
# ------------------------------------------------------------------ #

SAMPLE_STRATEGIES = [
    {
        "name": "MA_CROSS_20_60",
        "enabled": True,
        "priority": 10,
        "cooldown_sec": 300,
        "indicators": {
            "sma_short": {"type": "sma", "period": 20},
            "sma_long": {"type": "sma", "period": 60},
            "rsi": {"type": "rsi", "period": 14},
        },
        "entry_rule": {
            "logic": "AND",
            "conditions": [
                {"indicator": "sma_short", "operator": "cross_above", "value": 0},
                {"indicator": "rsi", "operator": "lt", "value": 70},
            ],
        },
        "exit_rule": {
            "logic": "OR",
            "conditions": [
                {"indicator": "sma_short", "operator": "cross_below", "value": 0},
                {"indicator": "rsi", "operator": "gt", "value": 80},
            ],
        },
    },
    {
        "name": "RSI_BOUNCE",
        "enabled": True,
        "priority": 20,
        "cooldown_sec": 600,
        "indicators": {
            "rsi": {"type": "rsi", "period": 14},
            "ema": {"type": "ema", "period": 20},
        },
        "entry_rule": {
            "logic": "AND",
            "conditions": [
                {"indicator": "rsi", "operator": "cross_above", "value": 30},
            ],
        },
        "exit_rule": {
            "logic": "OR",
            "conditions": [
                {"indicator": "rsi", "operator": "gt", "value": 70},
            ],
        },
    },
    {
        "name": "BOLLINGER_SQUEEZE",
        "enabled": False,
        "priority": 5,
        "cooldown_sec": 900,
        "indicators": {
            "bb": {"type": "bollinger", "period": 20},
            "obv": {"type": "obv", "period": 1},
        },
        "entry_rule": {
            "logic": "AND",
            "conditions": [
                {"indicator": "bb", "operator": "lt", "value": -2.0},
                {"indicator": "obv", "operator": "gt", "value": 0},
            ],
        },
        "exit_rule": {
            "logic": "AND",
            "conditions": [
                {"indicator": "bb", "operator": "gt", "value": 2.0},
            ],
        },
    },
]


# ------------------------------------------------------------------ #
# Candle generation with realistic patterns
# ------------------------------------------------------------------ #

def generate_candles(code: str, n: int = 120) -> list[Candle]:
    """Generate n realistic 1-minute candles with trend + noise."""
    profile = STOCKS[code]
    base = profile["base"]
    vol = profile["volatility"]
    candles = []
    base_time = datetime(2026, 3, 14, 9, 5)
    price = base

    # Create a sine-wave trend + random walk
    for i in range(n):
        trend = math.sin(i / 20) * vol * 0.5
        noise = random.gauss(0, vol * 0.3)
        price = max(price + trend * 0.02 + noise, base * 0.9)

        o = int(price)
        c = int(price + random.gauss(0, vol * 0.2))
        h = max(o, c) + random.randint(0, int(vol * 0.3))
        l = min(o, c) - random.randint(0, int(vol * 0.3))
        v = random.randint(500, 8000)

        candles.append(Candle(
            code=code,
            open=o, high=h, low=l, close=c, volume=v,
            timestamp=base_time + timedelta(minutes=i),
        ))
        price = c
    return candles


# ------------------------------------------------------------------ #
# Order generation
# ------------------------------------------------------------------ #

def generate_orders() -> list[Order]:
    """Generate sample pending + filled orders."""
    now = datetime.now()
    orders = [
        # Filled orders
        Order(
            code="005930", side=OrderSide.BUY, qty=10, price=72000,
            order_type=1, hoga_gb="00", state=OrderState.FILLED,
            order_no="ORD001", filled_qty=10, filled_price=72000,
            created_at=now - timedelta(minutes=45),
        ),
        Order(
            code="000660", side=OrderSide.BUY, qty=5, price=165000,
            order_type=1, hoga_gb="00", state=OrderState.FILLED,
            order_no="ORD002", filled_qty=5, filled_price=165000,
            created_at=now - timedelta(minutes=30),
        ),
        Order(
            code="035720", side=OrderSide.BUY, qty=20, price=52000,
            order_type=1, hoga_gb="00", state=OrderState.FILLED,
            order_no="ORD003", filled_qty=20, filled_price=52000,
            created_at=now - timedelta(minutes=20),
        ),
        Order(
            code="005930", side=OrderSide.SELL, qty=5, price=74500,
            order_type=2, hoga_gb="00", state=OrderState.FILLED,
            order_no="ORD004", filled_qty=5, filled_price=74500,
            created_at=now - timedelta(minutes=10),
        ),
        # Pending orders
        Order(
            code="005380", side=OrderSide.BUY, qty=3, price=237000,
            order_type=1, hoga_gb="00", state=OrderState.ACCEPTED,
            order_no="ORD005", filled_qty=0, filled_price=0,
            created_at=now - timedelta(minutes=5),
        ),
        Order(
            code="051910", side=OrderSide.BUY, qty=2, price=375000,
            order_type=1, hoga_gb="00", state=OrderState.SUBMITTED,
            order_no="ORD006", filled_qty=0, filled_price=0,
            created_at=now - timedelta(minutes=2),
        ),
        Order(
            code="035720", side=OrderSide.SELL, qty=10, price=55500,
            order_type=2, hoga_gb="00", state=OrderState.PARTIAL_FILL,
            order_no="ORD007", filled_qty=4, filled_price=55500,
            created_at=now - timedelta(minutes=1),
        ),
    ]
    return orders


# ------------------------------------------------------------------ #
# Main
# ------------------------------------------------------------------ #

def main():
    app = QApplication(sys.argv)
    settings = Settings()

    # Inject sample strategies into config
    settings._config["strategies"] = SAMPLE_STRATEGIES
    settings._config["watchlist"] = list(STOCKS.keys())
    settings._config["watchlist_strategies"] = {
        "005930": ["MA_CROSS_20_60", "RSI_BOUNCE"],
        "000660": ["MA_CROSS_20_60"],
        "035720": ["RSI_BOUNCE"],
        "005380": ["BOLLINGER_SQUEEZE"],
        "051910": [],
    }

    # Create MainWindow
    window = MainWindow(settings, on_strategy_reload=lambda: print("[HOT-SWAP] Strategy reload triggered"))
    window.setWindowTitle("KiwoomDayTrader [TEST MODE]")
    window.show()

    dashboard = window._dashboard_tab
    chart_tab = window._chart_tab
    strategy_tab = window._strategy_tab

    # ============================================================== #
    # 1. Dashboard: Positions
    # ============================================================== #
    risk_config = settings.risk_config
    tracker = PositionTracker(risk_config)

    tracker.add_position("005930", 10, 72000)
    tracker.add_position("000660", 5, 165000)
    tracker.add_position("035720", 20, 52000)
    tracker.add_position("005380", 3, 238000)
    tracker.add_position("051910", 2, 380000)

    # Simulate live prices
    tracker.update_price("005930", 74500)   # +3.47%
    tracker.update_price("000660", 160000)  # -3.03%
    tracker.update_price("035720", 55000)   # +5.77%
    tracker.update_price("005380", 241000)  # +1.26%
    tracker.update_price("051910", 372000)  # -2.11%

    tracker.record_realized_pnl(12500)  # From ORD004 partial sell

    positions = tracker.get_all_positions()
    total_invested = sum(p.avg_price * p.qty for p in positions.values())
    unrealized = sum(p.unrealized_pnl for p in positions.values())

    dashboard.update_positions(positions, total_invested)
    dashboard.update_pnl(
        daily_pnl=tracker.get_daily_pnl(),
        unrealized_pnl=unrealized,
        total_invested=total_invested,
    )
    dashboard.update_status(
        connected=True,
        market_state="TRADING",
        strategy_count=2,
        mode="paper",
    )

    # ============================================================== #
    # 2. Dashboard: Orders (pending + filled)
    # ============================================================== #
    orders = generate_orders()
    dashboard.update_orders(orders)

    # ============================================================== #
    # 3. Dashboard: Logs
    # ============================================================== #
    log_messages = [
        "=== KiwoomDayTrader started (TEST MODE) ===",
        "Phase 1 wired: KiwoomAPI, EventHandler, TRQueue, SessionManager",
        "Phase 2 wired: OrderManager, RiskManager, PositionTracker, MarketHours",
        "Phase 3 wired: CandleAggregator, ConditionEngine, StrategyManager, mode=paper",
        "Phase 4 wired: MainWindow, Dashboard, Chart, Strategy, Notifier",
        "Session connected to simulation server",
        "Market state: CLOSED → TRADING",
        "[MA_CROSS_20_60] BUY signal: 005930 @72,000 (SMA20 crossed above SMA60)",
        "[ORD001] 005930 BUY 10주 @72,000 접수",
        "[ORD001] 005930 BUY 10주 @72,000 체결 완료",
        "[RSI_BOUNCE] BUY signal: 035720 @52,000 (RSI crossed above 30)",
        "[ORD003] 035720 BUY 20주 @52,000 체결 완료",
        "RiskManager: 005930 take-profit approaching (+3.47%)",
        "[ORD004] 005930 SELL 5주 @74,500 체결 — 실현손익 +12,500원",
        "[ORD005] 005380 BUY 3주 @237,000 접수 대기중",
        "[ORD007] 035720 SELL 10주 중 4주 부분체결 @55,500",
        "Daily P&L: +73,500원 (실현: +12,500 / 평가: +61,000)",
    ]
    for msg in log_messages:
        dashboard.append_log(msg)

    # ============================================================== #
    # 4. Chart: Multi-stock candles + trade markers
    # ============================================================== #
    for code in STOCKS:
        candles = generate_candles(code, n=120)
        for candle in candles:
            chart_tab.on_new_candle(code, candle)

    # Trade markers on 005930
    chart_tab.add_trade_marker("005930", 15, 72000, "BUY")
    chart_tab.add_trade_marker("005930", 45, 74500, "SELL")
    chart_tab.add_trade_marker("005930", 70, 71800, "BUY")
    chart_tab.add_trade_marker("005930", 100, 73200, "SELL")

    # Trade markers on 035720
    chart_tab.add_trade_marker("035720", 20, 52000, "BUY")
    chart_tab.add_trade_marker("035720", 55, 55500, "SELL")

    # Trade markers on 000660
    chart_tab.add_trade_marker("000660", 10, 165000, "BUY")
    chart_tab.add_trade_marker("000660", 80, 160000, "SELL")

    # ============================================================== #
    # 5. Chart: Enable indicator overlays + sub-charts
    # ============================================================== #
    # Toggle SMA, EMA, Bollinger overlays ON
    for cb in chart_tab.findChildren(app.style().__class__.__bases__[0]):
        pass  # skip — use toggle_indicator directly

    chart_tab.toggle_indicator("sma", True)
    chart_tab.toggle_indicator("ema", True)
    chart_tab.toggle_indicator("bollinger", True)
    chart_tab.toggle_indicator("rsi", True)

    # Also check the checkboxes in the UI to match
    from PyQt5.QtWidgets import QCheckBox
    for cb in chart_tab.findChildren(QCheckBox):
        name = cb.text().lower()
        if name in ("sma", "ema", "bollinger", "rsi"):
            cb.setChecked(True)

    # Set initial watchlist selection to 005930
    if chart_tab._watchlist_widget and chart_tab._watchlist_widget.count() > 0:
        chart_tab._watchlist_widget.setCurrentRow(0)

    # ============================================================== #
    # 6. Strategy: Reload list
    # ============================================================== #
    strategy_tab._load_strategy_names()
    if strategy_tab._strategy_list.count() > 0:
        strategy_tab._strategy_list.setCurrentRow(0)

    # Reload watchlist table
    strategy_tab._load_watchlist()

    # ============================================================== #
    # Print summary
    # ============================================================== #
    print("\n" + "=" * 60)
    print("  KiwoomDayTrader [TEST MODE] - Rich Sample Data")
    print("=" * 60)
    print(f"  Positions:    {len(positions)} stocks")
    print(f"  Orders:       {len(orders)} (4 filled, 3 pending)")
    print(f"  Candles:      {len(STOCKS)} stocks × 120 candles")
    print(f"  Trade Markers: 8 total (BUY/SELL)")
    print(f"  Strategies:   {len(SAMPLE_STRATEGIES)} loaded")
    print(f"  Watchlist:    {len(STOCKS)} stocks assigned")
    print(f"  Overlays ON:  SMA, EMA, Bollinger, RSI")
    print("=" * 60)
    print("  Close the window to exit.\n")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
