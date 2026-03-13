"""Tests for performance metric pure functions (TDD RED phase).

Hand-calculated expected values for all metric functions.
BacktestResult is defined locally since 05-01 may not have added it to models.py yet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest

from kiwoom_trader.core.models import TradeRecord
from kiwoom_trader.backtest.performance import (
    calc_total_return,
    calc_max_drawdown,
    calc_win_rate,
    calc_profit_factor,
    calc_sharpe_ratio,
    calc_avg_pnl,
    calc_max_consecutive_losses,
    calc_total_trades,
    calc_avg_holding_period,
    calc_daily_returns,
    compute_all_metrics,
)


# ---------------------------------------------------------------------------
# Local BacktestResult for test isolation (real one lives in models.py via 05-01)
# ---------------------------------------------------------------------------
@dataclass
class BacktestResult:
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)
    initial_capital: int = 0
    final_capital: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    avg_pnl: float = 0.0
    max_consecutive_losses: int = 0
    avg_holding_periods: float = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_trade(
    side: str = "SELL",
    pnl: int = 0,
    price: int = 50000,
    qty: int = 10,
    ts: datetime | None = None,
) -> TradeRecord:
    return TradeRecord(
        timestamp=ts or datetime(2025, 1, 1),
        code="005930",
        side=side,
        strategy="test",
        price=price,
        qty=qty,
        amount=price * qty,
        pnl=pnl,
        pnl_pct=0.0,
        balance=10_000_000,
        reason="test",
    )


BASE = datetime(2025, 1, 1)


# ===================================================================
# calc_total_return
# ===================================================================
class TestCalcTotalReturn:
    def test_positive_return(self):
        # (11M - 10M) / 10M * 100 = 10.0%
        assert calc_total_return(10_000_000, 11_000_000) == pytest.approx(10.0)

    def test_negative_return(self):
        # (9M - 10M) / 10M * 100 = -10.0%
        assert calc_total_return(10_000_000, 9_000_000) == pytest.approx(-10.0)

    def test_zero_return(self):
        assert calc_total_return(10_000_000, 10_000_000) == pytest.approx(0.0)

    def test_initial_capital_zero(self):
        assert calc_total_return(0, 11_000_000) == 0.0

    def test_large_gain(self):
        # (20M - 10M) / 10M * 100 = 100.0%
        assert calc_total_return(10_000_000, 20_000_000) == pytest.approx(100.0)


# ===================================================================
# calc_max_drawdown
# ===================================================================
class TestCalcMaxDrawdown:
    def test_standard_drawdown(self):
        # Curve: 10M -> 12M -> 9M -> 11M
        # Peak=12M, trough=9M, DD = (12M-9M)/12M*100 = 25.0%
        curve = [
            (BASE, 10_000_000),
            (BASE + timedelta(days=1), 12_000_000),
            (BASE + timedelta(days=2), 9_000_000),
            (BASE + timedelta(days=3), 11_000_000),
        ]
        assert calc_max_drawdown(curve) == pytest.approx(25.0)

    def test_monotonically_increasing(self):
        curve = [
            (BASE, 10_000_000),
            (BASE + timedelta(days=1), 11_000_000),
            (BASE + timedelta(days=2), 12_000_000),
        ]
        assert calc_max_drawdown(curve) == pytest.approx(0.0)

    def test_empty_curve(self):
        assert calc_max_drawdown([]) == 0.0

    def test_single_point(self):
        assert calc_max_drawdown([(BASE, 10_000_000)]) == 0.0

    def test_two_drawdowns_picks_worst(self):
        # DD1: 100 -> 80 = 20%, DD2: 90 -> 60 = 33.3%
        curve = [
            (BASE, 100),
            (BASE + timedelta(days=1), 80),
            (BASE + timedelta(days=2), 90),
            (BASE + timedelta(days=3), 60),
        ]
        assert calc_max_drawdown(curve) == pytest.approx(40.0)
        # Peak stays at 100, trough goes to 60: (100-60)/100 = 40%


# ===================================================================
# calc_win_rate
# ===================================================================
class TestCalcWinRate:
    def test_basic_win_rate(self):
        # 3 sells: 2 profitable, 1 loss => 66.67%
        trades = [
            _make_trade(side="SELL", pnl=100_000),
            _make_trade(side="SELL", pnl=50_000),
            _make_trade(side="SELL", pnl=-30_000),
        ]
        assert calc_win_rate(trades) == pytest.approx(200 / 3, rel=1e-2)

    def test_ignores_buy_trades(self):
        trades = [
            _make_trade(side="BUY", pnl=0),
            _make_trade(side="SELL", pnl=100_000),
            _make_trade(side="SELL", pnl=-50_000),
        ]
        # 1 win / 2 sells = 50.0%
        assert calc_win_rate(trades) == pytest.approx(50.0)

    def test_no_sell_trades(self):
        trades = [_make_trade(side="BUY", pnl=0)]
        assert calc_win_rate(trades) == 0.0

    def test_empty_trades(self):
        assert calc_win_rate([]) == 0.0

    def test_all_winners(self):
        trades = [
            _make_trade(side="SELL", pnl=100),
            _make_trade(side="SELL", pnl=200),
        ]
        assert calc_win_rate(trades) == pytest.approx(100.0)

    def test_all_losers(self):
        trades = [
            _make_trade(side="SELL", pnl=-100),
            _make_trade(side="SELL", pnl=-200),
        ]
        assert calc_win_rate(trades) == pytest.approx(0.0)


# ===================================================================
# calc_profit_factor
# ===================================================================
class TestCalcProfitFactor:
    def test_standard(self):
        # gross_profit=300000, gross_loss=100000 => 3.0
        trades = [
            _make_trade(side="SELL", pnl=200_000),
            _make_trade(side="SELL", pnl=100_000),
            _make_trade(side="SELL", pnl=-100_000),
        ]
        assert calc_profit_factor(trades) == pytest.approx(3.0)

    def test_all_profits(self):
        trades = [
            _make_trade(side="SELL", pnl=100_000),
            _make_trade(side="SELL", pnl=50_000),
        ]
        assert calc_profit_factor(trades) == float("inf")

    def test_all_losses(self):
        trades = [
            _make_trade(side="SELL", pnl=-100_000),
        ]
        assert calc_profit_factor(trades) == 0.0

    def test_no_trades(self):
        assert calc_profit_factor([]) == 0.0

    def test_ignores_buy_trades(self):
        trades = [
            _make_trade(side="BUY", pnl=0),
            _make_trade(side="SELL", pnl=100_000),
            _make_trade(side="SELL", pnl=-50_000),
        ]
        # gross_profit=100000, gross_loss=50000 => 2.0
        assert calc_profit_factor(trades) == pytest.approx(2.0)

    def test_zero_pnl_sell_ignored(self):
        # pnl=0 is neither profit nor loss
        trades = [
            _make_trade(side="SELL", pnl=0),
            _make_trade(side="SELL", pnl=100_000),
            _make_trade(side="SELL", pnl=-50_000),
        ]
        assert calc_profit_factor(trades) == pytest.approx(2.0)


# ===================================================================
# calc_sharpe_ratio
# ===================================================================
class TestCalcSharpeRatio:
    def test_known_values(self):
        # daily_returns = [0.01, 0.02, -0.005, 0.015, 0.005] (5 days)
        # mean = (0.01+0.02-0.005+0.015+0.005)/5 = 0.045/5 = 0.009
        # daily_rf = 0.035/252 ≈ 0.00013889
        # excess = 0.009 - 0.00013889 = 0.00886111
        # variance = sum((r-0.009)^2) / 4
        #   deviations: 0.001, 0.011, -0.014, 0.006, -0.004
        #   sq: 0.000001, 0.000121, 0.000196, 0.000036, 0.000016
        #   sum = 0.00037, var = 0.00037/4 = 0.0000925
        #   std = sqrt(0.0000925) ≈ 0.009618
        # annual_std = 0.009618 * sqrt(252) ≈ 0.009618 * 15.8745 ≈ 0.15269
        # sharpe = (0.00886111 * 252) / 0.15269 ≈ 2.23296 / 0.15269 ≈ 14.62
        returns = [0.01, 0.02, -0.005, 0.015, 0.005]
        result = calc_sharpe_ratio(returns, risk_free_rate=0.035, trading_days=252)
        # Hand-calc ≈ 14.62 (high because these are daily pct returns, not decimal)
        assert result == pytest.approx(14.62, rel=0.05)

    def test_zero_std(self):
        # All same returns => std=0 => 0.0
        returns = [0.01, 0.01, 0.01]
        assert calc_sharpe_ratio(returns) == 0.0

    def test_fewer_than_two_points(self):
        assert calc_sharpe_ratio([0.01]) == 0.0
        assert calc_sharpe_ratio([]) == 0.0

    def test_negative_returns(self):
        # Should still compute (could be negative Sharpe)
        returns = [-0.01, -0.02, -0.015]
        result = calc_sharpe_ratio(returns)
        assert result < 0


# ===================================================================
# calc_avg_pnl
# ===================================================================
class TestCalcAvgPnl:
    def test_standard(self):
        trades = [
            _make_trade(side="SELL", pnl=100_000),
            _make_trade(side="SELL", pnl=-50_000),
            _make_trade(side="BUY", pnl=0),
        ]
        # Only SELL: (100000 + -50000) / 2 = 25000
        assert calc_avg_pnl(trades) == pytest.approx(25_000.0)

    def test_empty(self):
        assert calc_avg_pnl([]) == 0.0

    def test_no_sells(self):
        trades = [_make_trade(side="BUY", pnl=0)]
        assert calc_avg_pnl(trades) == 0.0


# ===================================================================
# calc_max_consecutive_losses
# ===================================================================
class TestCalcMaxConsecutiveLosses:
    def test_standard(self):
        trades = [
            _make_trade(side="SELL", pnl=100),
            _make_trade(side="SELL", pnl=-100),
            _make_trade(side="SELL", pnl=-200),
            _make_trade(side="SELL", pnl=-50),
            _make_trade(side="SELL", pnl=300),
            _make_trade(side="SELL", pnl=-10),
        ]
        # Consecutive losses: [1], [3 in a row], [1] => max = 3
        assert calc_max_consecutive_losses(trades) == 3

    def test_all_wins(self):
        trades = [
            _make_trade(side="SELL", pnl=100),
            _make_trade(side="SELL", pnl=200),
        ]
        assert calc_max_consecutive_losses(trades) == 0

    def test_empty(self):
        assert calc_max_consecutive_losses([]) == 0

    def test_zero_pnl_counts_as_loss(self):
        # pnl <= 0 counts as a loss
        trades = [
            _make_trade(side="SELL", pnl=0),
            _make_trade(side="SELL", pnl=-100),
        ]
        assert calc_max_consecutive_losses(trades) == 2

    def test_ignores_buy_trades(self):
        trades = [
            _make_trade(side="SELL", pnl=-100),
            _make_trade(side="BUY", pnl=0),
            _make_trade(side="SELL", pnl=-200),
        ]
        # BUY ignored; SELL losses: -100, -200 consecutive => 2
        assert calc_max_consecutive_losses(trades) == 2


# ===================================================================
# calc_total_trades
# ===================================================================
class TestCalcTotalTrades:
    def test_counts_sells_only(self):
        trades = [
            _make_trade(side="BUY"),
            _make_trade(side="SELL"),
            _make_trade(side="BUY"),
            _make_trade(side="SELL"),
            _make_trade(side="SELL"),
        ]
        assert calc_total_trades(trades) == 3

    def test_empty(self):
        assert calc_total_trades([]) == 0


# ===================================================================
# calc_avg_holding_period
# ===================================================================
class TestCalcAvgHoldingPeriod:
    def test_simple_pairs(self):
        # BUY at t=0, SELL at t=5 days; BUY at t=6, SELL at t=10 days
        trades = [
            _make_trade(side="BUY", ts=BASE),
            _make_trade(side="SELL", ts=BASE + timedelta(days=5)),
            _make_trade(side="BUY", ts=BASE + timedelta(days=6)),
            _make_trade(side="SELL", ts=BASE + timedelta(days=10)),
        ]
        # avg = (5 + 4) / 2 = 4.5 days
        assert calc_avg_holding_period(trades) == pytest.approx(4.5)

    def test_no_pairs(self):
        trades = [_make_trade(side="BUY")]
        assert calc_avg_holding_period(trades) == 0.0

    def test_empty(self):
        assert calc_avg_holding_period([]) == 0.0


# ===================================================================
# calc_daily_returns
# ===================================================================
class TestCalcDailyReturns:
    def test_standard(self):
        curve = [
            (BASE, 100.0),
            (BASE + timedelta(days=1), 110.0),
            (BASE + timedelta(days=2), 99.0),
        ]
        # r1 = (110-100)/100 = 0.10, r2 = (99-110)/110 = -0.10
        returns = calc_daily_returns(curve)
        assert len(returns) == 2
        assert returns[0] == pytest.approx(0.10)
        assert returns[1] == pytest.approx(-0.1, abs=0.001)

    def test_empty(self):
        assert calc_daily_returns([]) == []

    def test_single_point(self):
        assert calc_daily_returns([(BASE, 100.0)]) == []

    def test_zero_value_no_crash(self):
        # equity goes to 0 then non-zero: return 0.0 for div-by-zero
        curve = [
            (BASE, 100.0),
            (BASE + timedelta(days=1), 0.0),
            (BASE + timedelta(days=2), 50.0),
        ]
        returns = calc_daily_returns(curve)
        assert returns[0] == pytest.approx(-1.0)
        assert returns[1] == 0.0  # 0 -> 50, division by 0 => 0.0


# ===================================================================
# compute_all_metrics
# ===================================================================
class TestComputeAllMetrics:
    def test_fills_all_fields(self):
        trades = [
            _make_trade(side="BUY", pnl=0, ts=BASE),
            _make_trade(side="SELL", pnl=500_000, ts=BASE + timedelta(days=3)),
            _make_trade(side="BUY", pnl=0, ts=BASE + timedelta(days=4)),
            _make_trade(side="SELL", pnl=-200_000, ts=BASE + timedelta(days=7)),
        ]
        curve = [
            (BASE, 10_000_000.0),
            (BASE + timedelta(days=1), 10_100_000.0),
            (BASE + timedelta(days=2), 10_200_000.0),
            (BASE + timedelta(days=3), 10_500_000.0),
            (BASE + timedelta(days=4), 10_500_000.0),
            (BASE + timedelta(days=5), 10_400_000.0),
            (BASE + timedelta(days=6), 10_350_000.0),
            (BASE + timedelta(days=7), 10_300_000.0),
        ]
        result = BacktestResult(
            trades=trades,
            equity_curve=curve,
            initial_capital=10_000_000,
            final_capital=10_300_000.0,
        )
        result = compute_all_metrics(result)

        # total_return = (10.3M - 10M) / 10M * 100 = 3.0%
        assert result.total_return_pct == pytest.approx(3.0)
        # MDD: peak 10.5M, trough 10.3M => (10.5-10.3)/10.5*100 ≈ 1.905%
        assert result.max_drawdown_pct == pytest.approx(100 * 200_000 / 10_500_000, rel=0.01)
        # win_rate: 1 win / 2 sells = 50%
        assert result.win_rate_pct == pytest.approx(50.0)
        # profit_factor: 500000 / 200000 = 2.5
        assert result.profit_factor == pytest.approx(2.5)
        # total_trades: 2 sells
        assert result.total_trades == 2
        # avg_pnl: (500000 + -200000) / 2 = 150000
        assert result.avg_pnl == pytest.approx(150_000.0)
        # max_consecutive_losses: 1 (the -200000 trade)
        assert result.max_consecutive_losses == 1
        # avg_holding_period: (3 + 3) / 2 = 3.0 days
        assert result.avg_holding_periods == pytest.approx(3.0)
        # sharpe_ratio: should be a float (non-zero since returns vary)
        assert isinstance(result.sharpe_ratio, float)

    def test_empty_result(self):
        result = BacktestResult(
            trades=[],
            equity_curve=[],
            initial_capital=10_000_000,
            final_capital=10_000_000.0,
        )
        result = compute_all_metrics(result)
        assert result.total_return_pct == pytest.approx(0.0)
        assert result.max_drawdown_pct == pytest.approx(0.0)
        assert result.win_rate_pct == 0.0
        assert result.profit_factor == 0.0
        assert result.sharpe_ratio == 0.0
        assert result.total_trades == 0
        assert result.avg_pnl == 0.0
        assert result.max_consecutive_losses == 0
        assert result.avg_holding_periods == 0.0
