"""Composite condition engine for evaluating AND/OR trading rules.

Evaluates CompositeRule trees against a context dict of indicator values.
Supports 6 operators: gt, lt, gte, lte, cross_above, cross_below.
Missing indicator keys gracefully evaluate to False (warmup handling).
"""

from __future__ import annotations

from kiwoom_trader.core.models import Condition, CompositeRule


class ConditionEngine:
    """Evaluates composite trading rules against indicator context."""

    def evaluate(self, rule: CompositeRule, context: dict) -> bool:
        """Recursively evaluate a CompositeRule tree.

        Args:
            rule: CompositeRule with AND/OR logic and nested conditions.
            context: Dict mapping indicator names to current values.
                     For cross operators, must include "{indicator}_prev" keys.

        Returns:
            True if the rule is satisfied, False otherwise.
        """
        results = []
        for condition in rule.conditions:
            if isinstance(condition, CompositeRule):
                results.append(self.evaluate(condition, context))
            else:
                results.append(self._eval_condition(condition, context))

        if rule.logic == "AND":
            return all(results)
        else:  # OR
            return any(results)

    def _eval_condition(self, condition: Condition, context: dict) -> bool:
        """Evaluate a single Condition against the context.

        Returns False if the required indicator key is missing (graceful warmup).
        """
        ind = condition.indicator
        op = condition.operator
        threshold = condition.value

        # Cross operators need both current and prev values
        if op in ("cross_above", "cross_below"):
            if ind not in context or f"{ind}_prev" not in context:
                return False
            current = context[ind]
            prev = context[f"{ind}_prev"]
            if op == "cross_above":
                return prev <= threshold and current > threshold
            else:  # cross_below
                return prev >= threshold and current < threshold

        # Standard comparison operators
        if ind not in context:
            return False
        current = context[ind]

        if op == "gt":
            return current > threshold
        elif op == "lt":
            return current < threshold
        elif op == "gte":
            return current >= threshold
        elif op == "lte":
            return current <= threshold
        else:
            return False
