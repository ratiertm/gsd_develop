"""Tests for StrategyManager - strategy loading, signal evaluation, cooldown, routing."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kiwoom_trader.core.condition_engine import ConditionEngine
from kiwoom_trader.core.models import Candle, Signal
from kiwoom_trader.core.strategy_manager import StrategyManager


def _make_candle(code: str, close: int, volume: int = 1000, high: int = 0,
                 low: int = 0, open_: int = 0, ts: datetime | None = None) -> Candle:
    """Helper to create a Candle with sensible defaults."""
    if ts is None:
        ts = datetime(2026, 3, 14, 10, 0, 0)
    if high == 0:
        high = close + 10
    if low == 0:
        low = max(close - 10, 1)
    if open_ == 0:
        open_ = close
    return Candle(
        code=code, open=open_, high=high, low=low,
        close=close, volume=volume, timestamp=ts,
    )


RSI_STRATEGY_CONFIG = {
    "name": "RSI_REVERSAL",
    "enabled": True,
    "priority": 10,
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
    "cooldown_sec": 300,
}

MA_STRATEGY_CONFIG = {
    "name": "MA_CROSSOVER",
    "enabled": True,
    "priority": 20,
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
    "cooldown_sec": 300,
}


def _make_config(strategies=None, mode="paper", watchlist=None):
    if strategies is None:
        strategies = [RSI_STRATEGY_CONFIG]
    if watchlist is None:
        watchlist = {"005930": [s["name"] for s in strategies]}
    return {
        "mode": mode,
        "strategies": strategies,
        "watchlist_strategies": watchlist,
    }


@pytest.fixture
def engine():
    return ConditionEngine()


@pytest.fixture
def mock_risk_manager():
    rm = MagicMock()
    rm.validate_order.return_value = (True, "OK")
    return rm


@pytest.fixture
def mock_order_manager():
    om = MagicMock()
    return om


class TestStrategyLoading:
    """Test strategy config parsing."""

    def test_load_rsi_preset(self, engine, mock_risk_manager, mock_order_manager):
        config = _make_config([RSI_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)
        assert len(sm.strategies) == 1
        strat = sm.strategies[0]
        assert strat.name == "RSI_REVERSAL"
        assert strat.priority == 10
        assert strat.enabled is True

    def test_load_ma_preset(self, engine, mock_risk_manager, mock_order_manager):
        config = _make_config([MA_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)
        assert len(sm.strategies) == 1
        strat = sm.strategies[0]
        assert strat.name == "MA_CROSSOVER"
        assert strat.priority == 20

    def test_disabled_strategy_skipped(self, engine, mock_risk_manager, mock_order_manager):
        disabled = {**RSI_STRATEGY_CONFIG, "enabled": False}
        config = _make_config([disabled])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)
        # Feed candles; no signals should be emitted
        signals = sm.on_candle_complete("005930", _make_candle("005930", 10000))
        assert signals == []


class TestIndicatorManagement:
    """Test indicator instance creation and management."""

    def test_indicator_instances_created(self, engine, mock_risk_manager, mock_order_manager):
        config = _make_config([RSI_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)
        candle = _make_candle("005930", 10000)
        sm.on_candle_complete("005930", candle)
        # Indicator instances should exist for (005930, RSI_REVERSAL)
        key = ("005930", "RSI_REVERSAL")
        assert key in sm._indicators
        assert "rsi" in sm._indicators[key]

    def test_warmup_no_signal(self, engine, mock_risk_manager, mock_order_manager):
        """During indicator warmup (None values), no signals emitted."""
        config = _make_config([RSI_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)
        # RSI needs 15 candles (period=14 + 1 for first change). Feed only a few.
        for i in range(5):
            signals = sm.on_candle_complete("005930", _make_candle("005930", 10000 + i * 10))
            assert signals == [], f"Signal emitted during warmup at candle {i}"


class TestSignalEvaluation:
    """Test signal generation from strategy evaluation."""

    def test_evaluate_rsi_buy_signal(self, engine, mock_risk_manager, mock_order_manager):
        """Feed enough candles with declining prices to push RSI<30, verify BUY signal."""
        config = _make_config([RSI_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        # Feed 15 declining candles to get RSI well below 30
        signals = []
        for i in range(20):
            price = 10000 - i * 100  # Declining prices
            candle = _make_candle("005930", max(price, 100))
            result = sm.on_candle_complete("005930", candle)
            signals.extend(result)

        buy_signals = [s for s in signals if s.side == "BUY"]
        assert len(buy_signals) > 0, "Expected at least one BUY signal from RSI < 30"
        assert buy_signals[0].strategy_name == "RSI_REVERSAL"

    def test_evaluate_rsi_sell_signal(self, engine, mock_risk_manager, mock_order_manager):
        """Feed enough candles with rising prices to push RSI>70, verify SELL signal."""
        config = _make_config([RSI_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        # Feed 20 rising candles
        signals = []
        for i in range(20):
            price = 10000 + i * 100
            candle = _make_candle("005930", price)
            result = sm.on_candle_complete("005930", candle)
            signals.extend(result)

        sell_signals = [s for s in signals if s.side == "SELL"]
        assert len(sell_signals) > 0, "Expected at least one SELL signal from RSI > 70"
        assert sell_signals[0].strategy_name == "RSI_REVERSAL"

    def test_evaluate_ma_crossover_buy(self, engine, mock_risk_manager, mock_order_manager):
        """Feed candles where short EMA crosses above long EMA, verify BUY signal."""
        config = _make_config(
            [MA_STRATEGY_CONFIG],
            watchlist={"005930": ["MA_CROSSOVER"]},
        )
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        signals = []
        # First 25 declining candles (long EMA above short EMA)
        for i in range(25):
            price = 10000 - i * 50
            candle = _make_candle("005930", max(price, 100))
            result = sm.on_candle_complete("005930", candle)
            signals.extend(result)

        # Then sharp rise to push short EMA above long EMA
        for i in range(15):
            price = 8000 + i * 300
            candle = _make_candle("005930", price)
            result = sm.on_candle_complete("005930", candle)
            signals.extend(result)

        buy_signals = [s for s in signals if s.side == "BUY"]
        assert len(buy_signals) > 0, "Expected BUY signal from MA crossover"


class TestConflictResolution:
    """Test priority-based conflict resolution."""

    def test_priority_resolution(self, engine, mock_risk_manager, mock_order_manager):
        """Higher priority signal wins when multiple strategies trigger same direction."""
        # Both strategies assigned to same stock
        config = _make_config(
            [RSI_STRATEGY_CONFIG, MA_STRATEGY_CONFIG],
            watchlist={"005930": ["RSI_REVERSAL", "MA_CROSSOVER"]},
        )
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        # Create two conflicting signals manually and test resolution
        now = datetime.now()
        sig1 = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                      priority=10, price=10000, timestamp=now, reason="RSI<30")
        sig2 = Signal(code="005930", side="BUY", strategy_name="MA_CROSSOVER",
                      priority=20, price=10000, timestamp=now, reason="EMA cross")

        resolved = sm._resolve_conflicts([sig1, sig2])
        assert len(resolved) == 1
        assert resolved[0].strategy_name == "MA_CROSSOVER"  # Higher priority wins


class TestCooldown:
    """Test signal cooldown mechanism."""

    def test_cooldown_blocks_duplicate(self, engine, mock_risk_manager, mock_order_manager):
        config = _make_config([RSI_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        now = datetime(2026, 3, 14, 10, 0, 0)
        sig = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                     priority=10, price=10000, timestamp=now, reason="test")

        # First signal should pass
        assert sm._check_cooldown("005930", sig) is True
        sm._record_cooldown("005930", sig)

        # Second signal within cooldown window should be blocked
        sig2 = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                      priority=10, price=10000,
                      timestamp=datetime(2026, 3, 14, 10, 1, 0),
                      reason="test")
        assert sm._check_cooldown("005930", sig2) is False

    def test_cooldown_expires(self, engine, mock_risk_manager, mock_order_manager):
        config = _make_config([RSI_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        now = datetime(2026, 3, 14, 10, 0, 0)
        sig = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                     priority=10, price=10000, timestamp=now, reason="test")
        sm._record_cooldown("005930", sig)

        # Signal after cooldown_sec (300s = 5min) should pass
        sig2 = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                      priority=10, price=10000,
                      timestamp=datetime(2026, 3, 14, 10, 6, 0),
                      reason="test")
        assert sm._check_cooldown("005930", sig2) is True

    def test_cooldown_reset_daily(self, engine, mock_risk_manager, mock_order_manager):
        config = _make_config([RSI_STRATEGY_CONFIG])
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        now = datetime(2026, 3, 14, 10, 0, 0)
        sig = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                     priority=10, price=10000, timestamp=now, reason="test")
        sm._record_cooldown("005930", sig)

        sm.reset_daily()

        # After reset, should pass even within original cooldown window
        sig2 = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                      priority=10, price=10000,
                      timestamp=datetime(2026, 3, 14, 10, 1, 0),
                      reason="test")
        assert sm._check_cooldown("005930", sig2) is True


class TestRouting:
    """Test signal routing to PaperTrader or RiskManager."""

    def test_paper_mode_routes_to_paper_trader(self, engine, mock_risk_manager, mock_order_manager):
        config = _make_config([RSI_STRATEGY_CONFIG], mode="paper")
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)
        sm.paper_trader = MagicMock()

        now = datetime.now()
        sig = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                     priority=10, price=10000, timestamp=now, reason="test")
        sm._execute_signal(sig)

        sm.paper_trader.execute_signal.assert_called_once_with(sig)
        mock_risk_manager.validate_order.assert_not_called()

    def test_live_mode_routes_to_risk_manager(self, engine, mock_risk_manager, mock_order_manager):
        config = _make_config([RSI_STRATEGY_CONFIG], mode="live")
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        now = datetime.now()
        sig = Signal(code="005930", side="BUY", strategy_name="RSI_REVERSAL",
                     priority=10, price=10000, timestamp=now, reason="test")
        sm._execute_signal(sig)

        mock_risk_manager.validate_order.assert_called_once()
        mock_order_manager.submit_order.assert_called_once()


class TestVWAPReset:
    """Test VWAP indicator reset delegation."""

    def test_reset_vwap_delegates(self, engine, mock_risk_manager, mock_order_manager):
        """reset_vwap calls reset() on all VWAPIndicator instances."""
        from kiwoom_trader.core.indicators import VWAPIndicator

        config = _make_config([{
            "name": "VWAP_STRAT",
            "enabled": True,
            "priority": 5,
            "indicators": {"vwap": {"type": "vwap"}},
            "entry_rule": {"logic": "AND", "conditions": [
                {"indicator": "vwap", "operator": "gt", "value": 0},
            ]},
            "exit_rule": {"logic": "AND", "conditions": [
                {"indicator": "vwap", "operator": "lt", "value": 0},
            ]},
            "cooldown_sec": 300,
        }], watchlist={"005930": ["VWAP_STRAT"]})
        sm = StrategyManager(engine, mock_risk_manager, mock_order_manager, config)

        # Trigger indicator creation by feeding a candle
        candle = _make_candle("005930", 10000, volume=1000)
        sm.on_candle_complete("005930", candle)

        # Find the VWAP instance and mock it
        key = ("005930", "VWAP_STRAT")
        assert key in sm._indicators
        vwap_instance = sm._indicators[key]["vwap"]
        assert isinstance(vwap_instance, VWAPIndicator)

        # Replace with mock to track reset call
        mock_vwap = MagicMock(spec=VWAPIndicator)
        sm._indicators[key]["vwap"] = mock_vwap

        sm.reset_vwap()
        mock_vwap.reset.assert_called_once()
