"""Tests for ReplayEngine — tick-level replay through CandleAggregator pipeline.

No COM or PyQt5 dependency. Uses an in-memory SQLite DB with sample tick data.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from kiwoom_trader.backtest.cost_model import CostConfig
from kiwoom_trader.backtest.replay_engine import ReplayEngine
from kiwoom_trader.core.candle_aggregator import CandleAggregator
from kiwoom_trader.core.models import Candle, RiskConfig


# ── Fixtures ──────────────────────────────────────────────


def _create_test_db(path: Path, ticks: list[dict]) -> None:
    """Create a minimal 체결 SQLite DB for testing."""
    conn = sqlite3.connect(str(path))
    conn.execute(
        """CREATE TABLE 체결 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            real_type TEXT,
            fid_20 TEXT,
            fid_10 TEXT,
            fid_15 TEXT,
            fid_13 TEXT
        )"""
    )
    conn.execute("CREATE INDEX idx_체결_code_ts ON 체결(code, timestamp)")
    for tick in ticks:
        conn.execute(
            "INSERT INTO 체결 (timestamp, code, name, real_type, fid_20, fid_10, fid_15, fid_13) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tick["timestamp"],
                tick["code"],
                tick.get("name", "테스트"),
                "주식체결",
                tick["exec_time"],  # fid_20
                str(tick["price"]),  # fid_10
                str(tick["volume"]),  # fid_15
                str(tick.get("cum_volume", 0)),  # fid_13
            ),
        )
    conn.commit()
    conn.close()


def _make_ticks(code: str, base_time: str, prices: list[int], volumes: list[int]) -> list[dict]:
    """Generate tick dicts with sequential timestamps within the same minute."""
    ticks = []
    hh = int(base_time[:2])
    mm = int(base_time[2:4])
    for i, (price, vol) in enumerate(zip(prices, volumes)):
        ss = min(i, 59)
        exec_time = f"{hh:02d}{mm:02d}{ss:02d}"
        ts = f"2026-03-17 {hh:02d}:{mm:02d}:{ss:02d}.000"
        ticks.append({
            "timestamp": ts,
            "code": code,
            "exec_time": exec_time,
            "price": price,
            "volume": vol,
        })
    return ticks


SIMPLE_STRATEGY = {
    "mode": "paper",
    "strategies": [
        {
            "name": "TEST_MA",
            "enabled": True,
            "priority": 1,
            "indicators": {
                "ema_short": {"type": "ema", "period": 3},
                "ema_long": {"type": "ema", "period": 5},
            },
            "entry_rule": {
                "logic": "AND",
                "conditions": [
                    {"indicator": "ema_short", "operator": "cross_above", "value": 0},
                ],
            },
            "exit_rule": {
                "logic": "AND",
                "conditions": [
                    {"indicator": "ema_short", "operator": "cross_below", "value": 0},
                ],
            },
            "cooldown_sec": 0,
        }
    ],
    "watchlist_strategies": {"005930": ["TEST_MA"]},
}


# ── CandleAggregator replay_date tests ───────────────────


class TestCandleAggregatorReplay:
    def test_replay_timestamp_from_exec_time(self):
        """Candle timestamp should use replay_date + exec_time, not datetime.now()."""
        replay_date = datetime(2026, 3, 17)
        agg = CandleAggregator(interval_minutes=1, replay_date=replay_date)

        candles: list[Candle] = []
        agg.register_callback(lambda code, candle: candles.append(candle))

        # Two ticks in minute 0 (09:00), then one in minute 1 (09:01) to trigger emit
        agg.on_tick("005930", {20: "090000", 10: "50000", 15: "100"})
        agg.on_tick("005930", {20: "090030", 10: "50100", 15: "200"})
        agg.on_tick("005930", {20: "090100", 10: "50200", 15: "150"})

        assert len(candles) == 1
        c = candles[0]
        assert c.timestamp.year == 2026
        assert c.timestamp.month == 3
        assert c.timestamp.day == 17
        assert c.timestamp.hour == 9
        assert c.timestamp.minute == 0

    def test_flush_emits_remaining(self):
        """flush() should emit the last partial candle."""
        agg = CandleAggregator(interval_minutes=1, replay_date=datetime(2026, 3, 17))

        candles: list[Candle] = []
        agg.register_callback(lambda code, candle: candles.append(candle))

        agg.on_tick("005930", {20: "090000", 10: "50000", 15: "100"})
        assert len(candles) == 0

        agg.flush()
        assert len(candles) == 1

    def test_live_mode_uses_now(self):
        """Without replay_date, timestamp should be close to now."""
        agg = CandleAggregator(interval_minutes=1)

        candles: list[Candle] = []
        agg.register_callback(lambda code, candle: candles.append(candle))

        agg.on_tick("005930", {20: "090000", 10: "50000", 15: "100"})
        agg.on_tick("005930", {20: "090100", 10: "50100", 15: "200"})

        assert len(candles) == 1
        # Timestamp should be today, not 2026-03-17
        assert candles[0].timestamp.date() == datetime.now().date()

    def test_ohlcv_values(self):
        """OHLCV should be correctly aggregated from ticks."""
        agg = CandleAggregator(interval_minutes=1, replay_date=datetime(2026, 3, 17))

        candles: list[Candle] = []
        agg.register_callback(lambda code, candle: candles.append(candle))

        agg.on_tick("005930", {20: "090000", 10: "50000", 15: "100"})
        agg.on_tick("005930", {20: "090010", 10: "50500", 15: "200"})  # high
        agg.on_tick("005930", {20: "090020", 10: "49800", 15: "150"})  # low
        agg.on_tick("005930", {20: "090030", 10: "50200", 15: "50"})   # close
        # Trigger emit
        agg.on_tick("005930", {20: "090100", 10: "50300", 15: "100"})

        c = candles[0]
        assert c.open == 50000
        assert c.high == 50500
        assert c.low == 49800
        assert c.close == 50200
        assert c.volume == 500  # 100+200+150+50

    def test_multiple_codes(self):
        """Each code should have independent candle building."""
        agg = CandleAggregator(interval_minutes=1, replay_date=datetime(2026, 3, 17))

        candles: list[Candle] = []
        agg.register_callback(lambda code, candle: candles.append(candle))

        agg.on_tick("005930", {20: "090000", 10: "50000", 15: "100"})
        agg.on_tick("000660", {20: "090000", 10: "100000", 15: "50"})
        agg.on_tick("005930", {20: "090100", 10: "50100", 15: "200"})
        agg.on_tick("000660", {20: "090100", 10: "100200", 15: "60"})

        assert len(candles) == 2
        codes = {c.code for c in candles}
        assert codes == {"005930", "000660"}


# ── ReplayEngine tests ───────────────────────────────────


class TestReplayEngine:
    def test_basic_replay(self, tmp_path):
        """Replay should process ticks and generate candles without errors."""
        # Create ticks spanning multiple minutes
        ticks = []
        for minute in range(10):
            ticks.extend(
                _make_ticks(
                    "005930",
                    f"09{minute:02d}",
                    [50000 + minute * 100] * 3,
                    [100, 200, 150],
                )
            )

        db_path = tmp_path / "test.db"
        _create_test_db(db_path, ticks)

        engine = ReplayEngine(
            strategy_configs=SIMPLE_STRATEGY,
            initial_capital=10_000_000,
            candle_interval=1,
        )
        result = engine.run(db_path)

        assert result.initial_capital == 10_000_000
        assert engine._ticks_processed == len(ticks)
        assert engine._candles_generated > 0

    def test_empty_db(self, tmp_path):
        """Replay on empty DB should return zero-trade result."""
        db_path = tmp_path / "empty.db"
        _create_test_db(db_path, [])

        engine = ReplayEngine(
            strategy_configs=SIMPLE_STRATEGY,
            initial_capital=10_000_000,
        )
        result = engine.run(db_path)

        assert result.total_trades == 0
        assert result.final_capital == 10_000_000

    def test_code_filter(self, tmp_path):
        """Replay with code filter should only process matching codes."""
        ticks = []
        for minute in range(5):
            ticks.extend(_make_ticks("005930", f"09{minute:02d}", [50000] * 2, [100, 200]))
            ticks.extend(_make_ticks("000660", f"09{minute:02d}", [100000] * 2, [50, 60]))

        db_path = tmp_path / "multi.db"
        _create_test_db(db_path, ticks)

        engine = ReplayEngine(
            strategy_configs=SIMPLE_STRATEGY,
            initial_capital=10_000_000,
        )

        candles_seen: list[str] = []
        result = engine.run(
            db_path,
            codes=["005930"],
            on_candle=lambda code, candle: candles_seen.append(code),
        )

        # All candles should be 005930 only
        assert all(c == "005930" for c in candles_seen)

    def test_progress_callback(self, tmp_path):
        """Progress callback should be called during replay."""
        ticks = _make_ticks("005930", "0900", [50000] * 20000, [100] * 20000)
        db_path = tmp_path / "progress.db"
        _create_test_db(db_path, ticks)

        engine = ReplayEngine(
            strategy_configs=SIMPLE_STRATEGY,
            initial_capital=10_000_000,
        )

        progress_calls = []
        result = engine.run(
            db_path,
            on_progress=lambda cur, tot: progress_calls.append((cur, tot)),
        )

        assert len(progress_calls) > 0
        # Last progress should have current == total
        assert progress_calls[-1][0] == progress_calls[-1][1]

    def test_candle_callback(self, tmp_path):
        """on_candle callback should fire for each completed candle."""
        ticks = []
        for minute in range(5):
            ticks.extend(_make_ticks("005930", f"09{minute:02d}", [50000] * 3, [100] * 3))

        db_path = tmp_path / "candle_cb.db"
        _create_test_db(db_path, ticks)

        engine = ReplayEngine(
            strategy_configs=SIMPLE_STRATEGY,
            initial_capital=10_000_000,
        )

        candles: list[Candle] = []
        result = engine.run(db_path, on_candle=lambda code, c: candles.append(c))

        # Should have ~5 candles (one per minute) including flush
        assert len(candles) >= 4

    def test_db_not_found(self):
        """Should raise FileNotFoundError for missing DB."""
        engine = ReplayEngine(strategy_configs=SIMPLE_STRATEGY)
        with pytest.raises(FileNotFoundError):
            engine.run("nonexistent.db")

    def test_real_data_replay(self):
        """Integration test with actual collected data (skipped if not present)."""
        db_path = Path("data/realtime_20260317.db")
        if not db_path.exists():
            pytest.skip("Real data not available")

        engine = ReplayEngine(
            strategy_configs={
                **SIMPLE_STRATEGY,
                "watchlist_strategies": {
                    "005930": ["TEST_MA"],
                    "000660": ["TEST_MA"],
                    "005380": ["TEST_MA"],
                },
            },
            initial_capital=10_000_000,
        )

        result = engine.run(
            db_path,
            start_time="09:00:00",
            end_time="15:20:00",
        )

        assert engine._ticks_processed > 0
        assert engine._candles_generated > 0
        assert result.initial_capital == 10_000_000
