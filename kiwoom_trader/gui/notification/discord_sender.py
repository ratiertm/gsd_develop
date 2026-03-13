"""Discord webhook sender with background thread worker."""

import json
import os
import urllib.request
import threading

from loguru import logger


def build_trade_embed(trade_data: dict, side: str) -> dict:
    """Build Discord embed payload for trade notification.

    Args:
        trade_data: Dict with keys: code, price, qty, strategy, pnl_pct, timestamp.
        side: "BUY" or "SELL" -- determines embed color.

    Returns:
        Discord webhook payload dict with embeds array.
    """
    color = 0x26A69A if side == "BUY" else 0xEF5350
    title = f"{'매수' if side == 'BUY' else '매도'} 체결"

    return {
        "embeds": [
            {
                "title": title,
                "color": color,
                "fields": [
                    {
                        "name": "종목코드",
                        "value": trade_data.get("code", ""),
                        "inline": True,
                    },
                    {
                        "name": "가격",
                        "value": f"{trade_data.get('price', 0):,}원",
                        "inline": True,
                    },
                    {
                        "name": "수량",
                        "value": str(trade_data.get("qty", 0)),
                        "inline": True,
                    },
                    {
                        "name": "전략",
                        "value": trade_data.get("strategy", ""),
                        "inline": True,
                    },
                    {
                        "name": "수익률",
                        "value": f"{trade_data.get('pnl_pct', 0):.2f}%",
                        "inline": True,
                    },
                ],
                "timestamp": trade_data.get("timestamp", ""),
            }
        ]
    }


class DiscordSendWorker(threading.Thread):
    """Send Discord webhook payload in a background thread.

    Uses threading.Thread as a cross-platform fallback (QThread requires PyQt5).
    Fire-and-forget: all exceptions are caught and logged.

    Args:
        payload: Discord webhook JSON payload.
        webhook_url: Discord webhook URL. If empty, run() is a no-op.
    """

    def __init__(self, payload: dict, webhook_url: str = ""):
        super().__init__(daemon=True)
        self._payload = payload
        self._webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")

    def run(self):
        if not self._webhook_url:
            return
        try:
            data = json.dumps(self._payload).encode("utf-8")
            req = urllib.request.Request(
                self._webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.error(f"Discord webhook failed: {e}")
