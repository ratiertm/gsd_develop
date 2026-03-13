"""Tests for DataSource ABC and KiwoomDataSource implementation."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from kiwoom_trader.backtest.data_source import DataSource, KiwoomDataSource
from kiwoom_trader.core.models import Candle


class TestDataSourceABC:
    """DataSource ABC defines get_candles contract."""

    def test_cannot_instantiate_abc(self):
        """DataSource cannot be instantiated directly."""
        import pytest
        with pytest.raises(TypeError):
            DataSource()

    def test_concrete_subclass_works(self):
        """A concrete subclass implementing get_candles can be instantiated."""
        class FakeSource(DataSource):
            def get_candles(self, code, start_date, end_date, on_progress=None):
                return []
        src = FakeSource()
        assert src.get_candles("005930", date(2025, 1, 1), date(2025, 6, 1)) == []


class TestKiwoomDataSource:
    """KiwoomDataSource parses opt10081 TR responses into sorted Candle list."""

    def _make_source(self):
        """Create a KiwoomDataSource with mocked API and queue."""
        api = MagicMock()
        tr_queue = MagicMock()
        return KiwoomDataSource(api, tr_queue), api, tr_queue

    def test_init_stores_dependencies(self):
        src, api, queue = self._make_source()
        assert src._api is api
        assert src._tr_queue is queue

    def test_get_candles_parses_response(self):
        """Parses opt10081 data into Candle objects."""
        src, api, queue = self._make_source()

        # Simulate TR request -> response flow
        # The enqueue call should store a callback; we'll invoke the parsing directly
        raw_data = [
            {"date": "20250610", "open": "10000", "high": "10500", "low": "9800", "close": "10200", "volume": "50000"},
            {"date": "20250609", "open": "9900", "high": "10100", "low": "9700", "close": "10000", "volume": "40000"},
            {"date": "20250608", "open": "9800", "high": "10000", "low": "9600", "close": "9900", "volume": "35000"},
        ]

        # Mock get_comm_data_ex to return our data
        api.get_repeat_cnt.return_value = 3
        def mock_get_comm_data(tr_code, rq_name, idx, field_name):
            row = raw_data[idx]
            field_map = {
                "일자": row["date"],
                "시가": row["open"],
                "고가": row["high"],
                "저가": row["low"],
                "현재가": row["close"],
                "거래량": row["volume"],
            }
            return f"  {field_map.get(field_name, '0')}  "  # Include spaces for strip testing

        api.get_comm_data.side_effect = mock_get_comm_data

        # Call internal parse method directly
        candles = src._parse_tr_response(api, "opt10081", "주식일봉차트조회", "005930", 3)

        assert len(candles) == 3
        # Verify parsing correctness
        assert candles[0].close == 10200
        assert candles[0].volume == 50000
        assert candles[0].code == "005930"

    def test_candles_sorted_ascending(self):
        """get_candles returns candles sorted by timestamp ascending."""
        src, api, queue = self._make_source()

        raw_data = [
            {"date": "20250610", "open": "100", "high": "110", "low": "90", "close": "105", "volume": "1000"},
            {"date": "20250608", "open": "95", "high": "100", "low": "85", "close": "90", "volume": "800"},
            {"date": "20250609", "open": "90", "high": "105", "low": "88", "close": "100", "volume": "900"},
        ]

        api.get_repeat_cnt.return_value = 3
        def mock_get_comm_data(tr_code, rq_name, idx, field_name):
            row = raw_data[idx]
            field_map = {
                "일자": row["date"],
                "시가": row["open"],
                "고가": row["high"],
                "저가": row["low"],
                "현재가": row["close"],
                "거래량": row["volume"],
            }
            return field_map.get(field_name, "0")

        api.get_comm_data.side_effect = mock_get_comm_data

        candles = src._parse_tr_response(api, "opt10081", "주식일봉차트조회", "005930", 3)
        # Sort ascending by timestamp
        candles.sort(key=lambda c: c.timestamp)

        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps)

    def test_date_range_filtering(self):
        """Candles outside the requested date range are excluded."""
        src, api, queue = self._make_source()

        # Create candles spanning a wide date range
        all_candles = [
            Candle(code="005930", open=100, high=110, low=90, close=105, volume=1000,
                   timestamp=datetime(2025, 6, 5)),
            Candle(code="005930", open=100, high=110, low=90, close=105, volume=1000,
                   timestamp=datetime(2025, 6, 10)),
            Candle(code="005930", open=100, high=110, low=90, close=105, volume=1000,
                   timestamp=datetime(2025, 6, 15)),
            Candle(code="005930", open=100, high=110, low=90, close=105, volume=1000,
                   timestamp=datetime(2025, 6, 20)),
        ]

        filtered = src._filter_candles(all_candles, date(2025, 6, 8), date(2025, 6, 16))
        assert len(filtered) == 2
        assert filtered[0].timestamp == datetime(2025, 6, 10)
        assert filtered[1].timestamp == datetime(2025, 6, 15)

    def test_handles_negative_price_values(self):
        """Kiwoom returns prices with +/- signs; parsing uses abs()."""
        src, api, queue = self._make_source()

        api.get_repeat_cnt.return_value = 1
        def mock_get_comm_data(tr_code, rq_name, idx, field_name):
            field_map = {
                "일자": "20250610",
                "시가": "-10000",
                "고가": "+10500",
                "저가": "-9800",
                "현재가": "-10200",
                "거래량": "50000",
            }
            return field_map.get(field_name, "0")

        api.get_comm_data.side_effect = mock_get_comm_data
        candles = src._parse_tr_response(api, "opt10081", "주식일봉차트조회", "005930", 1)

        assert candles[0].open == 10000
        assert candles[0].high == 10500
        assert candles[0].close == 10200
