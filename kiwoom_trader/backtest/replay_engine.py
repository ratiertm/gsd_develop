"""ReplayEngine: replays collected tick data through the live pipeline.

Reads tick data from SQLite DB (체결 table), feeds through CandleAggregator
→ StrategyManager → BacktestEngine trade simulation. This ensures strategies
are tested with the exact same code path as live trading.

Usage:
    engine = ReplayEngine(strategy_configs, risk_config)
    result = engine.run("data/realtime_20260317.db")
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from loguru import logger

from kiwoom_trader.backtest.cost_model import CostConfig, calc_buy_cost, calc_sell_proceeds
from kiwoom_trader.core.candle_aggregator import CandleAggregator
from kiwoom_trader.core.condition_engine import ConditionEngine
from kiwoom_trader.core.models import (
    BacktestResult,
    Candle,
    RiskConfig,
    Signal,
    TradeRecord,
)
from kiwoom_trader.core.strategy_manager import StrategyManager


class ReplayEngine:
    """Replays collected tick data through CandleAggregator → StrategyManager.

    Unlike BacktestEngine which consumes pre-built candles, ReplayEngine
    starts from raw ticks — the same entry point as live trading.

    Args:
        strategy_configs: Strategy configuration dict.
        risk_config: RiskConfig for SL/TP/trailing stop.
        cost_config: CostConfig for commission/tax/slippage.
        initial_capital: Starting capital in KRW.
        candle_interval: Candle interval in minutes (default 1).
    """

    def __init__(
        self,
        strategy_configs: dict,
        risk_config: RiskConfig | None = None,
        cost_config: CostConfig | None = None,
        initial_capital: int = 10_000_000,
        candle_interval: int = 1,
    ) -> None:
        self._strategy_configs = strategy_configs
        self._risk_config = risk_config or RiskConfig()
        self._cost_config = cost_config or CostConfig()
        self._initial_capital = initial_capital
        self._candle_interval = candle_interval

        # Per-run state
        self._capital: float = 0.0
        self._positions: dict[str, dict] = {}
        self._trades: list[TradeRecord] = []
        self._equity_curve: list[tuple[datetime, float]] = []
        self._daily_pnl: dict = {}
        self._candles_generated: int = 0
        self._ticks_processed: int = 0

    def run(
        self,
        db_path: str | Path,
        codes: list[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        speed: float = 0,
        on_progress: Callable[[int, int], None] | None = None,
        on_candle: Callable[[str, Candle], None] | None = None,
        on_signal: Callable[[Signal], None] | None = None,
    ) -> BacktestResult:
        """Run tick replay simulation.

        Args:
            db_path: Path to SQLite DB with 체결 table.
            codes: Stock codes to replay (None = all codes in DB).
            start_time: Start time filter "HH:MM:SS" (None = from beginning).
            end_time: End time filter "HH:MM:SS" (None = until end).
            speed: Replay speed multiplier. 0 = max speed (no delay).
            on_progress: Callback(ticks_processed, total_ticks).
            on_candle: Callback(code, candle) for each completed candle.
            on_signal: Callback(signal) for each generated signal.

        Returns:
            BacktestResult with trades, equity curve, and metrics.
        """
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"DB not found: {db_path}")

        # Reset state
        self._capital = float(self._initial_capital)
        self._positions = {}
        self._trades = []
        self._equity_curve = []
        self._daily_pnl = {}
        self._candles_generated = 0
        self._ticks_processed = 0

        # Detect replay date from DB
        replay_date = self._detect_date(db_path)

        # Setup CandleAggregator with replay date
        aggregator = CandleAggregator(
            interval_minutes=self._candle_interval,
            replay_date=replay_date,
        )

        # Setup StrategyManager
        condition_engine = ConditionEngine()
        strategy_manager = StrategyManager(
            condition_engine=condition_engine,
            risk_manager=None,
            order_manager=None,
            config=self._strategy_configs,
        )

        # Candle handler: run strategy + trade logic on each completed candle
        def handle_candle(code: str, candle: Candle) -> None:
            self._candles_generated += 1

            if on_candle:
                on_candle(code, candle)

            # Feed to strategy
            signals = strategy_manager.on_candle_complete(code, candle)
            for sig in signals:
                if on_signal:
                    on_signal(sig)
                if sig.side == "BUY":
                    if self._check_daily_loss(candle.timestamp.date()):
                        logger.debug(f"[REPLAY] Daily loss limit hit, skipping BUY {sig.code}")
                    else:
                        self._execute_buy(sig, candle)
                elif sig.side == "SELL":
                    self._execute_sell(sig.code, sig.price, sig.reason, candle)

            # Risk triggers
            self._check_risk_triggers(candle)

            # Equity snapshot
            self._record_equity(candle)

        aggregator.register_callback(handle_candle)

        # Load and replay ticks
        total_ticks = self._count_ticks(db_path, codes, start_time, end_time)
        logger.info(f"Replaying {total_ticks:,} ticks from {db_path.name}")

        tick_delay = 1.0 / speed if speed > 0 else 0

        for i, (code, fid_dict) in enumerate(
            self._iter_ticks(db_path, codes, start_time, end_time)
        ):
            aggregator.on_tick(code, fid_dict)
            self._ticks_processed = i + 1

            if tick_delay > 0:
                time.sleep(tick_delay)

            if on_progress and (i + 1) % 10000 == 0:
                on_progress(i + 1, total_ticks)

        # Flush remaining partial candles
        aggregator.flush()

        # Report final progress
        if on_progress:
            on_progress(total_ticks, total_ticks)

        # Force close all positions
        if self._equity_curve:
            last_ts = self._equity_curve[-1][0]
            for code in list(self._positions):
                pos = self._positions[code]
                dummy_candle = Candle(
                    code=code,
                    open=pos["avg_price"],
                    high=pos["avg_price"],
                    low=pos["avg_price"],
                    close=pos["avg_price"],
                    volume=0,
                    timestamp=last_ts,
                )
                self._execute_sell(code, pos["avg_price"], "Replay end - forced close", dummy_candle)

        result = self._build_result()
        logger.info(
            f"Replay complete: {self._ticks_processed:,} ticks → "
            f"{self._candles_generated:,} candles → "
            f"{result.total_trades} trades, "
            f"return={result.total_return_pct:+.2f}%"
        )
        return result

    # ── Data loading ─────────────────────────────────────────

    def _detect_date(self, db_path: Path) -> datetime:
        """Detect the trading date from the first tick timestamp."""
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT timestamp FROM 체결 ORDER BY timestamp LIMIT 1"
            ).fetchone()
            if row:
                ts = datetime.fromisoformat(row[0].split(".")[0])
                return ts.replace(hour=0, minute=0, second=0, microsecond=0)
        finally:
            conn.close()
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def _count_ticks(
        self,
        db_path: Path,
        codes: list[str] | None,
        start_time: str | None,
        end_time: str | None,
    ) -> int:
        """Count total ticks matching the filters."""
        conn = sqlite3.connect(str(db_path))
        try:
            query = "SELECT COUNT(*) FROM 체결"
            conditions, params = self._build_where(codes, start_time, end_time)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            return conn.execute(query, params).fetchone()[0]
        finally:
            conn.close()

    def _iter_ticks(
        self,
        db_path: Path,
        codes: list[str] | None,
        start_time: str | None,
        end_time: str | None,
    ):
        """Iterate ticks from SQLite DB, yielding (code, fid_dict) tuples.

        fid_dict maps int FID → str value, matching CandleAggregator.on_tick() format.
        """
        conn = sqlite3.connect(str(db_path))
        try:
            # Get column info
            cursor = conn.execute("PRAGMA table_info(체결)")
            columns = [(row[1], row[0]) for row in cursor.fetchall()]
            col_names = [c[0] for c in columns]

            # Build FID column mapping: column_index -> FID int
            fid_cols: list[tuple[int, int]] = []
            code_idx = col_names.index("code")
            for i, name in enumerate(col_names):
                if name.startswith("fid_"):
                    fid_num = int(name[4:])
                    fid_cols.append((i, fid_num))

            # Query ticks
            query = "SELECT * FROM 체결"
            conditions, params = self._build_where(codes, start_time, end_time)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY timestamp, id"

            cursor = conn.execute(query, params)
            while True:
                rows = cursor.fetchmany(5000)
                if not rows:
                    break
                for row in rows:
                    code = row[code_idx]
                    fid_dict = {}
                    for col_idx, fid_num in fid_cols:
                        val = row[col_idx]
                        if val is not None:
                            fid_dict[fid_num] = str(val)
                    yield code, fid_dict
        finally:
            conn.close()

    def _build_where(
        self,
        codes: list[str] | None,
        start_time: str | None,
        end_time: str | None,
    ) -> tuple[list[str], list]:
        """Build WHERE clause parts from filters."""
        conditions: list[str] = []
        params: list = []

        if codes:
            placeholders = ",".join("?" for _ in codes)
            conditions.append(f"code IN ({placeholders})")
            params.extend(codes)

        if start_time:
            conditions.append("substr(fid_20, 1, 2) || ':' || substr(fid_20, 3, 2) || ':' || substr(fid_20, 5, 2) >= ?")
            params.append(start_time)

        if end_time:
            conditions.append("substr(fid_20, 1, 2) || ':' || substr(fid_20, 3, 2) || ':' || substr(fid_20, 5, 2) <= ?")
            params.append(end_time)

        return conditions, params

    # ── Trade execution (same as BacktestEngine) ─────────────

    def _execute_buy(self, signal: Signal, candle: Candle) -> None:
        if len(self._positions) >= self._risk_config.max_positions:
            return
        if signal.code in self._positions:
            return

        price = signal.price
        if price <= 0:
            return

        max_amount = self._capital * self._risk_config.max_symbol_weight_pct / 100
        cost_per_share = calc_buy_cost(price, 1, self._cost_config)
        if cost_per_share <= 0:
            return
        qty = int(max_amount / cost_per_share)
        if qty <= 0:
            return

        total_cost = calc_buy_cost(price, qty, self._cost_config)
        if total_cost > self._capital:
            qty = int(self._capital / cost_per_share)
            if qty <= 0:
                return
            total_cost = calc_buy_cost(price, qty, self._cost_config)

        self._capital -= total_cost
        self._positions[signal.code] = {
            "qty": qty,
            "avg_price": price,
            "highest_price": price,
        }
        self._trades.append(TradeRecord(
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
        ))
        logger.debug(f"[REPLAY BUY] {signal.code} qty={qty} price={price}")

    def _execute_sell(self, code: str, price: int, reason: str, candle: Candle) -> None:
        if code not in self._positions:
            return

        pos = self._positions[code]
        qty = pos["qty"]
        avg_price = pos["avg_price"]

        proceeds = calc_sell_proceeds(price, qty, self._cost_config)
        buy_cost = calc_buy_cost(avg_price, qty, self._cost_config)
        pnl = proceeds - buy_cost
        pnl_pct = (pnl / buy_cost * 100) if buy_cost > 0 else 0.0

        self._capital += proceeds

        day = candle.timestamp.date()
        self._daily_pnl[day] = self._daily_pnl.get(day, 0.0) + pnl

        del self._positions[code]

        self._trades.append(TradeRecord(
            timestamp=candle.timestamp,
            code=code,
            side="SELL",
            strategy="replay",
            price=price,
            qty=qty,
            amount=proceeds,
            pnl=int(pnl),
            pnl_pct=round(pnl_pct, 2),
            balance=int(self._capital),
            reason=reason,
        ))
        logger.debug(f"[REPLAY SELL] {code} qty={qty} price={price} pnl={pnl:.0f}")

    def _check_risk_triggers(self, candle: Candle) -> None:
        code = candle.code
        if code not in self._positions:
            return

        pos = self._positions[code]
        avg_price = pos["avg_price"]
        close = candle.close

        if close > pos["highest_price"]:
            pos["highest_price"] = close

        sl_price = avg_price * (1 + self._risk_config.stop_loss_pct / 100)
        if close <= sl_price:
            self._execute_sell(code, close, "Stop loss triggered", candle)
            return

        tp_price = avg_price * (1 + self._risk_config.take_profit_pct / 100)
        if close >= tp_price:
            self._execute_sell(code, close, "Take profit triggered", candle)
            return

        ts_price = pos["highest_price"] * (1 - self._risk_config.trailing_stop_pct / 100)
        if close <= ts_price and pos["highest_price"] > avg_price:
            self._execute_sell(code, close, "Trailing stop triggered", candle)

    def _check_daily_loss(self, today) -> bool:
        daily_loss = self._daily_pnl.get(today, 0.0)
        limit = self._initial_capital * self._risk_config.daily_loss_limit_pct / 100
        return daily_loss < -limit

    def _record_equity(self, candle: Candle) -> None:
        equity = self._capital
        for code, pos in self._positions.items():
            if code == candle.code:
                equity += pos["qty"] * candle.close
            else:
                equity += pos["qty"] * pos["avg_price"]
        self._equity_curve.append((candle.timestamp, equity))

    def _build_result(self) -> BacktestResult:
        sell_trades = [t for t in self._trades if t.side == "SELL"]
        return BacktestResult(
            trades=self._trades,
            equity_curve=self._equity_curve,
            initial_capital=self._initial_capital,
            final_capital=self._capital,
            total_trades=len(self._trades),
            total_return_pct=(
                (self._capital - self._initial_capital) / self._initial_capital * 100
                if self._initial_capital > 0 else 0.0
            ),
            win_rate_pct=(
                sum(1 for t in sell_trades if t.pnl > 0) / len(sell_trades) * 100
                if sell_trades else 0.0
            ),
        )
