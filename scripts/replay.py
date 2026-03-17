"""CLI script to replay collected tick data through trading strategies.

Usage:
    # Replay with default config
    .venv32\\Scripts\\python.exe scripts/replay.py data/realtime_20260317.db

    # Replay specific codes with time range
    .venv32\\Scripts\\python.exe scripts/replay.py data/realtime_20260317.db \\
        --codes 005930,000660 --start 09:00:00 --end 15:00:00

    # Replay with custom capital and candle interval
    .venv32\\Scripts\\python.exe scripts/replay.py data/realtime_20260317.db \\
        --capital 50000000 --interval 3

    # Also works with 64-bit Python (no COM needed)
    python scripts/replay.py data/realtime_20260317.db
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from kiwoom_trader.backtest.cost_model import CostConfig
from kiwoom_trader.backtest.performance import compute_all_metrics
from kiwoom_trader.backtest.replay_engine import ReplayEngine
from kiwoom_trader.core.models import RiskConfig


def load_config(config_path: Path) -> dict:
    """Load config.json for strategy settings."""
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def build_default_strategy_configs() -> dict:
    """Build a simple MA crossover strategy for replay testing."""
    return {
        "mode": "paper",
        "strategies": [
            {
                "name": "MA_CROSSOVER",
                "enabled": True,
                "priority": 1,
                "indicators": {
                    "ema_short": {"type": "ema", "period": 5},
                    "ema_long": {"type": "ema", "period": 20},
                    "rsi": {"type": "rsi", "period": 14},
                },
                "entry_rule": {
                    "logic": "AND",
                    "conditions": [
                        {"indicator": "ema_short", "operator": "cross_above", "value_ref": "ema_long"},
                        {"indicator": "rsi", "operator": "lt", "value": 70},
                    ],
                },
                "exit_rule": {
                    "logic": "OR",
                    "conditions": [
                        {"indicator": "ema_short", "operator": "cross_below", "value_ref": "ema_long"},
                        {"indicator": "rsi", "operator": "gt", "value": 80},
                    ],
                },
                "cooldown_sec": 300,
            }
        ],
        "watchlist_strategies": {},  # Will be populated dynamically
    }


def print_result(result, ticks: int, candles: int) -> None:
    """Print replay results in a formatted table."""
    print("\n" + "=" * 60)
    print("  REPLAY RESULT")
    print("=" * 60)

    print(f"\n  Data: {ticks:,} ticks → {candles:,} candles")
    print(f"  Capital: {result.initial_capital:,.0f} → {result.final_capital:,.0f} KRW")
    print(f"  Return: {result.total_return_pct:+.2f}%")
    print(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")

    print(f"\n  Trades: {result.total_trades}")
    print(f"  Win Rate: {result.win_rate_pct:.1f}%")
    print(f"  Profit Factor: {result.profit_factor:.2f}")
    print(f"  Avg P&L: {result.avg_pnl:,.0f} KRW")
    print(f"  Max Consec. Losses: {result.max_consecutive_losses}")
    print(f"  Avg Holding Period: {result.avg_holding_periods:.2f} days")

    if result.trades:
        print(f"\n  {'Time':<20} {'Code':<8} {'Side':<5} {'Price':>10} {'Qty':>6} {'P&L':>12} {'Reason'}")
        print("  " + "-" * 85)
        for t in result.trades:
            pnl_str = f"{t.pnl:+,}" if t.side == "SELL" else ""
            print(
                f"  {t.timestamp.strftime('%H:%M:%S'):<20} "
                f"{t.code:<8} {t.side:<5} {t.price:>10,} {t.qty:>6} "
                f"{pnl_str:>12} {t.reason}"
            )

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Replay collected tick data")
    parser.add_argument("db_path", help="Path to SQLite DB file")
    parser.add_argument("--codes", help="Comma-separated stock codes (default: all)")
    parser.add_argument("--start", help="Start time HH:MM:SS (default: market open)")
    parser.add_argument("--end", help="End time HH:MM:SS (default: market close)")
    parser.add_argument("--capital", type=int, default=10_000_000, help="Initial capital (default: 10M)")
    parser.add_argument("--interval", type=int, default=1, help="Candle interval minutes (default: 1)")
    parser.add_argument("--config", help="Path to config.json for strategy settings")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Logging
    logger.remove()
    if args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")

    # Strategy config
    if args.config:
        config = load_config(Path(args.config))
        strategy_configs = config.get("strategy", build_default_strategy_configs())
    else:
        strategy_configs = build_default_strategy_configs()

    # Auto-populate watchlist_strategies with all codes if empty
    codes = args.codes.split(",") if args.codes else None
    if not strategy_configs.get("watchlist_strategies"):
        # Discover codes from DB
        import sqlite3
        conn = sqlite3.connect(args.db_path)
        all_codes = [row[0] for row in conn.execute("SELECT DISTINCT code FROM 체결").fetchall()]
        conn.close()

        if codes:
            all_codes = [c for c in all_codes if c in codes]

        strategy_names = [s["name"] for s in strategy_configs.get("strategies", [])]
        strategy_configs["watchlist_strategies"] = {
            code: strategy_names for code in all_codes
        }

    # Build engine
    engine = ReplayEngine(
        strategy_configs=strategy_configs,
        risk_config=RiskConfig(),
        cost_config=CostConfig(),
        initial_capital=args.capital,
        candle_interval=args.interval,
    )

    # Progress display
    def show_progress(current, total):
        pct = current / total * 100 if total > 0 else 0
        bar_len = 30
        filled = int(bar_len * current / total) if total > 0 else 0
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"\r  [{bar}] {pct:.1f}% ({current:,}/{total:,} ticks)", end="", flush=True)

    print(f"\n  Replaying: {args.db_path}")
    if codes:
        print(f"  Codes: {', '.join(codes)}")
    if args.start or args.end:
        print(f"  Time: {args.start or 'start'} ~ {args.end or 'end'}")

    # Run
    result = engine.run(
        db_path=args.db_path,
        codes=codes,
        start_time=args.start,
        end_time=args.end,
        on_progress=show_progress,
    )

    print()  # newline after progress bar

    # Compute full metrics
    compute_all_metrics(result)

    # Print results
    print_result(result, engine._ticks_processed, engine._candles_generated)


if __name__ == "__main__":
    main()
