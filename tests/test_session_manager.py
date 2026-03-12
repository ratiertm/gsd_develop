"""Tests for SessionManager with auto-reconnection and subscription restore."""

from unittest.mock import MagicMock, patch, call

import pytest

from kiwoom_trader.api.session_manager import SessionManager


@pytest.fixture
def mock_api():
    """Mock KiwoomAPI with connection methods and signals."""
    api = MagicMock()
    api.get_connect_state.return_value = 1  # connected
    api.comm_connect = MagicMock()
    api.set_real_reg = MagicMock()
    api.connected = MagicMock()
    return api


@pytest.fixture
def session_mgr(mock_api):
    """Create SessionManager with mocked QTimer and API."""
    with patch("kiwoom_trader.api.session_manager.QTimer") as MockQTimer:
        # Create separate mock instances for reconnect and heartbeat timers
        reconnect_timer = MagicMock()
        heartbeat_timer = MagicMock()
        MockQTimer.side_effect = [reconnect_timer, heartbeat_timer]

        mgr = SessionManager(mock_api)
        mgr._reconnect_timer = reconnect_timer
        mgr._heartbeat_timer = heartbeat_timer
        yield mgr


class TestLoginHandling:
    """Tests for _on_connect success/failure paths."""

    def test_successful_login(self, session_mgr, mock_api):
        """_on_connect(0) resets retry count and starts heartbeat."""
        session_mgr._retry_count = 3  # Simulate previous failures

        session_mgr._on_connect(0)

        assert session_mgr._retry_count == 0
        session_mgr._heartbeat_timer.start.assert_called()

    def test_failed_login_schedules_reconnect(self, session_mgr, mock_api):
        """_on_connect(non-zero) increments retry and schedules reconnect."""
        initial_retries = session_mgr._retry_count

        session_mgr._on_connect(-100)

        assert session_mgr._retry_count == initial_retries + 1
        session_mgr._reconnect_timer.setInterval.assert_called()
        session_mgr._reconnect_timer.start.assert_called()


class TestExponentialBackoff:
    """Tests for reconnection delay calculation."""

    def test_exponential_backoff(self, session_mgr):
        """Delay doubles with each retry: 5000, 10000, 20000."""
        delays = []

        for _ in range(3):
            session_mgr._schedule_reconnect()
            # Extract the interval set on the timer
            call_args = session_mgr._reconnect_timer.setInterval.call_args
            delays.append(call_args[0][0])

        assert delays == [5000, 10000, 20000]

    def test_max_retries_stops(self, session_mgr):
        """After MAX_RETRIES, _schedule_reconnect does not start timer."""
        session_mgr._retry_count = SessionManager.MAX_RETRIES

        session_mgr._schedule_reconnect()

        session_mgr._reconnect_timer.start.assert_not_called()


class TestHeartbeat:
    """Tests for connection state monitoring."""

    def test_heartbeat_detects_disconnect(self, session_mgr, mock_api):
        """_check_connection when get_connect_state returns 0 triggers reconnect."""
        mock_api.get_connect_state.return_value = 0

        session_mgr._check_connection()

        session_mgr._heartbeat_timer.stop.assert_called()
        # Should schedule reconnect
        session_mgr._reconnect_timer.setInterval.assert_called()
        session_mgr._reconnect_timer.start.assert_called()


class TestSubscriptionRestore:
    """Tests for real-time subscription tracking and restoration."""

    def test_track_and_restore_subscriptions(self, session_mgr, mock_api):
        """Track 2 subscriptions, restore them, verify set_real_reg called twice."""
        session_mgr.track_real_subscription("5001", "005930", "10;13;15", "0")
        session_mgr.track_real_subscription("5002", "000660", "10;13;15", "1")

        session_mgr._restore_real_subscriptions()

        assert mock_api.set_real_reg.call_count == 2
        mock_api.set_real_reg.assert_any_call("5001", "005930", "10;13;15", "0")
        mock_api.set_real_reg.assert_any_call("5002", "000660", "10;13;15", "1")

    def test_reconnect_restores_subscriptions(self, session_mgr, mock_api):
        """_on_connect(0) with tracked subscriptions calls _restore_real_subscriptions."""
        session_mgr.track_real_subscription("5001", "005930", "10;13;15", "0")

        session_mgr._on_connect(0)

        mock_api.set_real_reg.assert_called_once_with("5001", "005930", "10;13;15", "0")
