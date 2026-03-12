"""Rate-limited TR request dispatcher using QTimer.

Enforces a minimum interval (default 4000ms) between TR requests to comply
with Kiwoom OpenAPI+ rate limits (1 request per 3.6s for sequential queries).
Requests are queued in FIFO order via collections.deque.
"""

from collections import deque

from loguru import logger

try:
    from PyQt5.QtCore import QTimer, QObject, pyqtSignal

    _HAS_PYQT5 = True
except ImportError:
    from unittest.mock import MagicMock

    QTimer = MagicMock
    QObject = object

    def pyqtSignal(*args, **kwargs):
        return MagicMock()

    _HAS_PYQT5 = False


class TRRequestQueue(QObject):
    """Rate-limited TR request dispatcher.

    Signals:
        queue_empty: Emitted when all queued requests have been dispatched.
    """

    queue_empty = pyqtSignal()

    def __init__(self, kiwoom_api, interval_ms: int = 4000):
        super().__init__()
        self._queue = deque()
        self._api = kiwoom_api

        self._timer = QTimer()
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._process_next)

    def enqueue(
        self,
        tr_code: str,
        rq_name: str,
        screen_no: str,
        inputs: dict,
        prev_next: int = 0,
        callback=None,
    ):
        """Add a TR request to the queue.

        If the queue is idle (timer not active), the first request is
        processed immediately and the timer starts for subsequent requests.

        Args:
            tr_code: Kiwoom TR code (e.g., "opt10001")
            rq_name: Request name for response routing
            screen_no: 4-digit screen number string
            inputs: Dict of SetInputValue key-value pairs
            prev_next: 0 for first request, 2 for continuation
            callback: Optional callback for when response arrives
        """
        self._queue.append(
            {
                "tr_code": tr_code,
                "rq_name": rq_name,
                "screen_no": screen_no,
                "inputs": inputs,
                "prev_next": prev_next,
                "callback": callback,
            }
        )
        logger.debug(
            f"TR enqueued: {rq_name} ({tr_code}), queue size: {len(self._queue)}"
        )

        if not self._timer.isActive():
            self._process_next()
            self._timer.start()

    def _process_next(self):
        """Pop and dispatch the next request in the queue.

        If the queue is empty, stops the timer and emits queue_empty.
        """
        if not self._queue:
            self._timer.stop()
            self.queue_empty.emit()
            return

        request = self._queue.popleft()
        for key, value in request["inputs"].items():
            self._api.set_input_value(key, value)

        ret = self._api.comm_rq_data(
            request["rq_name"],
            request["tr_code"],
            request["prev_next"],
            request["screen_no"],
        )
        logger.info(
            f"TR dispatched: {request['rq_name']} -> ret={ret}, "
            f"remaining={len(self._queue)}"
        )

    @property
    def pending_count(self) -> int:
        """Number of requests waiting in the queue."""
        return len(self._queue)
