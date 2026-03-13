"""Central notification dispatcher -- routes events to enabled channels."""

import os
import time

from loguru import logger

from kiwoom_trader.gui.notification.discord_sender import (
    DiscordSendWorker,
    build_trade_embed,
)


class Notifier:
    """Routes notification events to enabled channels (log, GUI toast, Discord).

    Each channel can be independently toggled via config dict.
    All sends are fire-and-forget -- failures are logged but never propagated.

    Args:
        config: Notification config dict with keys:
            gui_popup_enabled, log_enabled, discord_enabled, discord_rate_limit_sec.
        main_window: Optional MainWindow instance for GUI toast display.
    """

    def __init__(self, config: dict, main_window=None):
        self._config = config
        self._main_window = main_window
        self._last_discord_time: float = 0.0
        self._discord_workers: list = []  # prevent GC of active workers

    def notify(
        self,
        event_type: str,
        title: str,
        message: str,
        data: dict = None,
    ):
        """Dispatch notification to all enabled channels.

        Args:
            event_type: "trade", "signal", or "error".
            title: Short notification title.
            message: Detailed message body.
            data: Optional structured data (code, price, side, etc.).
        """
        # Log channel (NOTI-02)
        if self._config.get("log_enabled", True):
            try:
                logger.bind(log_type="trade").info(
                    f"[{event_type.upper()}] {title}: {message}"
                )
            except Exception:
                pass

        # GUI toast channel (NOTI-01)
        if self._config.get("gui_popup_enabled", True) and self._main_window:
            try:
                self._main_window.show_toast(title, message, event_type)
            except Exception:
                pass

        # Discord channel (NOTI-03)
        if self._config.get("discord_enabled", False):
            self._send_discord(event_type, title, message, data)

    def _send_discord(
        self,
        event_type: str,
        title: str,
        message: str,
        data: dict = None,
    ):
        """Send notification to Discord webhook with rate limiting.

        Rate limit: drops messages sent within discord_rate_limit_sec of the last send.
        """
        rate_limit = self._config.get("discord_rate_limit_sec", 2)
        now = time.time()

        if now - self._last_discord_time < rate_limit:
            logger.debug(
                f"Discord rate limited: dropped [{event_type}] {title}"
            )
            return

        # Build payload
        if data and "side" in data:
            payload = build_trade_embed(data, data["side"])
        else:
            payload = {"content": f"[{event_type.upper()}] {title}: {message}"}

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        worker = DiscordSendWorker(payload=payload, webhook_url=webhook_url)
        self._discord_workers.append(worker)
        worker.start()
        self._last_discord_time = now

        # Clean up finished workers
        self._discord_workers = [
            w for w in self._discord_workers if w.is_alive()
        ]
