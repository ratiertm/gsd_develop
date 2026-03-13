"""BacktestEngine: replays historical candles through StrategyManager.

Creates a fresh StrategyManager + ConditionEngine per run to avoid stale state.
Handles trade execution with cost modeling, risk triggers (SL/TP/trailing stop),
position limits, daily loss limits, and forced close at end.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable

from loguru import logger

from kiwoom_trader.backtest.cost_model import CostConfig, calc_buy_cost, calc_sell_proceeds
from kiwoom_trader.core.condition_engine import ConditionEngine
from kiwoom_trader.core.models import (
    BacktestResult,
    Candle,
    RiskConfig,
    Signal,
    TradeRecord,
)
from kiwoom_trader.core.strategy_manager import StrategyManager


class BacktestEngine:
    """Replays historical candles through StrategyManager with cost modeling.

    Creates a fresh StrategyManager per run (no stale indicator state).
    Does NOT pass risk_manager or paper_trader to StrategyManager --
    BacktestEngine handles execution itself.

    Args:
        strategy_configs: Strategy configuration dict (mode, strategies, watchlist_strategies).
        risk_config: RiskConfig for SL/TP/trailing stop and position limits.
        cost_config: CostConfig for commission/tax/slippage.
        initial_capital: Starting capital in KRW.
    """

    def __init__(
        self,
        strategy_configs: dict,
        risk_config: RiskConfig,
        cost_config: CostConfig,
        initial_capital: int = 10_000_000,
    ) -> None:
        self._strategy_configs = strategy_configs
        self._risk_config = risk_config
        self._cost_config = cost_config
        self._initial_capital = initial_capital

        # Per-run state (reset at start of each run)
        self._capital: float = 0.0
        self._positions: dict[str, dict] = {}  # code -> {qty, avg_price, highest_price}
        self._trades: list[TradeRecord] = []
        self._equity_curve: list[tuple[datetime, float]] = []
        self._daily_pnl: dict[date, float] = {}  # date -> realized pnl for the day

    def run(
        self,
        candles: list[Candle],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> BacktestResult:
        """Run backtest simulation on the given candles.

        Creates a fresh StrategyManager + ConditionEngine for each run.
        Feeds candles one-by-one, captures signals, executes trades,
        checks risk triggers per candle, and force-closes at end.

        Args:
            candles: Historical candles sorted ascending by timestamp.
            on_progress: Optional callback(current_index, total_candles).

        Returns:
            BacktestResult with trades, equity curve, and capital info.
        """
        # Reset per-run state
        self._capital = float(self._initial_capital)
        self._positions = {}
        self._trades = []
        self._equity_curve = []
        self._daily_pnl = {}

        if not candles:
            return self._build_result()

        # Create fresh StrategyManager per run (no stale state)
        condition_engine = ConditionEngine()
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=self._strategy_configs,
        )

        total = len(candles)
        for i, candle in enumerate(candles):
            # 1. Feed candle to strategy manager -> get signals
            signals = strategy_manager.on_candle_complete(candle.code, candle)

            # 2. Process signals (BUY/SELL)
            for sig in signals:
                if sig.side == "BUY":
                    if not self._check_daily_loss(candle.timestamp.date()):
                        self._execute_buy(sig, candle)
                elif sig.side == "SELL":
                    self._execute_sell(
                        sig.code, sig.price, sig.reason, candle
                    )

            # 3. Check risk triggers (SL/TP/trailing stop)
            self._check_risk_triggers(candle)

            # 4. Record equity snapshot
            self._record_equity(candle)

            # 5. Progress callback
            if on_progress:
                on_progress(i + 1, total)

        # Force close all remaining positions at last candle price
        self._close_all_positions(candles[-1])

        return self._build_result()

    def _execute_buy(self, signal: Signal, candle: Candle) -> None:
        """Execute a buy trade with cost modeling.

        Validates position limits (max_positions, max_symbol_weight).
        Calculates quantity from capital weight.

        Args:
            signal: BUY signal from strategy.
            candle: Current candle data.
        """
        # Check max positions
        if len(self._positions) >= self._risk_config.max_positions:
            logger.debug(f"Max positions ({self._risk_config.max_positions}) reached, skipping buy")
            return

        # Check if already holding this code
        if signal.code in self._positions:
            logger.debug(f"Already holding {signal.code}, skipping buy")
            return

        price = signal.price
        if price <= 0:
            return

        # Calculate qty based on max symbol weight
        max_amount = self._capital * self._risk_config.max_symbol_weight_pct / 100
        # Calculate cost per share to determine qty
        cost_per_share = calc_buy_cost(price, 1, self._cost_config)
        if cost_per_share <= 0:
            return
        qty = int(max_amount / cost_per_share)
        if qty <= 0:
            return

        # Calculate actual total cost
        total_cost = calc_buy_cost(price, qty, self._cost_config)
        if total_cost > self._capital:
            # Reduce qty to fit
            qty = int(self._capital / cost_per_share)
            if qty <= 0:
                return
            total_cost = calc_buy_cost(price, qty, self._cost_config)

        # Deduct from capital
        self._capital -= total_cost

        # Add position
        self._positions[signal.code] = {
            "qty": qty,
            "avg_price": price,
            "highest_price": price,
        }

        # Record trade
        trade = TradeRecord(
            timestamp=candle.timestamp,
            code=signal.code,
            side="BUY",
            strategy=signal.strategy_name,
            price=price,
            qty=qty,
            amount=total_cost,
            pnl=0,
            pnl_pct=0.0,
            balance=int(self._capital),
            reason=signal.reason,
        )
        self._trades.append(trade)
        logger.debug(f"[BT BUY] {signal.code} qty={qty} price={price} cost={total_cost}")

    def _execute_sell(
        self, code: str, price: int, reason: str, candle: Candle
    ) -> None:
        """Execute a sell trade with cost modeling.

        Computes P&L including commission + tax + slippage.

        Args:
            code: Stock code.
            price: Sell price.
            reason: Reason for sale.
            candle: Current candle data.
        """
        if code not in self._positions:
            return

        pos = self._positions[code]
        qty = pos["qty"]
        avg_price = pos["avg_price"]

        # Calculate net proceeds
        proceeds = calc_sell_proceeds(price, qty, self._cost_config)

        # Calculate P&L
        buy_cost = calc_buy_cost(avg_price, qty, self._cost_config)
        pnl = proceeds - buy_cost
        pnl_pct = (pnl / buy_cost * 100) if buy_cost > 0 else 0.0

        # Add proceeds to capital
        self._capital += proceeds

        # Track daily P&L
        day = candle.timestamp.date()
        self._daily_pnl[day] = self._daily_pnl.get(day, 0.0) + pnl

        # Remove position
        del self._positions[code]

        # Record trade
        trade = TradeRecord(
            timestamp=candle.timestamp,
            code=code,
            side="SELL",
            strategy="backtest",
            price=price,
            qty=qty,
            amount=proceeds,
            pnl=int(pnl),
            pnl_pct=round(pnl_pct, 2),
            balance=int(self._capital),
            reason=reason,
        )
        self._trades.append(trade)
        logger.debug(f"[BT SELL] {code} qty={qty} price={price} pnl={pnl:.0f}")

    def _check_risk_triggers(self, candle: Candle) -> None:
        """Check SL/TP/trailing stop for positions matching candle's code.

        Updates highest_price tracking for trailing stop.

        Args:
            candle: Current candle data.
        """
        code = candle.code
        if code not in self._positions:
            return

        pos = self._positions[code]
        avg_price = pos["avg_price"]
        highest = pos["highest_price"]
        close = candle.close

        # Update highest price for trailing stop
        if close > highest:
            pos["highest_price"] = close

        # Stop Loss: close <= avg_price * (1 + stop_loss_pct/100)
        # Note: stop_loss_pct is negative (e.g., -2.0)
        sl_price = avg_price * (1 + self._risk_config.stop_loss_pct / 100)
        if close <= sl_price:
            self._execute_sell(code, close, "Stop loss triggered", candle)
            return

        # Take Profit: close >= avg_price * (1 + take_profit_pct/100)
        tp_price = avg_price * (1 + self._risk_config.take_profit_pct / 100)
        if close >= tp_price:
            self._execute_sell(code, close, "Take profit triggered", candle)
            return

        # Trailing Stop: close <= highest * (1 - trailing_stop_pct/100)
        # Only active when price has moved above avg_price
        ts_price = pos["highest_price"] * (1 - self._risk_config.trailing_stop_pct / 100)
        if close <= ts_price and pos["highest_price"] > avg_price:
            self._execute_sell(code, close, "Trailing stop triggered", candle)
            return

    def _check_daily_loss(self, today: date) -> bool:
        """Check if daily realized loss exceeds the limit.

        Args:
            today: Current trading date.

        Returns:
            True if daily loss limit exceeded (buys should be blocked).
        """
        daily_loss = self._daily_pnl.get(today, 0.0)
        limit = self._initial_capital * self._risk_config.daily_loss_limit_pct / 100
        return daily_loss < -limit

    def _close_all_positions(self, last_candle: Candle) -> None:
        """Force close all remaining positions at the last candle's close price.

        Args:
            last_candle: The final candle in the backtest.
        """
        codes = list(self._positions.keys())
        for code in codes:
            self._execute_sell(
                code, last_candle.close, "Backtest end - forced close", last_candle
            )

    def _record_equity(self, candle: Candle) -> None:
        """Record current total equity (capital + position market values).

        Args:
            candle: Current candle for market price reference.
        """
        equity = self._capital
        for code, pos in self._positions.items():
            # Use candle.close as current price for matching code
            if code == candle.code:
                equity += pos["qty"] * candle.close
            else:
                # For other codes, use avg_price as approximation
                equity += pos["qty"] * pos["avg_price"]
        self._equity_curve.append((candle.timestamp, equity))

    def _build_result(self) -> BacktestResult:
        """Construct BacktestResult from collected data.

        Returns:
            BacktestResult with trades, equity curve, capital, and basic metrics.
        """
        total_trades = len(self._trades)
        sell_trades = [t for t in self._trades if t.side == "SELL"]

        return BacktestResult(
            trades=self._trades,
            equity_curve=self._equity_curve,
            initial_capital=self._initial_capital,
            final_capital=self._capital,
            total_trades=total_trades,
            total_return_pct=(
                (self._capital - self._initial_capital) / self._initial_capital * 100
                if self._initial_capital > 0
                else 0.0
            ),
            win_rate_pct=(
                sum(1 for t in sell_trades if t.pnl > 0) / len(sell_trades) * 100
                if sell_trades
                else 0.0
            ),
        )
