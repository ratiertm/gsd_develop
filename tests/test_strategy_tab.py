"""Tests for StrategyTab pure functions: validation, serialization, watchlist operations."""

import pytest

from kiwoom_trader.gui.strategy_tab import (
    validate_strategy,
    form_to_strategy_dict,
    strategy_dict_to_form_data,
    copy_strategy_name,
    watchlist_add_code,
    watchlist_remove_code,
    watchlist_assign_strategy,
)


# ------------------------------------------------------------------ #
# Sample fixtures
# ------------------------------------------------------------------ #

def _valid_strategy_dict():
    """Return a minimal valid strategy dict."""
    return {
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
    }


# ------------------------------------------------------------------ #
# test_strategy_to_dict
# ------------------------------------------------------------------ #

class TestFormToStrategyDict:
    def test_strategy_to_dict(self):
        """Form data serializes to valid strategy dict with correct structure."""
        result = form_to_strategy_dict(
            name="TEST_STRAT",
            enabled=True,
            priority=15,
            cooldown_sec=120,
            indicators=[
                {"name": "rsi", "type": "rsi", "period": 14},
            ],
            entry_conditions=[
                {"indicator": "rsi", "operator": "lt", "value": 30},
            ],
            entry_logic="AND",
            exit_conditions=[
                {"indicator": "rsi", "operator": "gt", "value": 70},
            ],
            exit_logic="AND",
        )
        assert result["name"] == "TEST_STRAT"
        assert result["enabled"] is True
        assert result["priority"] == 15
        assert result["cooldown_sec"] == 120
        assert "rsi" in result["indicators"]
        assert result["indicators"]["rsi"]["type"] == "rsi"
        assert result["indicators"]["rsi"]["period"] == 14
        assert result["entry_rule"]["logic"] == "AND"
        assert len(result["entry_rule"]["conditions"]) == 1
        assert result["exit_rule"]["logic"] == "AND"
        assert len(result["exit_rule"]["conditions"]) == 1


# ------------------------------------------------------------------ #
# test_dict_to_form
# ------------------------------------------------------------------ #

class TestStrategyDictToFormData:
    def test_dict_to_form(self):
        """Strategy dict populates form fields correctly."""
        strategy = _valid_strategy_dict()
        form = strategy_dict_to_form_data(strategy)
        assert form["name"] == "RSI_REVERSAL"
        assert form["enabled"] is True
        assert form["priority"] == 10
        assert form["cooldown_sec"] == 300
        assert len(form["indicators"]) == 1
        assert form["indicators"][0]["name"] == "rsi"
        assert form["indicators"][0]["type"] == "rsi"
        assert form["indicators"][0]["period"] == 14
        assert form["entry_logic"] == "AND"
        assert len(form["entry_conditions"]) == 1
        assert form["exit_logic"] == "AND"
        assert len(form["exit_conditions"]) == 1


# ------------------------------------------------------------------ #
# Validation tests
# ------------------------------------------------------------------ #

class TestValidateStrategy:
    def test_validate_strategy_requires_name(self):
        """Empty name returns validation error."""
        s = _valid_strategy_dict()
        s["name"] = ""
        errors = validate_strategy(s)
        assert any("name" in e.lower() for e in errors)

    def test_validate_strategy_requires_entry_rule(self):
        """Strategy with no entry conditions returns error."""
        s = _valid_strategy_dict()
        s["entry_rule"]["conditions"] = []
        errors = validate_strategy(s)
        assert any("entry" in e.lower() for e in errors)

    def test_validate_strategy_requires_exit_rule(self):
        """Strategy with no exit conditions returns error."""
        s = _valid_strategy_dict()
        s["exit_rule"]["conditions"] = []
        errors = validate_strategy(s)
        assert any("exit" in e.lower() for e in errors)

    def test_validate_indicator_type(self):
        """Invalid indicator type returns validation error."""
        s = _valid_strategy_dict()
        s["indicators"]["bad_ind"] = {"type": "nonexistent", "period": 10}
        errors = validate_strategy(s)
        assert any("indicator" in e.lower() or "type" in e.lower() for e in errors)

    def test_validate_operator(self):
        """Invalid operator returns validation error."""
        s = _valid_strategy_dict()
        s["entry_rule"]["conditions"][0]["operator"] = "invalid_op"
        errors = validate_strategy(s)
        assert any("operator" in e.lower() for e in errors)

    def test_valid_strategy_no_errors(self):
        """Valid strategy produces no errors."""
        s = _valid_strategy_dict()
        errors = validate_strategy(s)
        assert errors == []


# ------------------------------------------------------------------ #
# Copy strategy
# ------------------------------------------------------------------ #

class TestCopyStrategy:
    def test_copy_strategy_creates_duplicate(self):
        """Copy appends '_copy' to name."""
        assert copy_strategy_name("RSI_REVERSAL") == "RSI_REVERSAL_copy"

    def test_copy_already_copied(self):
        """Copy of a copy still appends '_copy'."""
        assert copy_strategy_name("RSI_REVERSAL_copy") == "RSI_REVERSAL_copy_copy"


# ------------------------------------------------------------------ #
# Watchlist operations
# ------------------------------------------------------------------ #

class TestWatchlistOperations:
    def test_watchlist_add_code(self):
        """Adding stock code updates watchlist_strategies in config."""
        config = {"watchlist_strategies": {}}
        watchlist_add_code(config, "005930")
        assert "005930" in config["watchlist_strategies"]
        assert config["watchlist_strategies"]["005930"] == []

    def test_watchlist_add_code_no_duplicate(self):
        """Adding existing code does not overwrite."""
        config = {"watchlist_strategies": {"005930": ["RSI"]}}
        watchlist_add_code(config, "005930")
        assert config["watchlist_strategies"]["005930"] == ["RSI"]

    def test_watchlist_remove_code(self):
        """Removing stock code removes from watchlist_strategies."""
        config = {"watchlist_strategies": {"005930": ["RSI"], "035720": []}}
        watchlist_remove_code(config, "005930")
        assert "005930" not in config["watchlist_strategies"]
        assert "035720" in config["watchlist_strategies"]

    def test_watchlist_remove_nonexistent(self):
        """Removing nonexistent code is a no-op."""
        config = {"watchlist_strategies": {}}
        watchlist_remove_code(config, "999999")  # Should not raise

    def test_watchlist_assign_strategy(self):
        """Assigning strategy to stock code updates config."""
        config = {"watchlist_strategies": {"005930": []}}
        watchlist_assign_strategy(config, "005930", ["RSI_REVERSAL", "MA_CROSSOVER"])
        assert config["watchlist_strategies"]["005930"] == ["RSI_REVERSAL", "MA_CROSSOVER"]
