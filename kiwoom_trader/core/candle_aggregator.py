"""CandleAggregator: converts real-time tick stream into OHLCV candles.

Subscribes to RealDataManager as a "주식체결" observer.
Emits completed candles via registered callbacks when minute boundaries cross.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from kiwoom_trader.config.constants import FID
from kiwoom_trader.core.models import Candle


class CandleAggregator:
    """Aggregates tick data into OHLCV candles per stock code.

    Each stock code has an independent building candle.
    When a tick crosses a minute boundary, the previous candle is finalized
    and emitted to all registered callbacks.

    Args:
        interval_minutes: Candle interval in minutes (default 1).
    """

    # Market opens at 09:00 (KST). Used as reference for minute-slot calculation.
    _MARKET_OPEN_MINUTES = 9 * 60  # 540

    def __init__(self, interval_minutes: int = 1) -> None:
        self._interval = interval_minutes
        self._building: dict[str, dict] = {}  # code -> partial candle data
        self._callbacks: list[Callable[[str, Candle], None]] = []

    def register_callback(self, callback: Callable[[str, Candle], None]) -> None:
        """Register a callback to receive completed candles."""
        self._callbacks.append(callback)

    def on_tick(self, code: str, data_dict: dict) -> None:
        """Process a single tick from RealDataManager subscriber callback.

        Extracts price/volume from FID-keyed dict, updates building candle.
        When minute boundary crosses, finalizes and emits the previous candle.

        Args:
            code: Stock code (e.g., "005930").
            data_dict: FID-keyed dict from Kiwoom API (keys are int FIDs, values are strings).
        """
        # Extract and sanitize values (abs for Kiwoom sign convention)
        price = abs(int(data_dict.get(FID.CURRENT_PRICE, "0") or "0"))
        volume = abs(int(data_dict.get(FID.EXEC_VOLUME, "0") or "0"))
        exec_time = data_dict.get(FID.EXEC_TIME, "")

        if price == 0:
            return

        minute_slot = self._get_minute_slot(exec_time)
        building = self._building.get(code)

        if building is None or building["slot"] != minute_slot:
            # Finalize previous candle if exists
            if building is not None:
                self._finalize_candle(code, building)
            # Start new building candle
            self._building[code] = {
                "slot": minute_slot,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
                "timestamp": datetime.now(),
                "cum_price_volume": float(price) * volume,
                "cum_volume": volume,
            }
            return

        # Update existing building candle
        building["high"] = max(building["high"], price)
        building["low"] = min(building["low"], price)
        building["close"] = price
        building["volume"] += volume
        building["cum_price_volume"] += float(price) * volume
        building["cum_volume"] += volume

    def _get_minute_slot(self, exec_time: str) -> int:
        """Calculate the minute slot from HHMMSS execution time.

        Returns minutes-since-open // interval * interval.
        """
        if len(exec_time) < 6:
            return 0
        hh = int(exec_time[:2])
        mm = int(exec_time[2:4])
        total_minutes = hh * 60 + mm
        minutes_since_open = total_minutes - self._MARKET_OPEN_MINUTES
        return minutes_since_open // self._interval * self._interval

    def _finalize_candle(self, code: str, building: dict) -> None:
        """Convert building candle dict to Candle dataclass and emit."""
        candle = Candle(
            code=code,
            open=building["open"],
            high=building["high"],
            low=building["low"],
            close=building["close"],
            volume=building["volume"],
            timestamp=building["timestamp"],
            cum_price_volume=building["cum_price_volume"],
            cum_volume=building["cum_volume"],
        )
        for callback in self._callbacks:
            callback(code, candle)
