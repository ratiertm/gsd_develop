"""Shared test fixtures for KiwoomDayTrader."""

import json
from unittest.mock import MagicMock

import pytest

from kiwoom_trader.config.settings import Settings
from kiwoom_trader.core.models import RiskConfig


@pytest.fixture
def mock_kiwoom_api():
    """Mock object mimicking KiwoomAPI interface.

    Provides mocked dynamicCall, connection state, and signal attributes
    without importing from kiwoom_trader.api.kiwoom_api (not yet implemented).
    """
    mock_api = MagicMock()

    # Connection state
    mock_api.get_connect_state.return_value = 1  # connected

    # dynamicCall returns
    mock_api.dynamicCall.return_value = ""

    # Signals as MagicMock (not real pyqtSignal -- those need Qt event loop)
    mock_api.connected = MagicMock()
    mock_api.disconnected = MagicMock()
    mock_api.tr_data_received = MagicMock()
    mock_api.real_data_received = MagicMock()

    # COM-style API methods
    mock_api.comm_connect = MagicMock()
    mock_api.set_input_value = MagicMock()
    mock_api.comm_rq_data = MagicMock(return_value=0)
    mock_api.get_comm_data = MagicMock(return_value="")
    mock_api.set_real_reg = MagicMock()
    mock_api.get_comm_real_data = MagicMock(return_value="")
    mock_api.set_real_remove = MagicMock()

    # Order/Chejan API methods (added in 02-02)
    mock_api.send_order = MagicMock(return_value=0)
    mock_api.get_chejan_data = MagicMock(return_value="")
    mock_api.chejan_data_received = MagicMock()

    return mock_api


@pytest.fixture
def mock_settings():
    """Returns a Settings-like object with default config dict (no file I/O)."""
    settings = MagicMock(spec=Settings)
    settings._config = Settings._default_config()
    settings.account_password = ""
    settings.is_simulation = True
    return settings


@pytest.fixture
def mock_risk_config():
    """Returns a RiskConfig with user-locked defaults."""
    return RiskConfig()


@pytest.fixture
def mock_position_tracker():
    """Mock PositionTracker with get_position, get_all_positions, update_from_chejan."""
    tracker = MagicMock()
    tracker.get_position.return_value = None
    tracker.get_all_positions.return_value = {}
    tracker.update_from_chejan = MagicMock()
    return tracker


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
    yield config_file
