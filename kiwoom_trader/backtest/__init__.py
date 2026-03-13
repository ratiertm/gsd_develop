"""Backtest module: historical data replay and strategy validation.

Exports:
    DataSource, KiwoomDataSource - Historical data retrieval
    CostConfig, calc_buy_cost, calc_sell_proceeds - Cost modeling
"""

from kiwoom_trader.backtest.cost_model import CostConfig, calc_buy_cost, calc_sell_proceeds
from kiwoom_trader.backtest.data_source import DataSource, KiwoomDataSource

__all__ = [
    "DataSource",
    "KiwoomDataSource",
    "CostConfig",
    "calc_buy_cost",
    "calc_sell_proceeds",
]
