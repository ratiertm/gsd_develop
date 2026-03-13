"""Tests for CandleAggregator: tick-to-OHLCV candle conversion."""

from datetime import datetime

import pytest

from kiwoom_trader.config.constants import FID
from kiwoom_trader.core.candle_aggregator import CandleAggregator
from kiwoom_trader.core.models import Candle


class TestCandleAggregator:
    """CandleAggregator converts tick stream into completed OHLCV candles."""

    def _make_tick(self, price: int, volume: int, time_str: str) -> dict:
        """Helper to build a FID-keyed tick dict."""
        return {
            FID.CURRENT_PRICE: str(price),
            FID.EXEC_VOLUME: str(volume),
            FID.EXEC_TIME: time_str,
        }

    def test_single_tick_starts_building_candle(self):
        """A single tick should start a building candle but not emit anything."""
        agg = CandleAggregator(interval_minutes=1)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        agg.on_tick("005930", self._make_tick(50000, 100, "090100"))

        assert len(emitted) == 0  # No candle emitted yet

    def test_multiple_ticks_same_slot_update_ohlcv(self):
        """Multiple ticks in the same minute slot should update the building candle."""
        agg = CandleAggregator(interval_minutes=1)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        # All within 09:01 minute slot
        agg.on_tick("005930", self._make_tick(50000, 100, "090100"))
        agg.on_tick("005930", self._make_tick(50500, 200, "090115"))  # new high
        agg.on_tick("005930", self._make_tick(49500, 150, "090130"))  # new low
        agg.on_tick("005930", self._make_tick(50200, 300, "090145"))  # close

        # Still no emission (same slot)
        assert len(emitted) == 0

        # Trigger emission by crossing to next minute
        agg.on_tick("005930", self._make_tick(50300, 50, "090200"))
        assert len(emitted) == 1

        code, candle = emitted[0]
        assert code == "005930"
        assert candle.open == 50000
        assert candle.high == 50500
        assert candle.low == 49500
        assert candle.close == 50200
        assert candle.volume == 100 + 200 + 150 + 300

    def test_minute_boundary_emits_candle(self):
        """Crossing a minute boundary should emit the completed candle."""
        agg = CandleAggregator(interval_minutes=1)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        agg.on_tick("005930", self._make_tick(50000, 100, "090100"))
        agg.on_tick("005930", self._make_tick(50100, 200, "090200"))  # new minute

        assert len(emitted) == 1
        candle = emitted[0][1]
        assert isinstance(candle, Candle)
        assert candle.code == "005930"
        assert candle.open == 50000
        assert candle.close == 50000
        assert candle.volume == 100

    def test_zero_price_ignored(self):
        """Ticks with price=0 should be silently ignored."""
        agg = CandleAggregator(interval_minutes=1)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        agg.on_tick("005930", self._make_tick(0, 100, "090100"))

        # Nothing should happen -- no building candle started
        assert len(emitted) == 0

    def test_abs_applied_to_negative_prices(self):
        """Kiwoom sign convention: negative prices should have abs() applied."""
        agg = CandleAggregator(interval_minutes=1)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        agg.on_tick("005930", self._make_tick(-50000, 100, "090100"))
        agg.on_tick("005930", self._make_tick(-49500, 200, "090200"))  # trigger emit

        assert len(emitted) == 1
        candle = emitted[0][1]
        assert candle.open == 50000
        assert candle.high == 50000
        assert candle.low == 50000
        assert candle.close == 50000

    def test_multiple_codes_independent(self):
        """Different stock codes should have independent building candles."""
        agg = CandleAggregator(interval_minutes=1)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        agg.on_tick("005930", self._make_tick(50000, 100, "090100"))
        agg.on_tick("035420", self._make_tick(300000, 50, "090100"))

        # Cross minute for both
        agg.on_tick("005930", self._make_tick(50100, 100, "090200"))
        agg.on_tick("035420", self._make_tick(301000, 50, "090200"))

        assert len(emitted) == 2
        codes = {e[0] for e in emitted}
        assert codes == {"005930", "035420"}

        # Check each candle has correct values
        for code, candle in emitted:
            if code == "005930":
                assert candle.open == 50000
            elif code == "035420":
                assert candle.open == 300000

    def test_custom_interval(self):
        """5-minute candles should aggregate ticks across 5-minute slots."""
        agg = CandleAggregator(interval_minutes=5)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        # All within first 5-min slot (09:00-09:04)
        agg.on_tick("005930", self._make_tick(50000, 100, "090000"))
        agg.on_tick("005930", self._make_tick(50500, 200, "090200"))
        agg.on_tick("005930", self._make_tick(49800, 150, "090400"))

        assert len(emitted) == 0  # Still in same 5-min slot

        # Cross into next 5-min slot (09:05)
        agg.on_tick("005930", self._make_tick(50100, 300, "090500"))

        assert len(emitted) == 1
        candle = emitted[0][1]
        assert candle.open == 50000
        assert candle.high == 50500
        assert candle.low == 49800
        assert candle.close == 49800
        assert candle.volume == 100 + 200 + 150

    def test_cum_price_volume_tracked(self):
        """Candle should track cumulative price*volume for VWAP calculation."""
        agg = CandleAggregator(interval_minutes=1)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        agg.on_tick("005930", self._make_tick(50000, 100, "090100"))
        agg.on_tick("005930", self._make_tick(50200, 200, "090130"))
        agg.on_tick("005930", self._make_tick(50300, 50, "090200"))  # trigger emit

        candle = emitted[0][1]
        expected_cpv = 50000.0 * 100 + 50200.0 * 200
        assert candle.cum_price_volume == pytest.approx(expected_cpv)
        assert candle.cum_volume == 100 + 200

    def test_empty_or_missing_fid_values(self):
        """Ticks with missing or empty FID values should be handled gracefully."""
        agg = CandleAggregator(interval_minutes=1)
        emitted = []
        agg.register_callback(lambda code, candle: emitted.append((code, candle)))

        # Missing price key
        agg.on_tick("005930", {FID.EXEC_VOLUME: "100", FID.EXEC_TIME: "090100"})
        assert len(emitted) == 0

        # Empty string price
        agg.on_tick("005930", {FID.CURRENT_PRICE: "", FID.EXEC_VOLUME: "100", FID.EXEC_TIME: "090100"})
        assert len(emitted) == 0
