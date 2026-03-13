"""End-to-end integration tests for the full trading pipeline.

Tests the complete flow: tick -> CandleAggregator -> StrategyManager -> PaperTrader
using real component instances (no mocks except for OrderManager/RiskManager).
"""

import datetime as dt
from datetime import datetime, timedelta

import pytest

from kiwoom_trader.config.constants import MarketState
from kiwoom_trader.core.candle_aggregator import CandleAggregator
from kiwoom_trader.core.condition_engine import ConditionEngine
from kiwoom_trader.core.indicators import RSIIndicator, VWAPIndicator
from kiwoom_trader.core.market_hours import MarketHoursManager
from kiwoom_trader.core.models import Candle, RiskConfig, Signal
from kiwoom_trader.core.paper_trader import PaperTrader
from kiwoom_trader.core.strategy_manager import StrategyManager


# --- Strategy configs matching Settings defaults ---

RSI_STRATEGY_CONFIG = {
    "name": "RSI_REVERSAL",
    "enabled": True,
    "priority": 10,
    "cooldown_sec": 300,
    "indicators": {
        "rsi": {"type": "rsi", "period": 14},
    },
    "entry_rule": {
        "logic": "AND",
        "conditions": [
            {"indicator": "rsi", "operator": "lt", "value": 30.0},
        ],
    },
    "exit_rule": {
        "logic": "AND",
        "conditions": [
            {"indicator": "rsi", "operator": "gt", "value": 70.0},
        ],
    },
}

MA_STRATEGY_CONFIG = {
    "name": "MA_CROSSOVER",
    "enabled": True,
    "priority": 20,
    "cooldown_sec": 300,
    "indicators": {
        "ema_short": {"type": "ema", "period": 5},
        "ema_long": {"type": "ema", "period": 20},
    },
    "entry_rule": {
        "logic": "AND",
        "conditions": [
            {"indicator": "ema_short", "operator": "cross_above", "value": 0.0},
        ],
    },
    "exit_rule": {
        "logic": "AND",
        "conditions": [
            {"indicator": "ema_short", "operator": "cross_below", "value": 0.0},
        ],
    },
}


def _make_config(strategies=None, mode="paper", watchlist=None):
    """Build strategy config dict."""
    if strategies is None:
        strategies = [RSI_STRATEGY_CONFIG]
    if watchlist is None:
        watchlist = {"005930": [s["name"] for s in strategies]}
    return {
        "mode": mode,
        "strategies": strategies,
        "watchlist_strategies": watchlist,
        "total_capital": 10_000_000,
    }


def _make_candle(code: str, close: int, volume: int = 1000,
                 ts: datetime | None = None) -> Candle:
    """Helper to create a Candle with sensible defaults."""
    if ts is None:
        ts = datetime(2026, 3, 14, 10, 0, 0)
    return Candle(
        code=code, open=close, high=close + 10,
        low=max(close - 10, 1), close=close, volume=volume, timestamp=ts,
    )


def _feed_rsi_candles(strategy_manager, code: str, prices: list[int],
                      start_ts: datetime) -> list[Signal]:
    """Feed a series of candles and collect all signals."""
    all_signals = []
    for i, price in enumerate(prices):
        ts = start_ts + timedelta(minutes=i)
        candle = _make_candle(code, price, ts=ts)
        signals = strategy_manager.on_candle_complete(code, candle)
        all_signals.extend(signals)
    return all_signals


