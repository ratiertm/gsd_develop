"""DataSource abstraction for historical candle data retrieval.

DataSource ABC defines the get_candles contract.
KiwoomDataSource implements it via Kiwoom opt10081 (daily) TR requests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Callable

from loguru import logger

from kiwoom_trader.core.models import Candle

try:
    from kiwoom_trader.api.tr_request_queue import TRRequestQueue
except ImportError:
    TRRequestQueue = None  # type: ignore[misc,assignment]


class DataSource(ABC):
    """Abstract base class for historical candle data sources."""

    @abstractmethod
    def get_candles(
        self,
        code: str,
        start_date: date,
        end_date: date,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[Candle]:
        """Fetch historical OHLCV candles, sorted by timestamp ascending.

        Args:
            code: Stock code (e.g., "005930").
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).
            on_progress: Optional callback(current_page, estimated_total).

        Returns:
            List of Candle objects sorted ascending by timestamp.
        """
        ...


class KiwoomDataSource(DataSource):
    """Fetches historical candles via Kiwoom opt10081 (daily) TR requests.

    Uses TRRequestQueue to respect 3.6s rate limits.
    Parses GetCommData response fields with abs(int(strip())) pattern
    matching Phase 2 chejan parsing.

    Args:
        kiwoom_api: Kiwoom API instance with get_comm_data, get_repeat_cnt.
        tr_queue: TRRequestQueue for rate-limited TR dispatch.
    """

    def __init__(self, kiwoom_api, tr_queue) -> None:
        self._api = kiwoom_api
        self._tr_queue = tr_queue

    def get_candles(
        self,
        code: str,
        start_date: date,
        end_date: date,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[Candle]:
        """Fetch daily candles via opt10081 TR requests with pagination.

        Enqueues TR requests with pagination (prev_next=0 first, then 2)
        until date < start_date or no more data.

        Args:
            code: Stock code.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).
            on_progress: Progress callback(current_page, estimated_total).

        Returns:
            Candles sorted ascending by timestamp, filtered to date range.
        """
        all_candles: list[Candle] = []
        page = 0
        prev_next = 0
        estimated_pages = 5  # Initial estimate

        while True:
            page += 1

            # Enqueue TR request
            inputs = {
                "종목코드": code,
                "기준일자": end_date.strftime("%Y%m%d"),
                "수정주가구분": "1",
            }
            self._tr_queue.enqueue(
                tr_code="opt10081",
                rq_name="주식일봉차트조회",
                screen_no="4001",
                inputs=inputs,
                prev_next=prev_next,
            )

            # Get response count
            count = self._api.get_repeat_cnt("opt10081", "주식일봉차트조회")
            if count == 0:
                break

            candles = self._parse_tr_response(
                self._api, "opt10081", "주식일봉차트조회", code, count
            )
            all_candles.extend(candles)

            if on_progress:
                on_progress(page, max(estimated_pages, page + 1))

            # Check if we've gone past start_date
            if candles:
                oldest = min(c.timestamp for c in candles)
                if oldest.date() < start_date:
                    break

            # Continue pagination
            prev_next = 2

        # Filter to date range and sort ascending
        filtered = self._filter_candles(all_candles, start_date, end_date)
        filtered.sort(key=lambda c: c.timestamp)
        return filtered

    def _parse_tr_response(
        self, api, tr_code: str, rq_name: str, code: str, count: int
    ) -> list[Candle]:
        """Parse opt10081 TR response into Candle objects.

        Uses abs(int(raw.strip() or '0')) pattern for price/qty fields
        to handle Kiwoom's +/- signs and whitespace.

        Args:
            api: Kiwoom API instance.
            tr_code: TR code (e.g., "opt10081").
            rq_name: Request name.
            code: Stock code.
            count: Number of rows in response.

        Returns:
            List of parsed Candle objects.
        """
        candles: list[Candle] = []
        for i in range(count):
            date_str = api.get_comm_data(tr_code, rq_name, i, "일자").strip()
            open_price = abs(int(api.get_comm_data(tr_code, rq_name, i, "시가").strip() or "0"))
            high = abs(int(api.get_comm_data(tr_code, rq_name, i, "고가").strip() or "0"))
            low = abs(int(api.get_comm_data(tr_code, rq_name, i, "저가").strip() or "0"))
            close = abs(int(api.get_comm_data(tr_code, rq_name, i, "현재가").strip() or "0"))
            volume = abs(int(api.get_comm_data(tr_code, rq_name, i, "거래량").strip() or "0"))

            try:
                timestamp = datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                logger.warning(f"Invalid date format: {date_str}, skipping row {i}")
                continue

            candles.append(
                Candle(
                    code=code,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    timestamp=timestamp,
                )
            )
        return candles

    def _filter_candles(
        self, candles: list[Candle], start_date: date, end_date: date
    ) -> list[Candle]:
        """Filter candles to [start_date, end_date] inclusive range.

        Args:
            candles: List of candles to filter.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).

        Returns:
            Filtered candles within date range.
        """
        return [
            c for c in candles
            if start_date <= c.timestamp.date() <= end_date
        ]
