"""Tests for ConditionEngine - composite AND/OR rule evaluation."""

import pytest

from kiwoom_trader.core.condition_engine import ConditionEngine
from kiwoom_trader.core.models import Condition, CompositeRule


@pytest.fixture
def engine():
    return ConditionEngine()


class TestSingleConditions:
    """Test individual condition operators."""

    def test_single_condition_gt(self, engine):
        """RSI > 70 with context {rsi: 75} -> True."""
        cond = Condition(indicator="rsi", operator="gt", value=70.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 75.0}) is True

    def test_single_condition_gt_false(self, engine):
        """RSI > 70 with context {rsi: 65} -> False."""
        cond = Condition(indicator="rsi", operator="gt", value=70.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 65.0}) is False

    def test_single_condition_lt(self, engine):
        """RSI < 30 with context {rsi: 25} -> True."""
        cond = Condition(indicator="rsi", operator="lt", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 25.0}) is True

    def test_single_condition_lt_false(self, engine):
        """RSI < 30 with context {rsi: 35} -> False."""
        cond = Condition(indicator="rsi", operator="lt", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 35.0}) is False

    def test_gte_operator(self, engine):
        """gte at boundary: value == threshold -> True."""
        cond = Condition(indicator="rsi", operator="gte", value=70.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 70.0}) is True

    def test_gte_operator_below(self, engine):
        """gte below boundary -> False."""
        cond = Condition(indicator="rsi", operator="gte", value=70.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 69.9}) is False

    def test_lte_operator(self, engine):
        """lte at boundary: value == threshold -> True."""
        cond = Condition(indicator="rsi", operator="lte", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 30.0}) is True

    def test_lte_operator_above(self, engine):
        """lte above boundary -> False."""
        cond = Condition(indicator="rsi", operator="lte", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 30.1}) is False


