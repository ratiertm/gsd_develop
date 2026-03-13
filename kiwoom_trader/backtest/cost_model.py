"""Cost model for backtest trade execution.

Handles Korean market specifics:
- Buy: commission + slippage (no tax)
- Sell: commission + tax (0.18%) + slippage
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostConfig:
    """Transaction cost configuration for backtest.

    Defaults reflect Korean market (Kiwoom Securities online trading):
    - buy_commission_pct: 0.015% (both sides)
    - sell_commission_pct: 0.015% (both sides)
    - tax_pct: 0.18% (sell-side only, Korean securities transaction tax)
    - slippage_bp: 5.0 basis points (0.05%)
    """

    buy_commission_pct: float = 0.015
    sell_commission_pct: float = 0.015
    tax_pct: float = 0.18
    slippage_bp: float = 5.0


def calc_buy_cost(price: int, qty: int, config: CostConfig) -> int:
    """Calculate total cost to buy shares.

    Total = effective_amount + commission.
    Slippage increases effective buy price.
    Tax does NOT apply to buy side.

    Args:
        price: Share price in KRW.
        qty: Number of shares.
        config: Cost configuration.

    Returns:
        Total cost in KRW (integer).
    """
    if qty == 0:
        return 0
    effective_price = price + int(price * config.slippage_bp / 10000)
    effective_amount = effective_price * qty
    commission = int(effective_amount * config.buy_commission_pct / 100)
    return effective_amount + commission


def calc_sell_proceeds(price: int, qty: int, config: CostConfig) -> int:
    """Calculate net proceeds from selling shares.

    Net = effective_amount - commission - tax.
    Slippage decreases effective sell price.
    Tax (0.18%) applies to sell side only.

    Args:
        price: Share price in KRW.
        qty: Number of shares.
        config: Cost configuration.

    Returns:
        Net proceeds in KRW (integer).
    """
    if qty == 0:
        return 0
    effective_price = price - int(price * config.slippage_bp / 10000)
    effective_amount = effective_price * qty
    commission = int(effective_amount * config.sell_commission_pct / 100)
    tax = int(effective_amount * config.tax_pct / 100)
    return effective_amount - commission - tax
