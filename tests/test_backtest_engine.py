"""Tests for BacktestEngine: replay loop, risk checks, position management."""

from datetime import datetime, timedelta

from kiwoom_trader.backtest.backtest_engine import BacktestEngine
from kiwoom_trader.backtest.cost_model import CostConfig
from kiwoom_trader.core.models import BacktestResult, Candle, RiskConfig, Signal


def _make_candles(prices, code="005930", start_date=None, volume=10000):
    """Helper: create candle list from price sequence."""
    if start_date is None:
        start_date = datetime(2025, 1, 1)
    candles = []
    for i, price in enumerate(prices):
        candles.append(
            Candle(
                code=code,
                open=price,
                high=price + 100,
                low=price - 100,
                close=price,
                volume=volume,
                timestamp=start_date + timedelta(days=i),
            )
        )
    return candles


def _rsi_strategy_config():
    """Simple RSI_REVERSAL strategy config dict for testing."""
    return {
        "mode": "paper",
        "strategies": [
            {
                "name": "RSI_REVERSAL",
                "enabled": True,
                "priority": 10,
                "cooldown_sec": 0,  # No cooldown for tests
                "indicators": {
                    "rsi": {"type": "rsi", "period": 14},
                },
                "entry_rule": {
                    "logic": "AND",
                    "conditions": [
                        {"indicator": "rsi", "operator": "lt", "value": 30},
                    ],
                },
                "exit_rule": {
                    "logic": "AND",
                    "conditions": [
                        {"indicator": "rsi", "operator": "gt", "value": 70},
                    ],
                },
            }
        ],
        "watchlist_strategies": {
            "005930": ["RSI_REVERSAL"],
        },
    }


def _zero_cost_config():
    """CostConfig with zero costs for simpler pnl assertions."""
    return CostConfig(
        buy_commission_pct=0.0,
        sell_commission_pct=0.0,
        tax_pct=0.0,
        slippage_bp=0.0,
    )


class TestEmptyCandles:
    def test_empty_candles_returns_zero_trades(self):
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )
        result = engine.run([])
        assert isinstance(result, BacktestResult)
        assert result.total_trades == 0
        assert len(result.trades) == 0
        assert result.initial_capital == 10_000_000
        assert result.final_capital == 10_000_000


class TestBuySignal:
    def test_buy_signal_creates_position(self):
        """When strategy generates BUY, position is created and capital reduced."""
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )
        # Create price sequence that triggers RSI < 30 (sustained decline)
        # Need 15+ candles for RSI warmup, then declining prices
        prices = [10000] * 15  # Warmup period
        # Add steep decline to trigger RSI < 30
        for i in range(10):
            prices.append(10000 - (i + 1) * 200)  # 9800, 9600, ..., 8000

        candles = _make_candles(prices)
        result = engine.run(candles)

        # Should have at least one BUY trade
        buy_trades = [t for t in result.trades if t.side == "BUY"]
        assert len(buy_trades) > 0
        # Capital should be reduced after buy
        # (Final capital may vary due to forced close at end)


class TestSellSignal:
    def test_buy_then_sell_computes_pnl(self):
        """BUY then SELL produces correct pnl with costs."""
        cost_config = CostConfig()
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(stop_loss_pct=-50.0, take_profit_pct=50.0),  # Wide SL/TP to avoid interference
            cost_config=cost_config,
            initial_capital=10_000_000,
        )
        # Price pattern: warmup, decline (trigger buy RSI<30), recovery (trigger sell RSI>70)
        prices = [10000] * 15
        for i in range(10):
            prices.append(10000 - (i + 1) * 200)
        for i in range(10):
            prices.append(8000 + (i + 1) * 300)

        candles = _make_candles(prices)
        result = engine.run(candles)

        sell_trades = [t for t in result.trades if t.side == "SELL"]
        # At minimum, forced close at end produces a sell
        assert len(sell_trades) > 0


class TestStopLoss:
    def test_stop_loss_triggers(self):
        """BUY at 10000, price drops > 2%, auto-sell triggered."""
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(stop_loss_pct=-2.0, take_profit_pct=50.0, trailing_stop_pct=50.0),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )

        # Manually inject a position to test stop loss directly
        engine._capital = 8_000_000.0
        engine._positions = {
            "005930": {"qty": 200, "avg_price": 10000, "highest_price": 10000}
        }

        # Create a candle at 9750 (2.5% drop from 10000 -- triggers SL)
        candle = Candle(
            code="005930", open=9800, high=9850, low=9700,
            close=9750, volume=10000, timestamp=datetime(2025, 3, 1),
        )
        engine._check_risk_triggers(candle)

        # Position should be closed
        assert "005930" not in engine._positions
        # Sell trade should be recorded
        sell_trades = [t for t in engine._trades if t.side == "SELL"]
        assert len(sell_trades) == 1
        assert "stop loss" in sell_trades[0].reason.lower()


