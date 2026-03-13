"""Paper trading: virtual trade execution with CSV logging and P&L tracking.

Simulates order execution without submitting real orders. Records all trades
to a CSV file for analysis and tracks virtual positions and balance.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime

from loguru import logger

from kiwoom_trader.core.models import Signal, TradeRecord

CSV_COLUMNS = [
    "timestamp", "code", "side", "strategy", "price", "qty",
    "amount", "pnl", "pnl_pct", "balance", "reason",
]


class PaperTrader:
    """Virtual trade execution with CSV logging.

    Args:
        csv_path: Path to CSV trade log file.
        initial_capital: Starting capital in KRW (default 10,000,000).
        max_symbol_weight_pct: Max percentage of capital per symbol (default 20.0).
    """

    def __init__(
        self,
        csv_path: str = "trades.csv",
        initial_capital: int = 10_000_000,
        max_symbol_weight_pct: float = 20.0,
    ) -> None:
        self._csv_path = csv_path
        self._initial_capital = initial_capital
        self._capital = initial_capital
        self._max_weight_pct = max_symbol_weight_pct

        # Virtual positions: {code: {"qty": int, "avg_price": int}}
        self.positions: dict[str, dict] = {}

        # Trade history for summary
        self._trades: list[TradeRecord] = []

        # Initialize CSV
        self._init_csv()

    def _init_csv(self) -> None:
        """Create CSV with header row if file doesn't exist."""
        if not os.path.exists(self._csv_path):
            with open(self._csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_COLUMNS)

    def execute_signal(self, signal: Signal) -> None:
        """Execute a virtual trade based on the signal.

        BUY: Calculate qty based on capital weight, add to virtual position.
        SELL: Close virtual position, compute realized P&L.
        """
        if signal.side == "BUY":
            self._execute_buy(signal)
        elif signal.side == "SELL":
            self._execute_sell(signal)

    def _execute_buy(self, signal: Signal) -> None:
        """Execute virtual buy order."""
        if signal.price <= 0:
            logger.warning(f"Invalid price {signal.price} for {signal.code}")
            return

        # Calculate qty: (capital * weight_pct%) / price
        max_amount = self._capital * self._max_weight_pct / 100.0
        qty = int(max_amount / signal.price)

        if qty <= 0:
            logger.info(f"Insufficient capital for {signal.code} at {signal.price}")
            return

        amount = qty * signal.price

        # Update position
        if signal.code in self.positions and self.positions[signal.code]["qty"] > 0:
            pos = self.positions[signal.code]
            total_qty = pos["qty"] + qty
            pos["avg_price"] = int(
                (pos["avg_price"] * pos["qty"] + signal.price * qty) / total_qty
            )
            pos["qty"] = total_qty
        else:
            self.positions[signal.code] = {"qty": qty, "avg_price": signal.price}

        self._capital -= amount

        record = TradeRecord(
            timestamp=signal.timestamp,
            code=signal.code,
            side="BUY",
            strategy=signal.strategy_name,
            price=signal.price,
            qty=qty,
            amount=amount,
            pnl=0,
            pnl_pct=0.0,
            balance=self._capital,
            reason=signal.reason,
        )
        self._trades.append(record)
        self._write_trade(record)
        logger.info(f"[PAPER BUY] {signal.code} qty={qty} price={signal.price} amount={amount}")

    def _execute_sell(self, signal: Signal) -> None:
        """Execute virtual sell order, computing realized P&L."""
        if signal.code not in self.positions or self.positions[signal.code]["qty"] <= 0:
            logger.info(f"No position to sell for {signal.code}")
            return

        pos = self.positions[signal.code]
        qty = pos["qty"]
        avg_price = pos["avg_price"]
        amount = qty * signal.price
        pnl = (signal.price - avg_price) * qty
        pnl_pct = ((signal.price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0

        self._capital += amount

        # Close position
        pos["qty"] = 0
        del self.positions[signal.code]

        record = TradeRecord(
            timestamp=signal.timestamp,
            code=signal.code,
            side="SELL",
            strategy=signal.strategy_name,
            price=signal.price,
            qty=qty,
            amount=amount,
            pnl=pnl,
            pnl_pct=round(pnl_pct, 2),
            balance=self._capital,
            reason=signal.reason,
        )
        self._trades.append(record)
        self._write_trade(record)
        logger.info(
            f"[PAPER SELL] {signal.code} qty={qty} price={signal.price} "
            f"pnl={pnl} ({pnl_pct:.2f}%)"
        )

    def _write_trade(self, record: TradeRecord) -> None:
        """Append a trade record row to CSV."""
        with open(self._csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                record.timestamp.isoformat(),
                record.code,
                record.side,
                record.strategy,
                record.price,
                record.qty,
                record.amount,
                record.pnl,
                record.pnl_pct,
                record.balance,
                record.reason,
            ])

    def get_summary(self) -> dict:
        """Return summary statistics of all trades.

        Returns:
            Dict with total_trades, total_pnl, win_rate keys.
        """
        total_trades = len(self._trades)
        sell_trades = [t for t in self._trades if t.side == "SELL"]
        total_pnl = sum(t.pnl for t in sell_trades)
        winning = sum(1 for t in sell_trades if t.pnl > 0)
        win_rate = (winning / len(sell_trades) * 100) if sell_trades else 0.0

        return {
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "win_rate": round(win_rate, 2),
        }
