"""Tests for config.json risk section and Settings.risk_config extension."""

import json
import os

import pytest


class TestConfigJsonRiskSection:
    """Tests that config.json contains a risk section with all defaults."""

    def test_config_json_has_risk_key(self):
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        assert "risk" in config

    def test_config_json_risk_values(self):
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        risk = config["risk"]
        assert risk["stop_loss_pct"] == -2.0
        assert risk["take_profit_pct"] == 3.0
        assert risk["trailing_stop_pct"] == 1.5
        assert risk["max_symbol_weight_pct"] == 20.0
        assert risk["max_positions"] == 5
        assert risk["daily_loss_limit_pct"] == 3.0
        assert risk["split_count"] == 3
        assert risk["split_interval_sec"] == 45
        assert risk["trading_start"] == "09:05"
        assert risk["trading_end_new_buy"] == "15:15"
        assert risk["auction_start_am"] == "08:30"
        assert risk["auction_end_am"] == "09:00"
        assert risk["auction_start_pm"] == "15:20"
        assert risk["auction_end_pm"] == "15:30"


class TestSettingsDefaultConfigRisk:
    """Tests that Settings._default_config() includes risk section."""

    def test_default_config_has_risk(self):
        from kiwoom_trader.config.settings import Settings

        defaults = Settings._default_config()
        assert "risk" in defaults
        risk = defaults["risk"]
        assert risk["stop_loss_pct"] == -2.0
        assert risk["take_profit_pct"] == 3.0
        assert risk["trailing_stop_pct"] == 1.5
        assert risk["max_positions"] == 5


class TestSettingsRiskConfig:
    """Tests for Settings.risk_config property."""

    def test_risk_config_returns_dataclass(self, tmp_path):
        from kiwoom_trader.config.settings import Settings
        from kiwoom_trader.core.models import RiskConfig

        # Create config.json with risk section
        config = {
            "tr_interval_ms": 4000,
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
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config), encoding="utf-8")

        s = Settings(config_path=str(config_file))
        rc = s.risk_config
        assert isinstance(rc, RiskConfig)
        assert rc.stop_loss_pct == -2.0
        assert rc.max_positions == 5

    def test_risk_config_uses_defaults_when_risk_missing(self):
        from kiwoom_trader.config.settings import Settings
        from kiwoom_trader.core.models import RiskConfig

        # Use nonexistent path so defaults kick in
        s = Settings(config_path="/nonexistent/config.json")
        rc = s.risk_config
        assert isinstance(rc, RiskConfig)
        assert rc.stop_loss_pct == -2.0
        assert rc.take_profit_pct == 3.0


class TestSettingsAccountNo:
    """Tests for Settings.account_no property."""

    def test_account_no_from_env(self, monkeypatch):
        from kiwoom_trader.config.settings import Settings

        monkeypatch.setenv("KIWOOM_ACCOUNT_NO", "1234567890")
        s = Settings(config_path="/nonexistent/config.json")
        assert s.account_no == "1234567890"

    def test_account_no_default_empty(self, monkeypatch):
        from kiwoom_trader.config.settings import Settings

        monkeypatch.delenv("KIWOOM_ACCOUNT_NO", raising=False)
        s = Settings(config_path="/nonexistent/config.json")
        assert s.account_no == ""