class TestFullPipelinePaperMode:
    """Test complete pipeline: CandleAggregator -> StrategyManager -> PaperTrader."""

    def test_rsi_buy_then_sell_with_csv(self, tmp_path):
        """Simulated tick sequence flows through full pipeline producing BUY then SELL in CSV."""
        csv_path = str(tmp_path / "trades.csv")
        config = _make_config(strategies=[RSI_STRATEGY_CONFIG])

        condition_engine = ConditionEngine()
        paper_trader = PaperTrader(csv_path=csv_path, initial_capital=10_000_000)
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=config,
        )
        strategy_manager.paper_trader = paper_trader

        # Wire CandleAggregator -> StrategyManager (2-arg direct match)
        candle_aggregator = CandleAggregator(interval_minutes=1)
        candle_aggregator.register_callback(strategy_manager.on_candle_complete)

        code = "005930"
        base_ts = datetime(2026, 3, 14, 10, 0, 0)

        # Phase 1: Warmup RSI with 14 stable candles (RSI starts at ~50)
        warmup_prices = [50000] * 14
        _feed_rsi_candles(strategy_manager, code, warmup_prices, base_ts)

        # Phase 2: Drive RSI below 30 with consecutive declining candles
        declining_prices = [49000, 48000, 47000, 46000, 45000, 44000, 43000, 42000, 41000, 40000]
        buy_signals = _feed_rsi_candles(
            strategy_manager, code, declining_prices,
            base_ts + timedelta(minutes=14),
        )

        # Should have at least one BUY signal
        buy_sigs = [s for s in buy_signals if s.side == "BUY"]
        assert len(buy_sigs) > 0, "Expected at least one BUY signal from RSI < 30"

        # Verify PaperTrader recorded the BUY
        assert code in paper_trader.positions
        assert paper_trader.positions[code]["qty"] > 0

        # Phase 3: Drive RSI above 70 with consecutive rising candles
        rising_prices = [45000, 50000, 55000, 60000, 65000, 70000, 75000, 80000, 85000, 90000]
        sell_signals = _feed_rsi_candles(
            strategy_manager, code, rising_prices,
            base_ts + timedelta(minutes=24 + 300),  # offset past cooldown
        )

        # Should have at least one SELL signal
        sell_sigs = [s for s in sell_signals if s.side == "SELL"]
        assert len(sell_sigs) > 0, "Expected at least one SELL signal from RSI > 70"

        # Verify PaperTrader closed the position
        assert code not in paper_trader.positions or paper_trader.positions.get(code, {}).get("qty", 0) == 0

        # Verify CSV has trade records
        with open(csv_path) as f:
            lines = f.readlines()
        # Header + at least 2 trades (BUY + SELL)
        assert len(lines) >= 3, f"Expected at least 3 lines in CSV, got {len(lines)}"

        # Verify P&L is positive (bought low, sold high)
        summary = paper_trader.get_summary()
        assert summary["total_pnl"] > 0


class TestMACrossoverSignal:
    """Test MA crossover strategy generates signals on EMA cross."""

    def test_ema_cross_above_generates_buy(self):
        """Feed enough candles for EMA(5) to cross above EMA(20) -> BUY signal."""
        config = _make_config(strategies=[MA_STRATEGY_CONFIG])
        condition_engine = ConditionEngine()
        paper_trader = PaperTrader(csv_path="/dev/null", initial_capital=10_000_000)
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=config,
        )
        strategy_manager.paper_trader = paper_trader

        code = "005930"
        base_ts = datetime(2026, 3, 14, 10, 0, 0)

        # Feed 20 candles at low price to initialize both EMAs (short below long eventually)
        low_prices = [10000] * 20
        _feed_rsi_candles(strategy_manager, code, low_prices, base_ts)

        # Now feed sharply rising prices so short EMA(5) crosses above long EMA(20)
        rising_prices = [12000, 14000, 16000, 18000, 20000, 22000, 24000, 26000, 28000, 30000]
        signals = _feed_rsi_candles(
            strategy_manager, code, rising_prices,
            base_ts + timedelta(minutes=20),
        )

        buy_sigs = [s for s in signals if s.side == "BUY"]
        assert len(buy_sigs) > 0, "Expected BUY signal when short EMA crosses above long EMA"


