"""Pure function performance metric calculators.

All functions are stateless -- no class, no side effects, stdlib only.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiwoom_trader.core.models import TradeRecord


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def calc_total_return(initial_capital: int, final_capital: float) -> float:
    """Return total return as a percentage.

    Returns 0.0 if *initial_capital* is zero.
    """
    if initial_capital == 0:
        return 0.0
    return (final_capital - initial_capital) / initial_capital * 100


def calc_max_drawdown(equity_curve: list[tuple[datetime, float]]) -> float:
    """Return maximum drawdown as a percentage of peak equity.

    Empty or single-point curves return 0.0.
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0][1]
    max_dd = 0.0
    for _, equity in equity_curve:
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
    return max_dd


def calc_win_rate(trades: list[TradeRecord]) -> float:
    """Return win rate as a percentage of profitable SELL trades.

    Only SELL trades are counted (BUY trades have no realized P&L).
    Returns 0.0 when there are no SELL trades.
    """
    sell_trades = [t for t in trades if t.side == "SELL"]
    if not sell_trades:
        return 0.0
    winners = sum(1 for t in sell_trades if t.pnl > 0)
    return winners / len(sell_trades) * 100


def calc_profit_factor(trades: list[TradeRecord]) -> float:
    """Return gross profit / gross loss for SELL trades.

    - All profits, no losses -> float('inf')
    - All losses or no trades -> 0.0
    """
    sell_trades = [t for t in trades if t.side == "SELL"]
    if not sell_trades:
        return 0.0

    gross_profit = sum(t.pnl for t in sell_trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in sell_trades if t.pnl < 0))

    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def calc_sharpe_ratio(
    daily_returns: list[float],
    risk_free_rate: float = 0.035,
    trading_days: int = 252,
) -> float:
    """Return annualized Sharpe ratio.

    Uses sample standard deviation (N-1 denominator).
    Returns 0.0 for fewer than 2 data points or zero standard deviation.
    """
    if len(daily_returns) < 2:
        return 0.0

    n = len(daily_returns)
    mean_ret = sum(daily_returns) / n
    variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (n - 1)
    std_ret = math.sqrt(variance)

    if std_ret == 0:
        return 0.0

    daily_rf = risk_free_rate / trading_days
    excess_daily = mean_ret - daily_rf
    annual_std = std_ret * math.sqrt(trading_days)
    return (excess_daily * trading_days) / annual_std


# ---------------------------------------------------------------------------
# Additional metrics
# ---------------------------------------------------------------------------

def calc_avg_pnl(trades: list[TradeRecord]) -> float:
    """Return average P&L of SELL trades. 0.0 if no sells."""
    sell_trades = [t for t in trades if t.side == "SELL"]
    if not sell_trades:
        return 0.0
    return sum(t.pnl for t in sell_trades) / len(sell_trades)


def calc_max_consecutive_losses(trades: list[TradeRecord]) -> int:
    """Return longest streak of SELL trades with pnl <= 0.

    BUY trades are ignored (not counted, not breaking streaks).
    """
    max_streak = 0
    current = 0
    for t in trades:
        if t.side != "SELL":
            continue
        if t.pnl <= 0:
            current += 1
            if current > max_streak:
                max_streak = current
        else:
            current = 0
    return max_streak


def calc_total_trades(trades: list[TradeRecord]) -> int:
    """Return the number of SELL trades (round-trips)."""
    return sum(1 for t in trades if t.side == "SELL")


def calc_avg_holding_period(trades: list[TradeRecord]) -> float:
    """Return average holding period in days between BUY-SELL pairs.

    Pairs are matched in order: first unmatched BUY with next SELL.
    Returns 0.0 when no complete pairs exist.
    """
    buy_queue: list[datetime] = []
    holding_days: list[float] = []

    for t in trades:
        if t.side == "BUY":
            buy_queue.append(t.timestamp)
        elif t.side == "SELL" and buy_queue:
            buy_ts = buy_queue.pop(0)
            delta = (t.timestamp - buy_ts).total_seconds() / 86400.0
            holding_days.append(delta)

    if not holding_days:
        return 0.0
    return sum(holding_days) / len(holding_days)


def calc_daily_returns(
    equity_curve: list[tuple[datetime, float]],
) -> list[float]:
    """Return list of daily percentage returns from equity snapshots.

    Division by zero (equity == 0) returns 0.0 for that period.
    """
    if len(equity_curve) < 2:
        return []

    returns = []
    for i in range(1, len(equity_curve)):
        prev_val = equity_curve[i - 1][1]
        curr_val = equity_curve[i][1]
        if prev_val == 0:
            returns.append(0.0)
        else:
            returns.append((curr_val - prev_val) / prev_val)
    return returns


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def compute_all_metrics(result: object) -> object:
    """Fill all metric fields on a BacktestResult and return it.

    Accepts any object with the expected attributes (duck-typed) so it works
    with both the local test BacktestResult and the real models.py version.
    """
    daily_returns = calc_daily_returns(result.equity_curve)

    result.total_return_pct = calc_total_return(
        result.initial_capital, result.final_capital
    )
    result.max_drawdown_pct = calc_max_drawdown(result.equity_curve)
    result.win_rate_pct = calc_win_rate(result.trades)
    result.profit_factor = calc_profit_factor(result.trades)
    result.sharpe_ratio = calc_sharpe_ratio(daily_returns)
    result.total_trades = calc_total_trades(result.trades)
    result.avg_pnl = calc_avg_pnl(result.trades)
    result.max_consecutive_losses = calc_max_consecutive_losses(result.trades)
    result.avg_holding_periods = calc_avg_holding_period(result.trades)

    return result
