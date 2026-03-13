"""Application settings from config.json + .env"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from kiwoom_trader.core.models import RiskConfig


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
            "mode": "paper",
            "candle_interval_minutes": 1,
            "strategies": [
                {
                    "name": "RSI_REVERSAL",
                    "enabled": True,
                    "priority": 10,
                    "cooldown_sec": 300,
                    "indicators": {
                        "rsi": {"type": "rsi", "period": 14},
                    },
                    "entry_rule": {
                        "logic": "AND",
                        "conditions": [
                            {"indicator": "rsi", "operator": "lt", "value": 30},
                        ],
                    },
                    "exit_rule": {
                        "logic": "AND",
                        "conditions": [
                            {"indicator": "rsi", "operator": "gt", "value": 70},
                        ],
                    },
                },
                {
                    "name": "MA_CROSSOVER",
                    "enabled": True,
                    "priority": 20,
                    "cooldown_sec": 300,
                    "indicators": {
                        "ema_short": {"type": "ema", "period": 5},
                        "ema_long": {"type": "ema", "period": 20},
                    },
                    "entry_rule": {
                        "logic": "AND",
                        "conditions": [
                            {"indicator": "ema_short", "operator": "cross_above", "value": 0},
                        ],
                    },
                    "exit_rule": {
                        "logic": "AND",
                        "conditions": [
                            {"indicator": "ema_short", "operator": "cross_below", "value": 0},
                        ],
                    },
                },
            ],
            "watchlist_strategies": {
                "005930": ["RSI_REVERSAL", "MA_CROSSOVER"],
                "035720": ["RSI_REVERSAL"],
            },
            "notification": {
                "gui_popup_enabled": True,
                "log_enabled": True,
                "discord_enabled": False,
                "discord_rate_limit_sec": 2,
            },
            "risk": {
                "stop_loss_pct": -2.0,
                "take_profit_pct": 3.0,
                "trailing_stop_pct": 1.5,
                "max_symbol_weight_pct": 20.0,
                "max_positions": 5,
                "daily_loss_limit_pct": 3.0,
                "split_count": 3,
                "split_interval_sec": 45,
                "trading_start": "09:05",
                "trading_end_new_buy": "15:15",
                "auction_start_am": "08:30",
                "auction_end_am": "09:00",
                "auction_start_pm": "15:20",
                "auction_end_pm": "15:30",
            },
        }

    def save(self):
        """Write current config to disk (JSON with indent=2)."""
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
        logger.info(f"Config saved to {self._config_path}")

    @property
    def notification_config(self) -> dict:
        """Return notification settings section."""
        return self._config.get("notification", {})

    @property
    def account_password(self) -> str:
        return os.getenv("KIWOOM_ACCOUNT_PW", "")

    @property
    def is_simulation(self) -> bool:
        return os.getenv("KIWOOM_SIMULATION", "true").lower() == "true"

    @property
    def account_no(self) -> str:
        return os.getenv("KIWOOM_ACCOUNT_NO", "")

    @property
    def strategy_config(self) -> dict:
        """Return strategy-related config section."""
        return {
            "mode": self._config.get("mode", "paper"),
            "candle_interval_minutes": self._config.get("candle_interval_minutes", 1),
            "strategies": self._config.get("strategies", []),
            "watchlist_strategies": self._config.get("watchlist_strategies", {}),
            "total_capital": self._config.get("total_capital", 10_000_000),
        }

    @property
    def risk_config(self) -> RiskConfig:
        """Return RiskConfig dataclass populated from config.json risk section."""
        risk_dict = self._config.get("risk", {})
        return RiskConfig(**risk_dict) if risk_dict else RiskConfig()