class TestCooldownPreventsRapidSignals:
    """Test that cooldown blocks repeated signals within cooldown window."""

    def test_cooldown_blocks_second_signal(self):
        """Trigger RSI buy, then immediately provide another buy condition -> blocked."""
        config = _make_config(strategies=[RSI_STRATEGY_CONFIG])
        condition_engine = ConditionEngine()
        paper_trader = PaperTrader(csv_path="/dev/null", initial_capital=10_000_000)
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=config,
        )
        strategy_manager.paper_trader = paper_trader

        code = "005930"
        base_ts = datetime(2026, 3, 14, 10, 0, 0)

        # Warmup + drive RSI below 30
        warmup_prices = [50000] * 14
        _feed_rsi_candles(strategy_manager, code, warmup_prices, base_ts)

        declining_prices = [49000, 48000, 47000, 46000, 45000, 44000, 43000, 42000, 41000, 40000]
        first_signals = _feed_rsi_candles(
            strategy_manager, code, declining_prices,
            base_ts + timedelta(minutes=14),
        )

        first_buys = [s for s in first_signals if s.side == "BUY"]
        assert len(first_buys) > 0, "First BUY should succeed"

        # Feed more declining candles within cooldown window (300s = 5 minutes)
        # First buy was around minute 14, so minute 15-17 is within cooldown
        more_declining = [39000, 38000, 37000]
        first_buy_ts = first_buys[0].timestamp
        second_signals = _feed_rsi_candles(
            strategy_manager, code, more_declining,
            first_buy_ts + timedelta(seconds=60),  # 60s after first buy, well within 300s cooldown
        )

        second_buys = [s for s in second_signals if s.side == "BUY"]
        assert len(second_buys) == 0, "Second BUY should be blocked by cooldown"


class TestDisabledStrategyNoSignal:
    """Test that disabled strategies produce no signals."""

    def test_disabled_strategy_ignored(self):
        """Strategy with enabled=False produces no signal even with triggering data."""
        disabled_config = {**RSI_STRATEGY_CONFIG, "enabled": False}
        config = _make_config(strategies=[disabled_config])
        condition_engine = ConditionEngine()
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=config,
        )

        code = "005930"
        base_ts = datetime(2026, 3, 14, 10, 0, 0)

        # Warmup + declining prices that would trigger RSI < 30
        warmup_prices = [50000] * 14
        declining_prices = [49000, 48000, 47000, 46000, 45000, 44000, 43000, 42000, 41000, 40000]
        all_prices = warmup_prices + declining_prices

        signals = _feed_rsi_candles(strategy_manager, code, all_prices, base_ts)
        assert len(signals) == 0, "Disabled strategy should produce no signals"


class TestMultipleStrategiesPriority:
    """Test that when multiple strategies trigger, highest priority wins."""

    def test_highest_priority_wins(self):
        """Two strategies both trigger BUY for same code -> only highest priority executes."""
        # Create two RSI strategies with different priorities
        low_priority = {
            **RSI_STRATEGY_CONFIG,
            "name": "RSI_LOW",
            "priority": 5,
        }
        high_priority = {
            **RSI_STRATEGY_CONFIG,
            "name": "RSI_HIGH",
            "priority": 50,
        }
        config = _make_config(
            strategies=[low_priority, high_priority],
            watchlist={"005930": ["RSI_LOW", "RSI_HIGH"]},
        )

        condition_engine = ConditionEngine()
        paper_trader = PaperTrader(csv_path="/dev/null", initial_capital=10_000_000)
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=config,
        )
        strategy_manager.paper_trader = paper_trader

        code = "005930"
        base_ts = datetime(2026, 3, 14, 10, 0, 0)

        # Warmup + declining to trigger both strategies
        warmup_prices = [50000] * 14
        declining_prices = [49000, 48000, 47000, 46000, 45000, 44000, 43000, 42000, 41000, 40000]
        all_prices = warmup_prices + declining_prices

        signals = _feed_rsi_candles(strategy_manager, code, all_prices, base_ts)

        buy_sigs = [s for s in signals if s.side == "BUY"]
        # Only one BUY signal should survive conflict resolution per candle
        # The highest priority (50) should win
        if buy_sigs:
            assert buy_sigs[0].strategy_name == "RSI_HIGH"
            assert buy_sigs[0].priority == 50