class TestCrossOperators:
    """Test cross_above and cross_below operators."""

    def test_cross_above(self, engine):
        """prev<=threshold AND current>threshold -> True."""
        cond = Condition(indicator="rsi", operator="cross_above", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        context = {"rsi": 31.0, "rsi_prev": 29.0}
        assert engine.evaluate(rule, context) is True

    def test_cross_above_already_above(self, engine):
        """Both prev and current above threshold -> False (not a cross)."""
        cond = Condition(indicator="rsi", operator="cross_above", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        context = {"rsi": 35.0, "rsi_prev": 32.0}
        assert engine.evaluate(rule, context) is False

    def test_cross_above_at_boundary(self, engine):
        """prev==threshold AND current>threshold -> True (prev<=threshold satisfied)."""
        cond = Condition(indicator="rsi", operator="cross_above", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        context = {"rsi": 31.0, "rsi_prev": 30.0}
        assert engine.evaluate(rule, context) is True

    def test_cross_below(self, engine):
        """prev>=threshold AND current<threshold -> True."""
        cond = Condition(indicator="rsi", operator="cross_below", value=70.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        context = {"rsi": 69.0, "rsi_prev": 71.0}
        assert engine.evaluate(rule, context) is True

    def test_cross_below_already_below(self, engine):
        """Both prev and current below threshold -> False."""
        cond = Condition(indicator="rsi", operator="cross_below", value=70.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        context = {"rsi": 65.0, "rsi_prev": 68.0}
        assert engine.evaluate(rule, context) is False

    def test_cross_below_at_boundary(self, engine):
        """prev==threshold AND current<threshold -> True."""
        cond = Condition(indicator="rsi", operator="cross_below", value=70.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        context = {"rsi": 69.0, "rsi_prev": 70.0}
        assert engine.evaluate(rule, context) is True


class TestCompositeRules:
    """Test AND/OR composite rule evaluation."""

    def test_and_rule_all_true(self, engine):
        """AND rule: all conditions true -> True."""
        rule = CompositeRule(
            logic="AND",
            conditions=[
                Condition(indicator="rsi", operator="lt", value=30.0),
                Condition(indicator="volume", operator="gt", value=1000.0),
            ],
        )
        context = {"rsi": 25.0, "volume": 2000.0}
        assert engine.evaluate(rule, context) is True

    def test_and_rule_one_false(self, engine):
        """AND rule: one condition false -> False."""
        rule = CompositeRule(
            logic="AND",
            conditions=[
                Condition(indicator="rsi", operator="lt", value=30.0),
                Condition(indicator="volume", operator="gt", value=1000.0),
            ],
        )
        context = {"rsi": 25.0, "volume": 500.0}
        assert engine.evaluate(rule, context) is False

    def test_or_rule_one_true(self, engine):
        """OR rule: one condition true -> True."""
        rule = CompositeRule(
            logic="OR",
            conditions=[
                Condition(indicator="rsi", operator="lt", value=30.0),
                Condition(indicator="volume", operator="gt", value=1000.0),
            ],
        )
        context = {"rsi": 25.0, "volume": 500.0}
        assert engine.evaluate(rule, context) is True

    def test_or_rule_all_false(self, engine):
        """OR rule: all conditions false -> False."""
        rule = CompositeRule(
            logic="OR",
            conditions=[
                Condition(indicator="rsi", operator="lt", value=30.0),
                Condition(indicator="volume", operator="gt", value=1000.0),
            ],
        )
        context = {"rsi": 35.0, "volume": 500.0}
        assert engine.evaluate(rule, context) is False

    def test_nested_rules(self, engine):
        """AND(OR(a, b), c) evaluates correctly."""
        inner_or = CompositeRule(
            logic="OR",
            conditions=[
                Condition(indicator="rsi", operator="lt", value=30.0),
                Condition(indicator="macd", operator="gt", value=0.0),
            ],
        )
        outer_and = CompositeRule(
            logic="AND",
            conditions=[
                inner_or,
                Condition(indicator="volume", operator="gt", value=1000.0),
            ],
        )
        # rsi=35 (fails), macd=0.5 (passes OR), volume=2000 (passes) -> True
        context = {"rsi": 35.0, "macd": 0.5, "volume": 2000.0}
        assert engine.evaluate(outer_and, context) is True

    def test_nested_rules_fails(self, engine):
        """AND(OR(a, b), c) where inner OR fails -> False."""
        inner_or = CompositeRule(
            logic="OR",
            conditions=[
                Condition(indicator="rsi", operator="lt", value=30.0),
                Condition(indicator="macd", operator="gt", value=0.0),
            ],
        )
        outer_and = CompositeRule(
            logic="AND",
            conditions=[
                inner_or,
                Condition(indicator="volume", operator="gt", value=1000.0),
            ],
        )
        # rsi=35 (fails), macd=-0.5 (fails OR), volume=2000 -> False
        context = {"rsi": 35.0, "macd": -0.5, "volume": 2000.0}
        assert engine.evaluate(outer_and, context) is False


class TestMissingIndicator:
    """Test graceful handling of missing indicator keys."""

    def test_missing_indicator_returns_false(self, engine):
        """Missing indicator key in context -> condition evaluates to False."""
        cond = Condition(indicator="rsi", operator="lt", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {}) is False

    def test_missing_prev_for_cross(self, engine):
        """Missing _prev key for cross operator -> condition evaluates to False."""
        cond = Condition(indicator="rsi", operator="cross_above", value=30.0)
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"rsi": 31.0}) is False


class TestValueRef:
    """Test value_ref (indicator-to-indicator comparison)."""

    def test_value_ref_gt(self, engine):
        """ema_short > ema_long via value_ref."""
        cond = Condition(indicator="ema_short", operator="gt", value_ref="ema_long")
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"ema_short": 105.0, "ema_long": 100.0}) is True
        assert engine.evaluate(rule, {"ema_short": 95.0, "ema_long": 100.0}) is False

    def test_value_ref_lt(self, engine):
        """price < bollinger_lower via value_ref."""
        cond = Condition(indicator="price", operator="lt", value_ref="bollinger_lower")
        rule = CompositeRule(logic="AND", conditions=[cond])
        ctx = {"price": 67000.0, "bollinger_lower": 67500.0}
        assert engine.evaluate(rule, ctx) is True

    def test_value_ref_missing_target(self, engine):
        """Missing value_ref indicator in context -> False (warmup)."""
        cond = Condition(indicator="ema_short", operator="gt", value_ref="ema_long")
        rule = CompositeRule(logic="AND", conditions=[cond])
        assert engine.evaluate(rule, {"ema_short": 105.0}) is False

    def test_value_ref_cross_above(self, engine):
        """ema_short crosses above ema_long: prev below, current above."""
        cond = Condition(indicator="ema_short", operator="cross_above", value_ref="ema_long")
        rule = CompositeRule(logic="AND", conditions=[cond])
        ctx = {
            "ema_short": 105.0, "ema_short_prev": 99.0,
            "ema_long": 100.0, "ema_long_prev": 101.0,
        }
        assert engine.evaluate(rule, ctx) is True

    def test_value_ref_cross_above_no_cross(self, engine):
        """Both already above -> not a cross."""
        cond = Condition(indicator="ema_short", operator="cross_above", value_ref="ema_long")
        rule = CompositeRule(logic="AND", conditions=[cond])
        ctx = {
            "ema_short": 105.0, "ema_short_prev": 103.0,
            "ema_long": 100.0, "ema_long_prev": 101.0,
        }
        assert engine.evaluate(rule, ctx) is False

    def test_value_ref_cross_below(self, engine):
        """macd_line crosses below macd_signal."""
        cond = Condition(indicator="macd_line", operator="cross_below", value_ref="macd_signal")
        rule = CompositeRule(logic="AND", conditions=[cond])
        ctx = {
            "macd_line": 0.08, "macd_line_prev": 0.15,
            "macd_signal": 0.10, "macd_signal_prev": 0.12,
        }
        assert engine.evaluate(rule, ctx) is True

    def test_value_ref_cross_missing_prev(self, engine):
        """Missing _prev for value_ref target -> False."""
        cond = Condition(indicator="ema_short", operator="cross_above", value_ref="ema_long")
        rule = CompositeRule(logic="AND", conditions=[cond])
        ctx = {"ema_short": 105.0, "ema_short_prev": 99.0, "ema_long": 100.0}
        assert engine.evaluate(rule, ctx) is False

    def test_mixed_value_and_value_ref(self, engine):
        """AND rule with both value and value_ref conditions."""
        rule = CompositeRule(
            logic="AND",
            conditions=[
                Condition(indicator="price", operator="lt", value_ref="bollinger_lower"),
                Condition(indicator="rsi", operator="lt", value=30.0),
            ],
        )
        ctx = {"price": 67000.0, "bollinger_lower": 67500.0, "rsi": 25.0}
        assert engine.evaluate(rule, ctx) is True

        ctx2 = {"price": 67000.0, "bollinger_lower": 67500.0, "rsi": 35.0}
        assert engine.evaluate(rule, ctx2) is False
