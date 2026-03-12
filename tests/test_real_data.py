"""Tests for real-time data manager (RealDataManager).

Covers CONN-03 requirements:
- SetRealReg subscription lifecycle
- Auto screen number generation
- FID data extraction and dispatch to subscribers
- Subscription tracking for session restoration
"""

from unittest.mock import MagicMock, call

from kiwoom_trader.api.real_data import RealDataManager
from kiwoom_trader.config.constants import FID, SCREEN


class TestRealDataManager:
    """RealDataManager unit tests with mocked KiwoomAPI."""

    def _make_manager(self, mock_kiwoom_api, session_manager=None):
        """Create a RealDataManager with provided mocks."""
        return RealDataManager(mock_kiwoom_api, session_manager=session_manager)

    def test_subscribe_calls_set_real_reg(self, mock_kiwoom_api):
        """subscribe() calls api.set_real_reg with correct arguments."""
        mgr = self._make_manager(mock_kiwoom_api)

        mgr.subscribe(
            code_list="005930",
            fid_list="10;13;15",
            screen_no="5000",
            real_type="1",
        )

        mock_kiwoom_api.set_real_reg.assert_called_once_with(
            "5000", "005930", "10;13;15", "1"
        )

    def test_auto_screen_number(self, mock_kiwoom_api):
        """Two subscribes without explicit screen_no get incrementing numbers."""
        mgr = self._make_manager(mock_kiwoom_api)

        mgr.subscribe("005930", "10;13")
        mgr.subscribe("000660", "10;13")

        calls = mock_kiwoom_api.set_real_reg.call_args_list
        assert calls[0].args[0] == "5000"
        assert calls[1].args[0] == "5001"

    def test_register_and_dispatch(self, mock_kiwoom_api):
        """Registered subscriber receives a dict with extracted FID values."""
        mgr = self._make_manager(mock_kiwoom_api)

        # Mock get_comm_real_data to return different values per FID
        def fake_get_comm_real_data(code, fid):
            return {
                FID.CURRENT_PRICE: "72000",
                FID.VOLUME: "1500000",
                FID.EXEC_VOLUME: "500",
                FID.OPEN_PRICE: "71000",
                FID.HIGH_PRICE: "73000",
                FID.LOW_PRICE: "70500",
            }.get(fid, "")

        mock_kiwoom_api.get_comm_real_data.side_effect = fake_get_comm_real_data

        subscriber = MagicMock()
        mgr.register_subscriber("주식체결", subscriber)

        mgr.on_real_data("005930", "주식체결", "")

        subscriber.assert_called_once()
        received = subscriber.call_args.args
        assert received[0] == "005930"  # code
        data_dict = received[1]
        assert data_dict[FID.CURRENT_PRICE] == "72000"
        assert data_dict[FID.VOLUME] == "1500000"

    def test_unsubscribe(self, mock_kiwoom_api):
        """unsubscribe() calls api.set_real_remove with correct args."""
        mgr = self._make_manager(mock_kiwoom_api)

        mgr.unsubscribe("5000", "005930")

        mock_kiwoom_api.set_real_remove.assert_called_once_with("5000", "005930")

    def test_subscription_tracking(self, mock_kiwoom_api):
        """subscribe() with session_manager calls track_real_subscription."""
        mock_session = MagicMock()
        mgr = self._make_manager(mock_kiwoom_api, session_manager=mock_session)

        mgr.subscribe("005930", "10;13;15", screen_no="5000", real_type="1")

        mock_session.track_real_subscription.assert_called_once_with(
            "5000", "005930", "10;13;15", "1"
        )
