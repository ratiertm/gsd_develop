"""Incremental technical indicators for real-time candle processing.

All indicators update in O(1) per new candle (except Bollinger which is O(N)
for stddev but with small window sizes this is negligible).

Each indicator returns None during warmup (before enough data accumulated).
"""

from __future__ import annotations

from collections import deque
from math import sqrt


class SMAIndicator:
    """Simple Moving Average with O(1) incremental update via running sum.

    Args:
        period: Number of values in the moving window.
    """

    def __init__(self, period: int) -> None:
        self._period = period
        self._window: deque[float] = deque(maxlen=period)
        self._sum = 0.0

    def update(self, value: float) -> float | None:
        """Add a new value and return the current SMA, or None if warming up."""
        if len(self._window) == self._period:
            self._sum -= self._window[0]  # Will be evicted by append
        self._window.append(value)
        self._sum += value
        if len(self._window) < self._period:
            return None
        return self._sum / self._period


class EMAIndicator:
    """Exponential Moving Average: EMA_t = alpha * value + (1-alpha) * EMA_{t-1}.

    Seeded with first value. Returns None until `period` values processed.

    Args:
        period: EMA period (used to compute alpha = 2/(period+1)).
    """

    def __init__(self, period: int) -> None:
        self._period = period
        self._alpha = 2.0 / (period + 1)
        self._ema: float | None = None
        self._count = 0

    def update(self, value: float) -> float | None:
        """Add a new value and return the current EMA, or None if warming up."""
        self._count += 1
        if self._ema is None:
            self._ema = value  # Seed with first value
        else:
            self._ema = self._alpha * value + (1 - self._alpha) * self._ema

        if self._count < self._period:
            return None
        return self._ema


class RSIIndicator:
    """RSI with Wilder's smoothing.

    Initial period uses simple average of gains/losses.
    Subsequent values use Wilder's smoothing:
        avg_gain = (prev_avg_gain * (period-1) + current_gain) / period

    Returns 100.0 when avg_loss==0 (all gains).
    Returns 0.0 when avg_gain==0 (all losses).

    Args:
        period: RSI period (default 14).
    """

    def __init__(self, period: int = 14) -> None:
        self._period = period
        self._prev_close: float | None = None
        self._avg_gain: float = 0.0
        self._avg_loss: float = 0.0
        self._count = 0
        self._gains: list[float] = []
        self._losses: list[float] = []

    def update(self, close: float) -> float | None:
        """Add a new close price and return RSI, or None if warming up."""
        if self._prev_close is None:
            self._prev_close = close
            return None

        change = close - self._prev_close
        self._prev_close = close
        gain = max(change, 0.0)
        loss = abs(min(change, 0.0))
        self._count += 1

        if self._count <= self._period:
            self._gains.append(gain)
            self._losses.append(loss)
            if self._count == self._period:
                self._avg_gain = sum(self._gains) / self._period
                self._avg_loss = sum(self._losses) / self._period
                self._gains.clear()
                self._losses.clear()
                return self._compute_rsi()
            return None

        # Wilder's smoothing
        self._avg_gain = (self._avg_gain * (self._period - 1) + gain) / self._period
        self._avg_loss = (self._avg_loss * (self._period - 1) + loss) / self._period
        return self._compute_rsi()

    def _compute_rsi(self) -> float:
        if self._avg_loss == 0:
            return 100.0 if self._avg_gain > 0 else 50.0
        if self._avg_gain == 0:
            return 0.0
        rs = self._avg_gain / self._avg_loss
        return 100.0 - (100.0 / (1.0 + rs))


