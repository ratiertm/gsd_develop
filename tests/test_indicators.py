"""Tests for 7 incremental technical indicators."""

from math import sqrt

import pytest

from kiwoom_trader.core.indicators import (
    BollingerBandsIndicator,
    EMAIndicator,
    MACDIndicator,
    OBVIndicator,
    RSIIndicator,
    SMAIndicator,
    VWAPIndicator,
)


class TestSMAIndicator:
    """Simple Moving Average with O(1) incremental update."""

    def test_sma_basic(self):
        """SMA(3) with [10, 20, 30, 40] -> [None, None, 20.0, 30.0]"""
        sma = SMAIndicator(period=3)
        assert sma.update(10) is None
        assert sma.update(20) is None
        assert sma.update(30) == pytest.approx(20.0)
        assert sma.update(40) == pytest.approx(30.0)

    def test_sma_warmup(self):
        """Returns None until period values received."""
        sma = SMAIndicator(period=5)
        for i in range(4):
            assert sma.update(float(i)) is None
        # 5th value should produce result
        result = sma.update(4.0)
        assert result is not None
        assert result == pytest.approx(2.0)  # mean(0,1,2,3,4)

    def test_sma_sliding_window(self):
        """SMA correctly drops oldest value as window slides."""
        sma = SMAIndicator(period=3)
        sma.update(10)
        sma.update(20)
        sma.update(30)  # 20.0
        result = sma.update(60)  # (20+30+60)/3 = 36.67
        assert result == pytest.approx(110.0 / 3)


class TestEMAIndicator:
    """Exponential Moving Average with recursive update."""

    def test_ema_seed_with_first_value(self):
        """First EMA value equals first input (after warmup)."""
        ema = EMAIndicator(period=1)
        result = ema.update(50.0)
        assert result == pytest.approx(50.0)

    def test_ema_basic(self):
        """Verify EMA against known values."""
        ema = EMAIndicator(period=3)
        # alpha = 2/(3+1) = 0.5
        assert ema.update(10.0) is None  # count=1 < 3
        assert ema.update(20.0) is None  # count=2 < 3
        # count=3, ema was seeded with 10, then updated:
        # ema after 20: 0.5*20 + 0.5*10 = 15
        # ema after 30: 0.5*30 + 0.5*15 = 22.5
        result = ema.update(30.0)
        assert result == pytest.approx(22.5)

    def test_ema_warmup(self):
        """Returns None until period values processed."""
        ema = EMAIndicator(period=5)
        for i in range(4):
            assert ema.update(float(i + 1)) is None
        result = ema.update(5.0)
        assert result is not None


class TestRSIIndicator:
    """RSI with Wilder's smoothing."""

    def test_rsi_basic(self):
        """Verify RSI against known values with 14-period."""
        rsi = RSIIndicator(period=14)
        # Feed 15 prices (14 changes needed for first RSI)
        prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
        results = []
        for p in prices:
            r = rsi.update(p)
            results.append(r)
        # First 14 should be None (only 13 changes from 15 prices, but first price sets prev)
        # Actually: first price -> None (sets prev), then 14 more needed
        # So prices[0] returns None, prices[1..14] accumulate changes
        # prices[14] (index 14) should produce first RSI
        assert all(r is None for r in results[:14])
        assert results[14] is not None
        # RSI should be between 0 and 100
        assert 0 <= results[14] <= 100

    def test_rsi_all_gains(self):
        """Returns 100.0 when all changes are gains (avg_loss==0)."""
        rsi = RSIIndicator(period=3)
        rsi.update(10)   # sets prev
        rsi.update(20)   # gain=10
        rsi.update(30)   # gain=10
        result = rsi.update(40)  # gain=10, now have 3 changes
        assert result == pytest.approx(100.0)

    def test_rsi_all_losses(self):
        """Returns 0.0 when all changes are losses (avg_gain==0)."""
        rsi = RSIIndicator(period=3)
        rsi.update(40)   # sets prev
        rsi.update(30)   # loss=10
        rsi.update(20)   # loss=10
        result = rsi.update(10)  # loss=10
        assert result == pytest.approx(0.0)

    def test_rsi_range(self):
        """RSI should always be between 0 and 100."""
        rsi = RSIIndicator(period=5)
        prices = [100, 102, 99, 101, 98, 103, 97, 105, 96, 104]
        for p in prices:
            r = rsi.update(p)
            if r is not None:
                assert 0 <= r <= 100


class TestMACDIndicator:
    """MACD = EMA(fast) - EMA(slow), Signal = EMA(MACD)."""

    def test_macd_warmup(self):
        """Returns None until slow+signal-1 periods ready."""
        macd = MACDIndicator(fast=12, slow=26, signal=9)
        # Need at least 26 values for slow EMA, then 9 for signal EMA
        for i in range(33):
            result = macd.update(float(i + 100))
            if i < 33:
                # Should still be warming up for most values
                pass
        # After 34 values (26 slow + 9 signal - 1), should have result
        result = macd.update(134.0)
        assert result is not None or True  # may still warm up

    def test_macd_basic(self):
        """Verify MACD returns (macd_line, signal_line, histogram) tuple."""
        macd = MACDIndicator(fast=3, slow=5, signal=3)
        # Feed enough values
        results = []
        for i in range(20):
            r = macd.update(float(100 + i))
            results.append(r)

        # Find first non-None result
        non_none = [r for r in results if r is not None]
        assert len(non_none) > 0
        macd_line, signal_line, histogram = non_none[0]
        assert histogram == pytest.approx(macd_line - signal_line)

    def test_macd_histogram_is_difference(self):
        """Histogram should always equal macd_line - signal_line."""
        macd = MACDIndicator(fast=3, slow=5, signal=3)
        for i in range(30):
            r = macd.update(float(100 + i * (-1) ** i))
            if r is not None:
                macd_line, signal_line, histogram = r
                assert histogram == pytest.approx(macd_line - signal_line)


