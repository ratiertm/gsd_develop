"""Tests for Settings, constants, and logging configuration."""

import json
import os
import tempfile
from pathlib import Path

import pytest


class TestSettings:
    """Tests for kiwoom_trader.config.settings.Settings"""

    def test_load_default_config(self):
        """Settings with nonexistent path returns defaults with tr_interval_ms=4000."""
        from kiwoom_trader.config.settings import Settings

        s = Settings(config_path="/nonexistent/config.json")
        assert s._config["tr_interval_ms"] == 4000
        assert s._config["heartbeat_interval_ms"] == 30000
        assert s._config["max_reconnect_retries"] == 5
        assert s._config["watchlist"] == []
        assert s._config["log_dir"] == "logs"

    def test_load_valid_config(self, tmp_config_file):
        """Settings with valid config file returns values from file."""
        from kiwoom_trader.config.settings import Settings

        s = Settings(config_path=str(tmp_config_file))
        assert s._config["tr_interval_ms"] == 5000
        assert s._config["watchlist"] == ["005930", "000660"]

    def test_env_vars_simulation(self, monkeypatch):
        """With KIWOOM_SIMULATION=false in env, is_simulation returns False."""
        from kiwoom_trader.config.settings import Settings

        monkeypatch.setenv("KIWOOM_SIMULATION", "false")
        s = Settings(config_path="/nonexistent/config.json")
        assert s.is_simulation is False

    def test_env_vars_simulation_default(self, monkeypatch):
        """Without KIWOOM_SIMULATION env var, is_simulation defaults to True."""
        from kiwoom_trader.config.settings import Settings

        monkeypatch.delenv("KIWOOM_SIMULATION", raising=False)
        s = Settings(config_path="/nonexistent/config.json")
        assert s.is_simulation is True

    def test_account_password(self, monkeypatch):
        """account_password reads from KIWOOM_ACCOUNT_PW env var."""
        from kiwoom_trader.config.settings import Settings

        monkeypatch.setenv("KIWOOM_ACCOUNT_PW", "secret123")
        s = Settings(config_path="/nonexistent/config.json")
        assert s.account_password == "secret123"


class TestConstants:
    """Tests for kiwoom_trader.config.constants"""

    def test_constants_fid(self):
        """FID.CURRENT_PRICE == 10, FID.VOLUME == 13."""
        from kiwoom_trader.config.constants import FID

        assert FID.CURRENT_PRICE == 10
        assert FID.VOLUME == 13
        assert FID.EXEC_TIME == 20
        assert FID.EXEC_STRENGTH == 228

    def test_constants_login_error(self):
        """LOGIN_ERROR.SUCCESS == 0."""
        from kiwoom_trader.config.constants import LOGIN_ERROR

        assert LOGIN_ERROR.SUCCESS == 0
        assert LOGIN_ERROR.PASSWORD_ERROR == -100

    def test_constants_screen(self):
        """SCREEN has LOGIN and base numbers."""
        from kiwoom_trader.config.constants import SCREEN

        assert SCREEN.LOGIN == "0000"
        assert SCREEN.TR_BASE == 1000
        assert SCREEN.REAL_BASE == 5000


class TestLogging:
    """Tests for kiwoom_trader.utils.logger"""

    def test_setup_logging(self, tmp_path):
        """setup_logging() creates log directory without error."""
        from kiwoom_trader.utils.logger import setup_logging

        log_dir = str(tmp_path / "test_logs")
        setup_logging(log_dir)
        assert Path(log_dir).exists()


@pytest.fixture
def tmp_config_file(tmp_path):
    """Creates a temporary config.json with known values, yields path, cleans up."""
    config = {
        "tr_interval_ms": 5000,
        "heartbeat_interval_ms": 30000,
        "max_reconnect_retries": 3,
        "real_data_fids": {
            "stock_execution": "10;11;12;13",
            "stock_orderbook": "41;61;62;63",
        },
        "watchlist": ["005930", "000660"],
        "log_dir": "logs",
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")
    yield config_file