class MACDIndicator:
    """MACD = EMA(fast) - EMA(slow), Signal = EMA(MACD, signal_period).

    Returns (macd_line, signal_line, histogram) or None during warmup.

    Args:
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal EMA period (default 9).
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self._fast_ema = EMAIndicator(fast)
        self._slow_ema = EMAIndicator(slow)
        self._signal_ema = EMAIndicator(signal)

    def update(self, value: float) -> tuple[float, float, float] | None:
        """Add a new value and return (macd, signal, histogram) or None."""
        fast = self._fast_ema.update(value)
        slow = self._slow_ema.update(value)
        if fast is None or slow is None:
            return None
        macd_line = fast - slow
        signal_line = self._signal_ema.update(macd_line)
        if signal_line is None:
            return None
        histogram = macd_line - signal_line
        return (macd_line, signal_line, histogram)


class BollingerBandsIndicator:
    """Bollinger Bands = SMA +/- K * population StdDev over sliding window.

    Returns (upper, middle, lower) or None during warmup.

    Args:
        period: Window size (default 20).
        num_std: Number of standard deviations (default 2.0).
    """

    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        self._period = period
        self._num_std = num_std
        self._window: deque[float] = deque(maxlen=period)

    def update(self, value: float) -> tuple[float, float, float] | None:
        """Add a new value and return (upper, middle, lower) or None."""
        self._window.append(value)
        if len(self._window) < self._period:
            return None
        mean = sum(self._window) / self._period
        variance = sum((x - mean) ** 2 for x in self._window) / self._period
        std = sqrt(variance)
        return (mean + self._num_std * std, mean, mean - self._num_std * std)


class VWAPIndicator:
    """Intraday VWAP = cumulative(typical_price * volume) / cumulative(volume).

    Resets daily via reset(). Uses typical price = (high + low + close) / 3.
    """

    def __init__(self) -> None:
        self._cum_pv: float = 0.0
        self._cum_vol: int = 0

    def update_candle(self, high: int, low: int, close: int, volume: int) -> float | None:
        """Update with candle HLCV data. Returns VWAP or None if volume is 0."""
        if volume == 0:
            return None
        typical_price = (high + low + close) / 3.0
        self._cum_pv += typical_price * volume
        self._cum_vol += volume
        return self._cum_pv / self._cum_vol

    def reset(self) -> None:
        """Reset for new trading day."""
        self._cum_pv = 0.0
        self._cum_vol = 0


class OBVIndicator:
    """On-Balance Volume: cumulative volume weighted by price direction.

    Volume added on up-close, subtracted on down-close, unchanged on flat.
    """

    def __init__(self) -> None:
        self._obv: int = 0
        self._prev_close: float | None = None

    def update(self, close: float, volume: int) -> int:
        """Update with close price and volume. Always returns current OBV."""
        if self._prev_close is not None:
            if close > self._prev_close:
                self._obv += volume
            elif close < self._prev_close:
                self._obv -= volume
        self._prev_close = close
        return self._obv


class ATRIndicator:
    """Average True Range — measures volatility.

    Uses Wilder's smoothing (EMA with alpha=1/period).

    Args:
        period: Smoothing period (default 14).
    """

    def __init__(self, period: int = 14) -> None:
        self._period = period
        self._prev_close: float | None = None
        self._atr: float | None = None
        self._count = 0

    def update_candle(self, high: float, low: float, close: float, volume: int = 0) -> float | None:
        """Update with OHLC data. Returns ATR or None during warmup."""
        if self._prev_close is None:
            self._prev_close = close
            return None

        # True Range = max(H-L, |H-prevC|, |L-prevC|)
        tr = max(high - low, abs(high - self._prev_close), abs(low - self._prev_close))
        self._prev_close = close
        self._count += 1

        if self._atr is None:
            if self._count < self._period:
                # Accumulate for initial average
                if not hasattr(self, "_tr_sum"):
                    self._tr_sum = 0.0
                self._tr_sum += tr
                return None
            else:
                # First ATR = simple average of first N true ranges
                self._tr_sum += tr
                self._atr = self._tr_sum / self._period
                del self._tr_sum
        else:
            # Wilder's smoothing: ATR = (prev_ATR * (N-1) + TR) / N
            self._atr = (self._atr * (self._period - 1) + tr) / self._period

        return self._atr


class ADXIndicator:
    """Average Directional Index — measures trend strength.

    Components: +DI, -DI, ADX.
    ADX > 25 = strong trend, ADX < 20 = no trend (sideways).

    Args:
        period: Smoothing period (default 14).

    Returns:
        Tuple of (adx, plus_di, minus_di) or None during warmup.
    """

    def __init__(self, period: int = 14) -> None:
        self._period = period
        self._prev_high: float | None = None
        self._prev_low: float | None = None
        self._prev_close: float | None = None
        self._smoothed_plus_dm = 0.0
        self._smoothed_minus_dm = 0.0
        self._smoothed_tr = 0.0
        self._dx_values: deque[float] = deque(maxlen=period)
        self._adx: float | None = None
        self._count = 0

    def update_candle(self, high: float, low: float, close: float, volume: int = 0) -> tuple[float, float, float] | None:
        """Update with OHLC data. Returns (ADX, +DI, -DI) or None during warmup."""
        if self._prev_high is None:
            self._prev_high = high
            self._prev_low = low
            self._prev_close = close
            return None

        # Directional Movement
        plus_dm = max(high - self._prev_high, 0) if (high - self._prev_high) > (self._prev_low - low) else 0
        minus_dm = max(self._prev_low - low, 0) if (self._prev_low - low) > (high - self._prev_high) else 0

        # True Range
        tr = max(high - low, abs(high - self._prev_close), abs(low - self._prev_close))

        self._prev_high = high
        self._prev_low = low
        self._prev_close = close
        self._count += 1

        if self._count <= self._period:
            # Accumulate initial sums
            self._smoothed_plus_dm += plus_dm
            self._smoothed_minus_dm += minus_dm
            self._smoothed_tr += tr
            if self._count < self._period:
                return None
            # First smoothed values = sum of first N
        else:
            # Wilder's smoothing
            self._smoothed_plus_dm = self._smoothed_plus_dm - (self._smoothed_plus_dm / self._period) + plus_dm
            self._smoothed_minus_dm = self._smoothed_minus_dm - (self._smoothed_minus_dm / self._period) + minus_dm
            self._smoothed_tr = self._smoothed_tr - (self._smoothed_tr / self._period) + tr

        # +DI and -DI
        if self._smoothed_tr == 0:
            return None
        plus_di = 100 * self._smoothed_plus_dm / self._smoothed_tr
        minus_di = 100 * self._smoothed_minus_dm / self._smoothed_tr

        # DX
        di_sum = plus_di + minus_di
        dx = 100 * abs(plus_di - minus_di) / di_sum if di_sum > 0 else 0

        self._dx_values.append(dx)

        if len(self._dx_values) < self._period:
            return None

        # ADX
        if self._adx is None:
            self._adx = sum(self._dx_values) / self._period
        else:
            self._adx = (self._adx * (self._period - 1) + dx) / self._period

        return (self._adx, plus_di, minus_di)