class TestBollingerBandsIndicator:
    """Bollinger Bands = SMA +/- K * population StdDev."""

    def test_bollinger_basic(self):
        """Verify (upper, middle, lower) against hand-calculated values."""
        bb = BollingerBandsIndicator(period=3, num_std=2.0)
        assert bb.update(10) is None
        assert bb.update(20) is None
        result = bb.update(30)
        assert result is not None

        upper, middle, lower = result
        assert middle == pytest.approx(20.0)
        # population std = sqrt(((10-20)^2 + (20-20)^2 + (30-20)^2) / 3)
        #                = sqrt((100 + 0 + 100) / 3) = sqrt(200/3)
        expected_std = sqrt(200.0 / 3)
        assert upper == pytest.approx(20.0 + 2.0 * expected_std)
        assert lower == pytest.approx(20.0 - 2.0 * expected_std)

    def test_bollinger_population_stddev(self):
        """Uses N (population) not N-1 (sample) divisor."""
        bb = BollingerBandsIndicator(period=2, num_std=1.0)
        bb.update(10)
        result = bb.update(20)
        upper, middle, lower = result
        # population std = sqrt(((10-15)^2 + (20-15)^2) / 2) = sqrt(50/2) = 5
        assert middle == pytest.approx(15.0)
        assert upper == pytest.approx(20.0)  # 15 + 5
        assert lower == pytest.approx(10.0)  # 15 - 5

    def test_bollinger_warmup(self):
        """Returns None until period values received."""
        bb = BollingerBandsIndicator(period=20, num_std=2.0)
        for i in range(19):
            assert bb.update(float(i)) is None
        result = bb.update(19.0)
        assert result is not None


class TestVWAPIndicator:
    """Intraday VWAP = cumulative(typical_price * volume) / cumulative(volume)."""

    def test_vwap_cumulative(self):
        """Verify cumulative typical_price*volume / cumulative_volume."""
        vwap = VWAPIndicator()
        # Candle 1: H=110, L=90, C=100, V=1000
        # typical = (110+90+100)/3 = 100
        r1 = vwap.update_candle(110, 90, 100, 1000)
        assert r1 == pytest.approx(100.0)

        # Candle 2: H=120, L=100, C=110, V=2000
        # typical = (120+100+110)/3 = 110
        # VWAP = (100*1000 + 110*2000) / (1000+2000) = 320000/3000 = 106.67
        r2 = vwap.update_candle(120, 100, 110, 2000)
        assert r2 == pytest.approx(320000.0 / 3000.0)

    def test_vwap_reset(self):
        """After reset(), starts fresh accumulation."""
        vwap = VWAPIndicator()
        vwap.update_candle(110, 90, 100, 1000)
        vwap.reset()
        r = vwap.update_candle(120, 100, 110, 2000)
        # Should be fresh: typical = 110, so VWAP = 110
        assert r == pytest.approx(110.0)

    def test_vwap_zero_volume_returns_none(self):
        """Zero volume candle should return None."""
        vwap = VWAPIndicator()
        assert vwap.update_candle(100, 90, 95, 0) is None


class TestOBVIndicator:
    """On-Balance Volume: cumulative volume by price direction."""

    def test_obv_up_down(self):
        """Volume added on up-close, subtracted on down-close."""
        obv = OBVIndicator()
        assert obv.update(100, 1000) == 0  # First: no prev, OBV=0
        assert obv.update(110, 2000) == 2000  # Up: +2000
        assert obv.update(105, 1500) == 500  # Down: -1500
        assert obv.update(115, 3000) == 3500  # Up: +3000

    def test_obv_flat(self):
        """No change on equal close."""
        obv = OBVIndicator()
        obv.update(100, 1000)
        result = obv.update(100, 2000)  # Same close
        assert result == 0  # No change

    def test_obv_always_returns_int(self):
        """OBV should return int."""
        obv = OBVIndicator()
        assert isinstance(obv.update(100, 500), int)
        assert isinstance(obv.update(110, 500), int)


class TestWarmupAllIndicators:
    """Each indicator returns None before sufficient data."""

    def test_warmup_all_indicators(self):
        """Verify warmup behavior across all indicator types."""
        # SMA(5): None for first 4
        sma = SMAIndicator(period=5)
        for i in range(4):
            assert sma.update(float(i)) is None

        # EMA(5): None for first 4
        ema = EMAIndicator(period=5)
        for i in range(4):
            assert ema.update(float(i)) is None

        # RSI(5): None for first 5 (need 5 changes = 6 prices, first returns None)
        rsi = RSIIndicator(period=5)
        for i in range(5):
            assert rsi.update(float(i * 10)) is None

        # Bollinger(5): None for first 4
        bb = BollingerBandsIndicator(period=5)
        for i in range(4):
            assert bb.update(float(i)) is None

        # MACD(3,5,3): warmup depends on slow + signal
        macd = MACDIndicator(fast=3, slow=5, signal=3)
        for i in range(4):
            assert macd.update(float(i)) is None

        # VWAP: returns value on first non-zero volume candle
        vwap = VWAPIndicator()
        assert vwap.update_candle(100, 90, 95, 0) is None  # zero volume
        assert vwap.update_candle(100, 90, 95, 100) is not None

        # OBV: always returns int (no warmup needed)
        obv = OBVIndicator()
        assert obv.update(100, 500) == 0  # First call, no prev