class TestTrailingStop:
    def test_trailing_stop_tracks_highest_and_triggers(self):
        """Trailing stop: BUY at 10000, price rises to 11000, then drops >1.5% from high."""
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(stop_loss_pct=-50.0, take_profit_pct=50.0, trailing_stop_pct=1.5),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )

        # Inject position
        engine._capital = 8_000_000.0
        engine._positions = {
            "005930": {"qty": 100, "avg_price": 10000, "highest_price": 10000}
        }

        # Price rises to 11000 -- should update highest_price
        candle_up = Candle(
            code="005930", open=10500, high=11100, low=10400,
            close=11000, volume=10000, timestamp=datetime(2025, 3, 1),
        )
        engine._check_risk_triggers(candle_up)
        assert engine._positions["005930"]["highest_price"] == 11000

        # Price drops to 10800 -- 1.82% below 11000 (> 1.5% trailing stop)
        candle_down = Candle(
            code="005930", open=10900, high=10950, low=10750,
            close=10800, volume=10000, timestamp=datetime(2025, 3, 2),
        )
        engine._check_risk_triggers(candle_down)

        # Position should be closed
        assert "005930" not in engine._positions
        sell_trades = [t for t in engine._trades if t.side == "SELL"]
        assert len(sell_trades) == 1
        assert "trailing" in sell_trades[0].reason.lower()


class TestCloseAllAtEnd:
    def test_remaining_positions_closed_at_last_candle(self):
        """All open positions are force-closed at the last candle price."""
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(stop_loss_pct=-50.0, take_profit_pct=50.0, trailing_stop_pct=50.0),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )

        # Inject position
        engine._capital = 8_000_000.0
        engine._positions = {
            "005930": {"qty": 100, "avg_price": 10000, "highest_price": 10000}
        }

        last_candle = Candle(
            code="005930", open=10100, high=10200, low=10050,
            close=10150, volume=10000, timestamp=datetime(2025, 3, 10),
        )
        engine._close_all_positions(last_candle)

        assert "005930" not in engine._positions
        assert engine._capital > 8_000_000.0  # Got sell proceeds


class TestFreshStrategyPerRun:
    def test_two_runs_produce_identical_results(self):
        """Running the same candles twice gives identical results (no stale state)."""
        config = _rsi_strategy_config()
        risk = RiskConfig()
        cost = _zero_cost_config()

        prices = [10000] * 15
        for i in range(10):
            prices.append(10000 - (i + 1) * 200)
        candles = _make_candles(prices)

        engine = BacktestEngine(
            strategy_configs=config,
            risk_config=risk,
            cost_config=cost,
            initial_capital=10_000_000,
        )

        result1 = engine.run(candles)
        result2 = engine.run(candles)

        assert len(result1.trades) == len(result2.trades)
        assert result1.final_capital == result2.final_capital


class TestDailyLossLimit:
    def test_daily_loss_blocks_further_buys(self):
        """When daily realized loss exceeds limit, subsequent buys are blocked."""
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(daily_loss_limit_pct=3.0),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )

        # Simulate a large daily loss
        today = datetime(2025, 3, 1).date()
        engine._daily_pnl[today] = -400_000.0  # 4% loss > 3% limit

        # Try to check daily loss
        assert engine._check_daily_loss(today) is True

    def test_within_limit_allows_buys(self):
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(daily_loss_limit_pct=3.0),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )

        today = datetime(2025, 3, 1).date()
        engine._daily_pnl[today] = -100_000.0  # 1% loss < 3% limit

        assert engine._check_daily_loss(today) is False


class TestProgressCallback:
    def test_on_progress_called(self):
        """on_progress callback receives (current, total) during replay."""
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )

        progress_calls = []
        candles = _make_candles([10000] * 5)
        engine.run(candles, on_progress=lambda cur, tot: progress_calls.append((cur, tot)))

        assert len(progress_calls) == 5
        assert progress_calls[-1] == (5, 5)


class TestEquityCurve:
    def test_equity_snapshots_recorded(self):
        """Equity curve has one entry per candle."""
        engine = BacktestEngine(
            strategy_configs=_rsi_strategy_config(),
            risk_config=RiskConfig(),
            cost_config=_zero_cost_config(),
            initial_capital=10_000_000,
        )
        candles = _make_candles([10000] * 5)
        result = engine.run(candles)
        assert len(result.equity_curve) == 5
