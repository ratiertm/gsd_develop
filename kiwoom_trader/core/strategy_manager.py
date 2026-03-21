"""Strategy manager: loads strategies, evaluates conditions, routes signals.

Manages indicator instances per stock per strategy, evaluates entry/exit rules
via ConditionEngine, resolves signal conflicts by priority, enforces cooldown,
and routes signals to PaperTrader or RiskManager->OrderManager.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from kiwoom_trader.config.constants import HogaGb
from kiwoom_trader.core.condition_engine import ConditionEngine
from kiwoom_trader.core.indicators import (
    ADXIndicator,
    ATRIndicator,
    BollingerBandsIndicator,
    EMAIndicator,
    MACDIndicator,
    OBVIndicator,
    RSIIndicator,
    SMAIndicator,
    VWAPIndicator,
)
from kiwoom_trader.core.models import (
    Candle,
    CompositeRule,
    Condition,
    OrderSide,
    Signal,
    StrategyConfig,
)

if TYPE_CHECKING:
    from kiwoom_trader.core.paper_trader import PaperTrader


# Indicator type string -> class mapping
INDICATOR_CLASSES: dict[str, type] = {
    "sma": SMAIndicator,
    "ema": EMAIndicator,
    "rsi": RSIIndicator,
    "macd": MACDIndicator,
    "bollinger": BollingerBandsIndicator,
    "vwap": VWAPIndicator,
    "obv": OBVIndicator,
    "atr": ATRIndicator,
    "adx": ADXIndicator,
}


def _parse_rule(rule_dict: dict) -> CompositeRule:
    """Parse a rule dict into a CompositeRule tree."""
    conditions = []
    for item in rule_dict["conditions"]:
        if "logic" in item:
            # Nested CompositeRule
            conditions.append(_parse_rule(item))
        else:
            conditions.append(
                Condition(
                    indicator=item["indicator"],
                    operator=item["operator"],
                    value=item.get("value"),
                    value_ref=item.get("value_ref"),
                )
            )
    return CompositeRule(logic=rule_dict["logic"], conditions=conditions)


class StrategyManager:
    """Manages trading strategies, evaluates conditions, and routes signals.

    Args:
        condition_engine: ConditionEngine for rule evaluation.
        risk_manager: RiskManager for live order validation.
        order_manager: OrderManager for live order submission.
        config: Dict with "mode", "strategies", "watchlist_strategies" keys.
    """

    def __init__(
        self,
        condition_engine: ConditionEngine,
        risk_manager,
        order_manager,
        config: dict,
    ) -> None:
        self._condition_engine = condition_engine
        self._risk_manager = risk_manager
        self._order_manager = order_manager
        self._mode = config.get("mode", "paper")
        self._watchlist: dict[str, list[str]] = config.get("watchlist_strategies", {})

        # Indicator instances: (code, strategy_name) -> {indicator_name: instance}
        self._indicators: dict[tuple[str, str], dict] = {}

        # Previous indicator values for cross detection: (code, strategy_name, indicator_name) -> value
        self._prev_values: dict[tuple[str, str, str], float] = {}

        # Cooldown tracking: (code, side) -> last signal timestamp
        self._cooldowns: dict[tuple[str, str], datetime] = {}

        # Market context: external data injected into evaluation context
        # e.g. {"005930": {"prev_close": 188700, "prev_high": 189200, ...}, "_global": {"kospi_pct": -0.5}}
        self.market_context: dict[str, dict[str, float]] = {}

        # Paper trader (set externally or created internally)
        self.paper_trader: PaperTrader | None = None

        # Load strategies
        self.strategies: list[StrategyConfig] = self._load_strategies(config)

        # Strategy lookup by name for quick access
        self._strategy_map: dict[str, StrategyConfig] = {s.name: s for s in self.strategies}

    def _load_strategies(self, config: dict) -> list[StrategyConfig]:
        """Parse strategy dicts into StrategyConfig objects."""
        strategies = []
        for s_dict in config.get("strategies", []):
            entry_rule = _parse_rule(s_dict["entry_rule"])
            exit_rule = _parse_rule(s_dict["exit_rule"])
            strategies.append(
                StrategyConfig(
                    name=s_dict["name"],
                    enabled=s_dict.get("enabled", True),
                    priority=s_dict.get("priority", 0),
                    entry_rule=entry_rule,
                    exit_rule=exit_rule,
                    indicators=s_dict.get("indicators", {}),
                    cooldown_sec=s_dict.get("cooldown_sec", 300),
                )
            )
        return strategies

    def _init_indicators(self, strategy: StrategyConfig, code: str) -> dict:
        """Create indicator instances for a (code, strategy) pair.

        Returns dict of {indicator_name: indicator_instance}.
        """
        key = (code, strategy.name)
        if key in self._indicators:
            return self._indicators[key]

        instances: dict = {}
        for ind_name, ind_config in strategy.indicators.items():
            ind_type = ind_config["type"]
            cls = INDICATOR_CLASSES.get(ind_type)
            if cls is None:
                logger.warning(f"Unknown indicator type: {ind_type}")
                continue

            # Create instance with config params (exclude 'type')
            params = {k: v for k, v in ind_config.items() if k != "type"}
            instances[ind_name] = cls(**params)

        self._indicators[key] = instances
        return instances

    # Sub-component names for tuple-returning indicators
    _TUPLE_COMPONENTS: dict[type, list[str]] = {
        BollingerBandsIndicator: ["upper", "middle", "lower"],
        MACDIndicator: ["line", "signal", "histogram"],
        ADXIndicator: ["adx", "plus_di", "minus_di"],
    }

    def _update_indicator(
        self, ind_name: str, instance, candle: Candle
    ) -> tuple[float | None, dict[str, float]]:
        """Update an indicator instance with candle data.

        Returns:
            (primary_value, sub_components) where sub_components maps
            e.g. "bollinger_upper" -> value for tuple indicators.
        """
        if isinstance(instance, (VWAPIndicator, ATRIndicator, ADXIndicator)):
            result = instance.update_candle(candle.high, candle.low, candle.close, candle.volume)
            if isinstance(result, tuple):
                components = self._TUPLE_COMPONENTS.get(type(instance), [])
                sub = {}
                for i, comp_name in enumerate(components):
                    if i < len(result):
                        sub[f"{ind_name}_{comp_name}"] = result[i]
                return result[0] if result else None, sub
            return result, {}
        elif isinstance(instance, OBVIndicator):
            val = instance.update(candle.close, candle.volume)
            return val, {}
        else:
            result = instance.update(candle.close)
            if isinstance(result, tuple):
                components = self._TUPLE_COMPONENTS.get(type(instance), [])
                sub = {}
                for i, comp_name in enumerate(components):
                    if i < len(result):
                        sub[f"{ind_name}_{comp_name}"] = result[i]
                return result[0], sub
            return result, {}

    def on_candle_complete(self, code: str, candle: Candle) -> list[Signal]:
        """Process a completed candle through all strategies assigned to this code.

        This is the 2-arg callback matching CandleAggregator's Callable[[str, Candle], None].

        Args:
            code: Stock code.
            candle: Completed candle data.

        Returns:
            List of signals that survived conflict resolution and cooldown.
        """
        # Get strategies assigned to this code
        assigned_strategies = self._watchlist.get(code, [])
        if not assigned_strategies:
            return []

        all_signals: list[Signal] = []

        for strat_name in assigned_strategies:
            strategy = self._strategy_map.get(strat_name)
            if strategy is None or not strategy.enabled:
                continue

            # Get or create indicator instances
            indicators = self._init_indicators(strategy, code)

            # Update ALL indicators first (so none miss candle data during warmup)
            primary_values: dict[str, float | None] = {}
            all_sub_components: dict[str, float] = {}
            for ind_name, instance in indicators.items():
                primary, subs = self._update_indicator(ind_name, instance, candle)
                primary_values[ind_name] = primary
                all_sub_components.update(subs)

            # Check if any indicator is still warming up
            if any(v is None for v in primary_values.values()):
                continue  # Warmup not complete

            # Build context with current and previous values
            context: dict[str, float] = {
                "price": float(candle.close),
                "volume": float(candle.volume),
                "hour": float(candle.timestamp.hour),
                "minute": float(candle.timestamp.minute),
            }

            for ind_name, current in primary_values.items():
                prev_key = (code, strat_name, ind_name)
                prev = self._prev_values.get(prev_key)

                context[ind_name] = current
                if prev is not None:
                    context[f"{ind_name}_prev"] = prev

                # Store current as next iteration's prev
                self._prev_values[prev_key] = current

            # Register sub-components (e.g. bollinger_upper, macd_signal)
            for sub_name, sub_val in all_sub_components.items():
                prev_key = (code, strat_name, sub_name)
                prev = self._prev_values.get(prev_key)

                context[sub_name] = sub_val
                if prev is not None:
                    context[f"{sub_name}_prev"] = prev

                self._prev_values[prev_key] = sub_val

            # Inject market context (per-code + global)
            if code in self.market_context:
                context.update(self.market_context[code])
            if "_global" in self.market_context:
                context.update(self.market_context["_global"])

            # Evaluate entry and exit rules
            if self._condition_engine.evaluate(strategy.entry_rule, context):
                all_signals.append(
                    Signal(
                        code=code,
                        side="BUY",
                        strategy_name=strat_name,
                        priority=strategy.priority,
                        price=candle.close,
                        timestamp=candle.timestamp,
                        reason=f"{strat_name} entry triggered",
                    )
                )

            if self._condition_engine.evaluate(strategy.exit_rule, context):
                all_signals.append(
                    Signal(
                        code=code,
                        side="SELL",
                        strategy_name=strat_name,
                        priority=strategy.priority,
                        price=candle.close,
                        timestamp=candle.timestamp,
                        reason=f"{strat_name} exit triggered",
                    )
                )

        # Resolve conflicts and apply cooldown
        resolved = self._resolve_conflicts(all_signals)
        surviving: list[Signal] = []
        for sig in resolved:
            if self._check_cooldown(sig.code, sig):
                self._record_cooldown(sig.code, sig)
                self._execute_signal(sig)
                surviving.append(sig)

        return surviving

    def _resolve_conflicts(self, signals: list[Signal]) -> list[Signal]:
        """Resolve signal conflicts using priority-weighted voting.

        1. Per (code, side): keep highest priority signal
        2. Cross-side conflict (BUY vs SELL for same code):
           - Compare BUY weight sum vs SELL weight sum
           - Only the winning side survives
           - If tied, no action (skip both)
        """
        # Step 1: best signal per (code, side)
        best: dict[tuple[str, str], Signal] = {}
        for sig in signals:
            key = (sig.code, sig.side)
            if key not in best or sig.priority > best[key].priority:
                best[key] = sig

        # Step 2: cross-side conflict resolution per code
        # Collect weight sums per code per side
        code_weights: dict[str, dict[str, int]] = {}
        for sig in signals:
            if sig.code not in code_weights:
                code_weights[sig.code] = {"BUY": 0, "SELL": 0}
            code_weights[sig.code][sig.side] += sig.priority

        # Remove losing side from best
        result: list[Signal] = []
        for (code, side), sig in best.items():
            weights = code_weights.get(code, {})
            buy_w = weights.get("BUY", 0)
            sell_w = weights.get("SELL", 0)

            if buy_w > 0 and sell_w > 0:
                # Conflict: only winning side passes
                if side == "BUY" and buy_w > sell_w:
                    result.append(sig)
                elif side == "SELL" and sell_w > buy_w:
                    result.append(sig)
                else:
                    # Tied or losing side — skip
                    logger.debug(
                        f"[CONFLICT] {code} {side} dropped (BUY={buy_w} vs SELL={sell_w})"
                    )
            else:
                # No conflict
                result.append(sig)

        return result

    def _check_cooldown(self, code: str, signal: Signal) -> bool:
        """Return True if signal passes cooldown check (enough time elapsed)."""
        key = (code, signal.side)
        if key not in self._cooldowns:
            return True

        last_time = self._cooldowns[key]
        strategy = self._strategy_map.get(signal.strategy_name)
        cooldown_sec = strategy.cooldown_sec if strategy else 300

        elapsed = (signal.timestamp - last_time).total_seconds()
        return elapsed >= cooldown_sec

    def _record_cooldown(self, code: str, signal: Signal) -> None:
        """Record signal timestamp for cooldown tracking."""
        key = (code, signal.side)
        self._cooldowns[key] = signal.timestamp

    def _execute_signal(self, signal: Signal) -> None:
        """Route signal to PaperTrader or RiskManager->OrderManager."""
        if self._mode == "replay":
            return  # ReplayEngine handles execution directly
        if self._mode == "paper":
            if self.paper_trader is not None:
                self.paper_trader.execute_signal(signal)
            else:
                logger.warning("Paper mode but no PaperTrader configured")
        else:
            # Live mode: validate then submit
            if self._risk_manager is None or self._order_manager is None:
                logger.error(
                    "Live mode but RiskManager/OrderManager not initialized"
                )
                return
            side = OrderSide.BUY if signal.side == "BUY" else OrderSide.SELL
            valid, reason = self._risk_manager.validate_order(
                signal.code, side, 1, signal.price
            )
            if valid:
                self._order_manager.submit_order(
                    signal.code, side, 1, signal.price, HogaGb.MARKET
                )
            else:
                logger.warning(f"Signal rejected by risk manager: {reason}")

    def reset_daily(self) -> None:
        """Reset cooldown state for new trading day."""
        self._cooldowns.clear()

    def reset_vwap(self) -> None:
        """Reset all managed VWAP indicator instances."""
        for indicators in self._indicators.values():
            for instance in indicators.values():
                if isinstance(instance, VWAPIndicator):
                    instance.reset()
