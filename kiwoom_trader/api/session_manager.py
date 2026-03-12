"""Session lifecycle manager with auto-reconnect and subscription restore.

Monitors Kiwoom API connection via heartbeat, handles login success/failure,
reconnects with exponential backoff, and restores SetRealReg subscriptions
after successful reconnection.
"""

try:
    from PyQt5.QtCore import QTimer, QObject, pyqtSignal

    _HAS_PYQT5 = True
except ImportError:
    # Fallback for testing without PyQt5 (non-Windows environments)
    from unittest.mock import MagicMock

    QTimer = MagicMock
    QObject = object

    def pyqtSignal(*args, **kwargs):
        return MagicMock()

    _HAS_PYQT5 = False

from loguru import logger


class SessionManager(QObject):
    """Manages Kiwoom API session lifecycle with auto-reconnect.

    Signals:
        session_restored: Emitted on successful login/reconnection.
        session_lost: Emitted when heartbeat detects disconnection.
    """

    session_restored = pyqtSignal()
    session_lost = pyqtSignal()

    MAX_RETRIES = 5
    BASE_DELAY_MS = 5000  # 5 seconds
    MAX_DELAY_MS = 60000  # 1 minute

    def __init__(self, kiwoom_api):
        super().__init__()
        self._api = kiwoom_api
        self._retry_count = 0

        # Reconnection timer (single-shot, exponential backoff)
        self._reconnect_timer = QTimer()
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)

        # Heartbeat timer (periodic, checks connection state)
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.setInterval(30000)  # 30 seconds
        self._heartbeat_timer.timeout.connect(self._check_connection)

        # Tracked real-time subscriptions for restoration after reconnect
        self._real_subscriptions: list[dict] = []

        # Connect to API connected signal
        self._api.connected.connect(self._on_connect)

    def start_monitoring(self):
        """Start the heartbeat timer to monitor connection state."""
        self._heartbeat_timer.start()
        logger.info("Session monitoring started (30s heartbeat)")

    def _on_connect(self, err_code: int):
        """Handle login/reconnection result from OnEventConnect.

        Args:
            err_code: 0 for success, negative values for various failures.
        """
        if err_code == 0:
            logger.info("Login successful")
            self._retry_count = 0
            self._heartbeat_timer.start()
            if self._real_subscriptions:
                self._restore_real_subscriptions()
            self.session_restored.emit()
        else:
            logger.error(f"Login failed: err_code={err_code}")
            self._schedule_reconnect()

    def _check_connection(self):
        """Heartbeat check: verify connection state is still active."""
        state = self._api.get_connect_state()
        if state == 0:
            logger.warning("Connection lost detected by heartbeat")
            self._heartbeat_timer.stop()
            self.session_lost.emit()
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt with exponential backoff.

        Delay: BASE_DELAY_MS * 2^retry_count, capped at MAX_DELAY_MS.
        Stops after MAX_RETRIES attempts.
        """
        if self._retry_count >= self.MAX_RETRIES:
            logger.critical(
                f"Max reconnection attempts ({self.MAX_RETRIES}) reached. "
                "Manual intervention required."
            )
            return

        delay = min(
            self.BASE_DELAY_MS * (2 ** self._retry_count),
            self.MAX_DELAY_MS,
        )
        self._retry_count += 1
        logger.info(f"Reconnect attempt {self._retry_count} in {delay}ms")
        self._reconnect_timer.setInterval(delay)
        self._reconnect_timer.start()

    def _attempt_reconnect(self):
        """Execute the reconnection attempt via CommConnect."""
        logger.info("Attempting reconnection...")
        self._api.comm_connect()

    def track_real_subscription(
        self, screen_no: str, code_list: str, fid_list: str, real_type: str
    ):
        """Track a SetRealReg subscription for restoration after reconnect.

        Args:
            screen_no: 4-digit screen number string
            code_list: Semicolon-separated stock codes
            fid_list: Semicolon-separated FID numbers
            real_type: "0" = replace, "1" = add
        """
        self._real_subscriptions.append(
            {
                "screen_no": screen_no,
                "code_list": code_list,
                "fid_list": fid_list,
                "real_type": real_type,
            }
        )
        logger.debug(
            f"Tracked real subscription: screen={screen_no}, codes={code_list}"
        )

    def _restore_real_subscriptions(self):
        """Replay all tracked SetRealReg subscriptions after reconnect."""
        logger.info(
            f"Restoring {len(self._real_subscriptions)} real-time subscriptions"
        )
        for sub in self._real_subscriptions:
            self._api.set_real_reg(
                sub["screen_no"],
                sub["code_list"],
                sub["fid_list"],
                sub["real_type"],
            )
