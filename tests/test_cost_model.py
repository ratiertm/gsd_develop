"""Tests for backtest cost model: CostConfig, calc_buy_cost, calc_sell_proceeds."""

from kiwoom_trader.backtest.cost_model import CostConfig, calc_buy_cost, calc_sell_proceeds


class TestCostConfig:
    """CostConfig dataclass defaults match Korean market specifics."""

    def test_default_values(self):
        cfg = CostConfig()
        assert cfg.buy_commission_pct == 0.015
        assert cfg.sell_commission_pct == 0.015
        assert cfg.tax_pct == 0.18
        assert cfg.slippage_bp == 5.0

    def test_custom_values(self):
        cfg = CostConfig(buy_commission_pct=0.01, sell_commission_pct=0.02, tax_pct=0.20, slippage_bp=10.0)
        assert cfg.buy_commission_pct == 0.01
        assert cfg.sell_commission_pct == 0.02
        assert cfg.tax_pct == 0.20
        assert cfg.slippage_bp == 10.0


class TestCalcBuyCost:
    """calc_buy_cost applies slippage + commission (buy-side only, no tax)."""

    def test_basic_buy_cost(self):
        """Buy 10 shares at 10000 with default config."""
        cfg = CostConfig()
        cost = calc_buy_cost(10000, 10, cfg)
        # effective_price = 10000 + int(10000 * 5.0 / 10000) = 10000 + 5 = 10005
        # effective_amount = 10005 * 10 = 100050
        # commission = int(100050 * 0.015 / 100) = int(15.0075) = 15
        # total = 100050 + 15 = 100065
        assert cost == 100065

    def test_zero_slippage_zero_commission(self):
        """With zero config, returns exact amount."""
        cfg = CostConfig(buy_commission_pct=0.0, sell_commission_pct=0.0, tax_pct=0.0, slippage_bp=0.0)
        cost = calc_buy_cost(10000, 10, cfg)
        assert cost == 100000

    def test_zero_qty(self):
        cfg = CostConfig()
        cost = calc_buy_cost(10000, 0, cfg)
        assert cost == 0

    def test_single_share(self):
        cfg = CostConfig()
        cost = calc_buy_cost(50000, 1, cfg)
        # effective_price = 50000 + int(50000 * 5.0 / 10000) = 50000 + 25 = 50025
        # effective_amount = 50025 * 1 = 50025
        # commission = int(50025 * 0.015 / 100) = int(7.50375) = 7
        # total = 50025 + 7 = 50032
        assert cost == 50032

    def test_high_slippage(self):
        """Higher slippage increases buy cost."""
        cfg = CostConfig(slippage_bp=20.0)
        cost = calc_buy_cost(10000, 10, cfg)
        # effective_price = 10000 + int(10000 * 20.0 / 10000) = 10000 + 20 = 10020
        # effective_amount = 10020 * 10 = 100200
        # commission = int(100200 * 0.015 / 100) = int(15.03) = 15
        # total = 100200 + 15 = 100215
        assert cost == 100215


class TestCalcSellProceeds:
    """calc_sell_proceeds deducts commission + tax (sell-side) + slippage."""

    def test_basic_sell_proceeds(self):
        """Sell 10 shares at 10000 with default config."""
        cfg = CostConfig()
        proceeds = calc_sell_proceeds(10000, 10, cfg)
        # effective_price = 10000 - int(10000 * 5.0 / 10000) = 10000 - 5 = 9995
        # effective_amount = 9995 * 10 = 99950
        # commission = int(99950 * 0.015 / 100) = int(14.9925) = 14
        # tax = int(99950 * 0.18 / 100) = int(179.91) = 179
        # net = 99950 - 14 - 179 = 99757
        assert proceeds == 99757

    def test_zero_config_returns_exact_amount(self):
        cfg = CostConfig(buy_commission_pct=0.0, sell_commission_pct=0.0, tax_pct=0.0, slippage_bp=0.0)
        proceeds = calc_sell_proceeds(10000, 10, cfg)
        assert proceeds == 100000

    def test_zero_qty(self):
        cfg = CostConfig()
        proceeds = calc_sell_proceeds(10000, 0, cfg)
        assert proceeds == 0

    def test_tax_is_sell_side_only(self):
        """Tax applies only on sell, not buy."""
        cfg_no_tax = CostConfig(tax_pct=0.0)
        cfg_with_tax = CostConfig(tax_pct=0.18)
        # Buy cost should be same regardless of tax
        buy_no_tax = calc_buy_cost(10000, 10, cfg_no_tax)
        buy_with_tax = calc_buy_cost(10000, 10, cfg_with_tax)
        assert buy_no_tax == buy_with_tax

        # Sell proceeds differ with tax
        sell_no_tax = calc_sell_proceeds(10000, 10, cfg_no_tax)
        sell_with_tax = calc_sell_proceeds(10000, 10, cfg_with_tax)
        assert sell_no_tax > sell_with_tax

    def test_slippage_reduces_sell_proceeds(self):
        """Higher slippage decreases sell proceeds."""
        cfg_low = CostConfig(slippage_bp=5.0)
        cfg_high = CostConfig(slippage_bp=20.0)
        assert calc_sell_proceeds(10000, 10, cfg_low) > calc_sell_proceeds(10000, 10, cfg_high)
