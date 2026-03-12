"""Tests for TR request throttle queue (TRRequestQueue).

Covers CONN-02 requirements:
- Rate-limited TR dispatching at 4s intervals
- FIFO ordering
- Timer lifecycle (start on enqueue, stop when empty)
"""

from unittest.mock import MagicMock, patch, call


class TestTRRequestQueue:
    """TRRequestQueue unit tests with mocked QTimer and KiwoomAPI."""

    def _make_queue(self, mock_kiwoom_api, interval_ms=4000):
        """Create a TRRequestQueue with mocked QTimer."""
        with patch(
            "kiwoom_trader.api.tr_request_queue.QTimer"
        ) as MockQTimer:
            mock_timer = MagicMock()
            mock_timer.isActive.return_value = False
            MockQTimer.return_value = mock_timer

            from kiwoom_trader.api.tr_request_queue import TRRequestQueue

            queue = TRRequestQueue(mock_kiwoom_api, interval_ms=interval_ms)
            queue._timer = mock_timer
            return queue, mock_timer

    def test_enqueue_processes_first_immediately(self, mock_kiwoom_api):
        """First enqueue when idle processes immediately via set_input_value + comm_rq_data."""
        queue, mock_timer = self._make_queue(mock_kiwoom_api)
        mock_timer.isActive.return_value = False

        queue.enqueue(
            tr_code="opt10001",
            rq_name="주식기본정보",
            screen_no="1000",
            inputs={"종목코드": "005930"},
            prev_next=0,
        )

        mock_kiwoom_api.set_input_value.assert_called_once_with("종목코드", "005930")
        mock_kiwoom_api.comm_rq_data.assert_called_once_with(
            "주식기본정보", "opt10001", 0, "1000"
        )

    def test_fifo_order(self, mock_kiwoom_api):
        """Requests are dispatched in FIFO order."""
        queue, mock_timer = self._make_queue(mock_kiwoom_api)
        # Simulate timer already active so enqueue just appends
        mock_timer.isActive.return_value = True

        queue.enqueue("opt10001", "req_A", "1001", {"key": "a"})
        queue.enqueue("opt10002", "req_B", "1002", {"key": "b"})
        queue.enqueue("opt10003", "req_C", "1003", {"key": "c"})

        # Process all three manually
        queue._process_next()
        queue._process_next()
        queue._process_next()

        rq_names = [
            c.args[0] for c in mock_kiwoom_api.comm_rq_data.call_args_list
        ]
        assert rq_names == ["req_A", "req_B", "req_C"]

    def test_empty_queue_stops_timer(self, mock_kiwoom_api):
        """After processing last item, timer.stop() is called and queue_empty emitted."""
        queue, mock_timer = self._make_queue(mock_kiwoom_api)
        mock_timer.isActive.return_value = False

        # Enqueue 1 item -- it gets processed immediately
        queue.enqueue("opt10001", "req_A", "1001", {"key": "a"})
        mock_timer.stop.reset_mock()

        # Next _process_next should find empty queue and stop timer
        queue._process_next()
        mock_timer.stop.assert_called_once()

    def test_pending_count(self, mock_kiwoom_api):
        """pending_count reflects the current queue length."""
        queue, mock_timer = self._make_queue(mock_kiwoom_api)
        mock_timer.isActive.return_value = True

        queue.enqueue("opt10001", "req_A", "1001", {"key": "a"})
        queue.enqueue("opt10002", "req_B", "1002", {"key": "b"})
        assert queue.pending_count == 2

        queue._process_next()
        assert queue.pending_count == 1

    def test_interval_set(self, mock_kiwoom_api):
        """QTimer interval is set to the configured value (default 4000ms)."""
        queue, mock_timer = self._make_queue(mock_kiwoom_api, interval_ms=4000)
        mock_timer.setInterval.assert_called_with(4000)
