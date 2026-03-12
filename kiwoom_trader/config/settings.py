"""Application settings from config.json + .env"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger


class Settings:
    """Application settings from config.json + .env"""

    def __init__(self, config_path: str = "config.json"):
        load_dotenv()
        self._config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"Config loaded from {self._config_path}")
                return config
        else:
            logger.warning(
                f"Config file not found: {self._config_path}, using defaults"
            )
            return self._default_config()

    @staticmethod
    def _default_config() -> dict:
        return {
            "tr_interval_ms": 4000,
            "heartbeat_interval_ms": 30000,
            "max_reconnect_retries": 5,
            "real_data_fids": {
                "stock_execution": "10;11;12;13;15;20;21;25;27;28;41;61;62;63;64;65;66;67;68;69",
                "stock_orderbook": "41;61;62;63;64;65;66;67;68;69;71;72;73;74;75;76;77;78;79;80",
            },
            "watchlist": [],
            "log_dir": "logs",
        }

    @property
    def account_password(self) -> str:
        return os.getenv("KIWOOM_ACCOUNT_PW", "")

    @property
    def is_simulation(self) -> bool:
        return os.getenv("KIWOOM_SIMULATION", "true").lower() == "true"