class TestCandleAggregatorStrategyManagerWiring:
    """Test that CandleAggregator.register_callback works with StrategyManager.on_candle_complete."""

    def test_2arg_callback_wiring(self):
        """CandleAggregator callback(code, candle) matches StrategyManager.on_candle_complete(code, candle)."""
        config = _make_config(strategies=[RSI_STRATEGY_CONFIG])
        condition_engine = ConditionEngine()
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=config,
        )

        candle_aggregator = CandleAggregator(interval_minutes=1)
        candle_aggregator.register_callback(strategy_manager.on_candle_complete)

        # Verify the callback was registered
        assert len(candle_aggregator._callbacks) == 1
        assert candle_aggregator._callbacks[0] == strategy_manager.on_candle_complete


# --- VWAP strategy config for reset integration test ---

VWAP_STRATEGY_CONFIG = {
    "name": "VWAP_BOUNCE",
    "enabled": True,
    "priority": 15,
    "cooldown_sec": 300,
    "indicators": {
        "vwap": {"type": "vwap"},
    },
    "entry_rule": {
        "logic": "AND",
        "conditions": [
            {"indicator": "price", "operator": "lt", "value": 999999.0},
        ],
    },
    "exit_rule": {
        "logic": "AND",
        "conditions": [
            {"indicator": "price", "operator": "gt", "value": 999999.0},
        ],
    },
}


class TestVWAPAndCooldownResetOnTradingStart:
    """Integration test: VWAP and cooldown reset when MarketHoursManager transitions to TRADING."""

    def test_vwap_and_cooldown_reset_on_trading_start(self):
        """Full flow: accumulate VWAP state + cooldowns, transition to TRADING, verify both reset."""
        risk_config = RiskConfig()

        # Start in MARKET_OPEN_BUFFER (09:02)
        current_time = [dt.time(9, 2)]

        def time_func():
            return current_time[0]

        market_hours = MarketHoursManager(risk_config, time_func=time_func)

        # Create strategy with VWAP indicator
        config = _make_config(
            strategies=[VWAP_STRATEGY_CONFIG],
            watchlist={"005930": ["VWAP_BOUNCE"]},
        )
        condition_engine = ConditionEngine()
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=config,
        )
        paper_trader = PaperTrader(csv_path="/dev/null", initial_capital=10_000_000)
        strategy_manager.paper_trader = paper_trader

        # Wire the state callback (same as main.py does)
        def _on_market_state_changed(old_state, new_state):
            if new_state == MarketState.TRADING:
                strategy_manager.reset_vwap()
                strategy_manager.reset_daily()

        market_hours.register_state_callback(_on_market_state_changed)

        # Feed candles to accumulate VWAP state and cooldown entries
        code = "005930"
        base_ts = datetime(2026, 3, 14, 9, 2, 0)
        for i in range(5):
            candle = _make_candle(code, 50000 + i * 100, volume=1000, ts=base_ts + timedelta(minutes=i))
            strategy_manager.on_candle_complete(code, candle)

        # Verify VWAP has accumulated state
        key = (code, "VWAP_BOUNCE")
        indicators = strategy_manager._indicators.get(key, {})
        vwap_instance = indicators.get("vwap")
        assert vwap_instance is not None, "VWAP indicator should be initialized"
        assert vwap_instance._cum_vol > 0, "VWAP should have accumulated volume"
        assert vwap_instance._cum_pv > 0, "VWAP should have accumulated price*volume"

        # Add a cooldown entry
        strategy_manager._cooldowns[("005930", "BUY")] = base_ts
        assert len(strategy_manager._cooldowns) > 0

        # Initialize state tracking (first poll)
        market_hours.check_state_transition()

        # Transition to TRADING (09:05)
        current_time[0] = dt.time(9, 5)
        result = market_hours.check_state_transition()

        # Verify transition detected
        assert result is not None
        assert result == (MarketState.MARKET_OPEN_BUFFER, MarketState.TRADING)

        # Verify VWAP reset: cumulative values should be 0
        assert vwap_instance._cum_pv == 0.0, "VWAP cum_pv should be reset"
        assert vwap_instance._cum_vol == 0, "VWAP cum_vol should be reset"

        # Verify cooldowns reset: dict should be empty
        assert len(strategy_manager._cooldowns) == 0, "Cooldowns should be cleared"
