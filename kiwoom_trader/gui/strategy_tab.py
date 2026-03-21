"""Strategy settings tab: CRUD for strategies, validation, watchlist management.

Provides:
- StrategyTab QWidget with strategy list, form editor, and watchlist manager
- Pure functions for validation, serialization, and watchlist operations (testable)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from kiwoom_trader.core.strategy_manager import INDICATOR_CLASSES

# Valid operators matching ConditionEngine._eval_condition
OPERATORS = {"gt", "lt", "gte", "lte", "cross_above", "cross_below"}

try:
    from PyQt5.QtCore import QDate, Qt
    from PyQt5.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    _HAS_PYQT5 = True
except ImportError:
    _HAS_PYQT5 = False
    QWidget = object

from kiwoom_trader.config.settings import Settings


# ------------------------------------------------------------------ #
# Valid indicator types and operators (re-exported for validation)
# ------------------------------------------------------------------ #

VALID_INDICATOR_TYPES = set(INDICATOR_CLASSES.keys())
VALID_OPERATORS = OPERATORS


# ------------------------------------------------------------------ #
# Pure functions: validation
# ------------------------------------------------------------------ #

def validate_strategy(strategy_dict: dict) -> list[str]:
    """Validate a strategy dict, returning list of error messages.

    Checks:
        - name not empty
        - at least one entry condition
        - at least one exit condition
        - all indicator types in INDICATOR_CLASSES keys
        - all operators in valid set
        - condition values are numeric
    """
    errors: list[str] = []

    # Name check
    if not strategy_dict.get("name", "").strip():
        errors.append("Strategy name is required")

    # Entry rule check
    entry_conditions = strategy_dict.get("entry_rule", {}).get("conditions", [])
    if not entry_conditions:
        errors.append("At least one entry condition is required")

    # Exit rule check
    exit_conditions = strategy_dict.get("exit_rule", {}).get("conditions", [])
    if not exit_conditions:
        errors.append("At least one exit condition is required")

    # Indicator type check
    for ind_name, ind_config in strategy_dict.get("indicators", {}).items():
        ind_type = ind_config.get("type", "")
        if ind_type not in VALID_INDICATOR_TYPES:
            errors.append(f"Invalid indicator type '{ind_type}' for indicator '{ind_name}'")

    # Operator and value check for all conditions
    all_conditions = entry_conditions + exit_conditions
    for cond in all_conditions:
        op = cond.get("operator", "")
        if op not in VALID_OPERATORS:
            errors.append(f"Invalid operator '{op}' in condition")
        val = cond.get("value")
        if val is not None and not isinstance(val, (int, float)):
            try:
                float(val)
            except (TypeError, ValueError):
                errors.append(f"Non-numeric value '{val}' in condition")

    return errors


# ------------------------------------------------------------------ #
# Pure functions: serialization
# ------------------------------------------------------------------ #

def form_to_strategy_dict(
    name: str,
    enabled: bool,
    priority: int,
    cooldown_sec: int,
    indicators: list[dict],
    entry_conditions: list[dict],
    entry_logic: str,
    exit_conditions: list[dict],
    exit_logic: str,
) -> dict:
    """Serialize form field values into a strategy dict.

    Args:
        name: Strategy name.
        enabled: Whether strategy is active.
        priority: Priority (higher wins conflict resolution).
        cooldown_sec: Seconds between signals.
        indicators: List of {"name": str, "type": str, "period": int}.
        entry_conditions: List of {"indicator": str, "operator": str, "value": float}.
        entry_logic: "AND" or "OR".
        exit_conditions: List of {"indicator": str, "operator": str, "value": float}.
        exit_logic: "AND" or "OR".

    Returns:
        Strategy dict matching Settings config format.
    """
    ind_dict = {}
    for ind in indicators:
        ind_name = ind["name"]
        ind_dict[ind_name] = {
            "type": ind["type"],
            "period": ind["period"],
        }

    def _serialize_condition(c):
        cond = {"indicator": c["indicator"], "operator": c["operator"]}
        if "value_ref" in c and c["value_ref"]:
            cond["value_ref"] = c["value_ref"]
        else:
            cond["value"] = c.get("value", 0)
        return cond

    return {
        "name": name,
        "enabled": enabled,
        "priority": priority,
        "cooldown_sec": cooldown_sec,
        "indicators": ind_dict,
        "entry_rule": {
            "logic": entry_logic,
            "conditions": [_serialize_condition(c) for c in entry_conditions],
        },
        "exit_rule": {
            "logic": exit_logic,
            "conditions": [_serialize_condition(c) for c in exit_conditions],
        },
    }


def strategy_dict_to_form_data(strategy_dict: dict) -> dict:
    """Deserialize a strategy dict into form field values.

    Returns:
        Dict with keys: name, enabled, priority, cooldown_sec, indicators (list),
        entry_logic, entry_conditions (list), exit_logic, exit_conditions (list).
    """
    indicators = []
    for ind_name, ind_config in strategy_dict.get("indicators", {}).items():
        indicators.append({
            "name": ind_name,
            "type": ind_config.get("type", ""),
            "period": ind_config.get("period", 0),
        })

    entry_rule = strategy_dict.get("entry_rule", {})
    exit_rule = strategy_dict.get("exit_rule", {})

    return {
        "name": strategy_dict.get("name", ""),
        "enabled": strategy_dict.get("enabled", True),
        "priority": strategy_dict.get("priority", 0),
        "cooldown_sec": strategy_dict.get("cooldown_sec", 300),
        "indicators": indicators,
        "entry_logic": entry_rule.get("logic", "AND"),
        "entry_conditions": entry_rule.get("conditions", []),
        "exit_logic": exit_rule.get("logic", "AND"),
        "exit_conditions": exit_rule.get("conditions", []),
    }


# ------------------------------------------------------------------ #
# Pure functions: copy helper
# ------------------------------------------------------------------ #

def copy_strategy_name(original_name: str) -> str:
    """Generate a copy name by appending '_copy'."""
    return f"{original_name}_copy"


# ------------------------------------------------------------------ #
# Pure functions: watchlist operations
# ------------------------------------------------------------------ #

def watchlist_add_code(config: dict, code: str) -> None:
    """Add a stock code to watchlist_strategies if not already present.

    Modifies config dict in-place.
    """
    ws = config.setdefault("watchlist_strategies", {})
    if code not in ws:
        ws[code] = []


def watchlist_remove_code(config: dict, code: str) -> None:
    """Remove a stock code from watchlist_strategies.

    Modifies config dict in-place. No-op if code not present.
    """
    ws = config.get("watchlist_strategies", {})
    ws.pop(code, None)


def watchlist_assign_strategy(config: dict, code: str, strategies: list[str]) -> None:
    """Assign strategies to a stock code in watchlist_strategies.

    Modifies config dict in-place.
    """
    ws = config.setdefault("watchlist_strategies", {})
    ws[code] = strategies


# ------------------------------------------------------------------ #
# StrategyTab widget
# ------------------------------------------------------------------ #

class StrategyTab(QWidget if _HAS_PYQT5 else object):
    """Strategy editor tab with strategy list, form editor, and watchlist manager.

    Args:
        settings: Application Settings instance.
        on_strategy_reload: Optional callback invoked after save to trigger
            StrategyManager re-initialization (hot-swap).
    """

    def __init__(
        self,
        settings: Settings,
        on_strategy_reload: Callable | None = None,
        on_backtest_requested: Callable | None = None,
    ) -> None:
        if _HAS_PYQT5:
            super().__init__()
        self._settings = settings
        self._on_strategy_reload = on_strategy_reload
        self._on_backtest_requested = on_backtest_requested
        self._current_strategy_index: int = -1

        # GUI state for indicator/condition rows
        self._indicator_rows: list[dict] = []
        self._entry_condition_rows: list[dict] = []
        self._exit_condition_rows: list[dict] = []
        self._stock_names_cache: dict[str, str] = {}  # code -> name cache

        if _HAS_PYQT5:
            self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the full strategy tab layout."""
        layout = QVBoxLayout(self)

        # Top section: strategy list + editor
        top_splitter = QSplitter(Qt.Horizontal)

        # --- Left panel (30%): Strategy list + action buttons ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self._strategy_list = QListWidget()
        self._load_strategy_names()
        self._strategy_list.currentRowChanged.connect(self._on_strategy_selected)
        left_layout.addWidget(self._strategy_list)

        btn_layout = QHBoxLayout()
        btn_new = QPushButton("New")
        btn_new.clicked.connect(self._on_new_strategy)
        btn_copy = QPushButton("Copy")
        btn_copy.clicked.connect(self._on_copy_strategy)
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self._on_delete_strategy)
        btn_layout.addWidget(btn_new)
        btn_layout.addWidget(btn_copy)
        btn_layout.addWidget(btn_delete)
        left_layout.addLayout(btn_layout)

        top_splitter.addWidget(left_panel)

        # --- Right panel (70%): Strategy editor form ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Basic fields
        form = QFormLayout()
        self._name_edit = QLineEdit()
        self._enabled_check = QCheckBox()
        self._enabled_check.setChecked(True)
        self._priority_spin = QSpinBox()
        self._priority_spin.setRange(1, 100)
        self._cooldown_spin = QSpinBox()
        self._cooldown_spin.setRange(0, 3600)
        form.addRow("Name:", self._name_edit)
        form.addRow("Enabled:", self._enabled_check)
        form.addRow("Priority:", self._priority_spin)
        form.addRow("Cooldown (sec):", self._cooldown_spin)
        right_layout.addLayout(form)

        # Indicators section
        self._indicators_group = QGroupBox("Indicators")
        self._indicators_layout = QVBoxLayout()
        btn_add_ind = QPushButton("Add Indicator")
        btn_add_ind.clicked.connect(self._add_indicator_row)
        self._indicators_layout.addWidget(btn_add_ind)
        self._indicators_group.setLayout(self._indicators_layout)
        right_layout.addWidget(self._indicators_group)

        # Entry rules section
        entry_group = QGroupBox("Entry Rules")
        entry_layout = QVBoxLayout()
        entry_header = QHBoxLayout()
        entry_header.addWidget(QLabel("Logic:"))
        self._entry_logic_combo = QComboBox()
        self._entry_logic_combo.addItems(["AND", "OR"])
        entry_header.addWidget(self._entry_logic_combo)
        btn_add_entry = QPushButton("Add Condition")
        btn_add_entry.clicked.connect(lambda: self._add_condition_row("entry"))
        entry_header.addWidget(btn_add_entry)
        entry_layout.addLayout(entry_header)
        self._entry_conditions_layout = QVBoxLayout()
        entry_layout.addLayout(self._entry_conditions_layout)
        entry_group.setLayout(entry_layout)
        right_layout.addWidget(entry_group)

        # Exit rules section
        exit_group = QGroupBox("Exit Rules")
        exit_layout = QVBoxLayout()
        exit_header = QHBoxLayout()
        exit_header.addWidget(QLabel("Logic:"))
        self._exit_logic_combo = QComboBox()
        self._exit_logic_combo.addItems(["AND", "OR"])
        exit_header.addWidget(self._exit_logic_combo)
        btn_add_exit = QPushButton("Add Condition")
        btn_add_exit.clicked.connect(lambda: self._add_condition_row("exit"))
        exit_header.addWidget(btn_add_exit)
        exit_layout.addLayout(exit_header)
        self._exit_conditions_layout = QVBoxLayout()
        exit_layout.addLayout(self._exit_conditions_layout)
        exit_group.setLayout(exit_layout)
        right_layout.addWidget(exit_group)

        # Save and Backtest buttons
        save_bt_layout = QHBoxLayout()
        btn_save = QPushButton("Save Strategy")
        btn_save.clicked.connect(self._on_save)
        save_bt_layout.addWidget(btn_save)

        btn_backtest = QPushButton("Backtest")
        btn_backtest.clicked.connect(self._on_backtest_clicked)
        save_bt_layout.addWidget(btn_backtest)
        right_layout.addLayout(save_bt_layout)

        top_splitter.addWidget(right_panel)
        top_splitter.setStretchFactor(0, 3)
        top_splitter.setStretchFactor(1, 7)

        layout.addWidget(top_splitter, stretch=10)

    # ------------------------------------------------------------------ #
    # Strategy list management
    # ------------------------------------------------------------------ #

    def _load_strategy_names(self) -> None:
        """Populate strategy list from config with enabled checkboxes."""
        self._strategy_list.clear()
        for s in self._settings._config.get("strategies", []):
            from PyQt5.QtWidgets import QListWidgetItem
            item = QListWidgetItem(s["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if s.get("enabled", True) else Qt.Unchecked)
            self._strategy_list.addItem(item)
        # Connect check state change to toggle enabled
        try:
            self._strategy_list.itemChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        self._strategy_list.itemChanged.connect(self._on_strategy_toggled)

    def _on_strategy_toggled(self, item) -> None:
        """Toggle strategy enabled state from checkbox."""
        index = self._strategy_list.row(item)
        strategies = self._settings._config.get("strategies", [])
        if 0 <= index < len(strategies):
            enabled = item.checkState() == Qt.Checked
            strategies[index]["enabled"] = enabled
            self._settings.save()
            if self._on_strategy_reload:
                self._on_strategy_reload()
            from loguru import logger
            logger.info(f"전략 {'활성화' if enabled else '비활성화'}: {strategies[index]['name']}")

    def _on_strategy_selected(self, index: int) -> None:
        """Load selected strategy into editor form."""
        self._current_strategy_index = index
        strategies = self._settings._config.get("strategies", [])
        if 0 <= index < len(strategies):
            form_data = strategy_dict_to_form_data(strategies[index])
            self._populate_form(form_data)

    def _populate_form(self, form_data: dict) -> None:
        """Fill the editor form with form_data dict."""
        self._name_edit.setText(form_data["name"])
        self._enabled_check.setChecked(form_data["enabled"])
        self._priority_spin.setValue(form_data["priority"])
        self._cooldown_spin.setValue(form_data["cooldown_sec"])

        # Clear and rebuild indicator rows
        self._clear_indicator_rows()
        for ind in form_data["indicators"]:
            self._add_indicator_row(ind["name"], ind["type"], ind["period"])

        # Clear and rebuild condition rows
        self._clear_condition_rows("entry")
        self._entry_logic_combo.setCurrentText(form_data["entry_logic"])
        for cond in form_data["entry_conditions"]:
            self._add_condition_row(
                "entry", cond.get("indicator", ""), cond.get("operator", "gt"),
                cond.get("value", 0) or 0, cond.get("value_ref", ""),
            )

        self._clear_condition_rows("exit")
        self._exit_logic_combo.setCurrentText(form_data["exit_logic"])
        for cond in form_data["exit_conditions"]:
            self._add_condition_row(
                "exit", cond.get("indicator", ""), cond.get("operator", "gt"),
                cond.get("value", 0) or 0, cond.get("value_ref", ""),
            )

    def _on_new_strategy(self) -> None:
        """Create a new empty strategy."""
        new_strat = {
            "name": "NEW_STRATEGY",
            "enabled": True,
            "priority": 10,
            "cooldown_sec": 300,
            "indicators": {},
            "entry_rule": {"logic": "AND", "conditions": []},
            "exit_rule": {"logic": "AND", "conditions": []},
        }
        strategies = self._settings._config.setdefault("strategies", [])
        strategies.append(new_strat)
        self._load_strategy_names()
        self._strategy_list.setCurrentRow(len(strategies) - 1)

    def _on_copy_strategy(self) -> None:
        """Copy currently selected strategy."""
        strategies = self._settings._config.get("strategies", [])
        if 0 <= self._current_strategy_index < len(strategies):
            import copy
            original = strategies[self._current_strategy_index]
            copied = copy.deepcopy(original)
            copied["name"] = copy_strategy_name(original["name"])
            strategies.append(copied)
            self._load_strategy_names()
            self._strategy_list.setCurrentRow(len(strategies) - 1)

    def _on_delete_strategy(self) -> None:
        """Delete currently selected strategy with confirmation."""
        strategies = self._settings._config.get("strategies", [])
        if 0 <= self._current_strategy_index < len(strategies):
            name = strategies[self._current_strategy_index]["name"]
            reply = QMessageBox.question(
                self, "Delete Strategy",
                f"Delete strategy '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                strategies.pop(self._current_strategy_index)
                self._settings.save()
                self._load_strategy_names()

    # ------------------------------------------------------------------ #
    # Indicator row management
    # ------------------------------------------------------------------ #

    def _add_indicator_row(
        self,
        name: str = "",
        ind_type: str = "sma",
        period: int = 14,
    ) -> None:
        """Add an indicator row to the editor."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("indicator name")
        type_combo = QComboBox()
        type_combo.addItems(sorted(VALID_INDICATOR_TYPES))
        type_combo.setCurrentText(ind_type)
        period_spin = QSpinBox()
        period_spin.setRange(1, 500)
        period_spin.setValue(period)
        btn_remove = QPushButton("Remove")

        row_layout.addWidget(name_edit)
        row_layout.addWidget(type_combo)
        row_layout.addWidget(period_spin)
        row_layout.addWidget(btn_remove)

        row_data = {
            "widget": row_widget,
            "name": name_edit,
            "type": type_combo,
            "period": period_spin,
        }
        self._indicator_rows.append(row_data)

        # Insert before the "Add" button
        self._indicators_layout.insertWidget(
            self._indicators_layout.count() - 1, row_widget,
        )

        btn_remove.clicked.connect(lambda: self._remove_indicator_row(row_data))

    def _remove_indicator_row(self, row_data: dict) -> None:
        """Remove an indicator row."""
        if row_data in self._indicator_rows:
            self._indicator_rows.remove(row_data)
            row_data["widget"].setParent(None)
            row_data["widget"].deleteLater()

    def _clear_indicator_rows(self) -> None:
        """Remove all indicator rows."""
        for row in list(self._indicator_rows):
            row["widget"].setParent(None)
            row["widget"].deleteLater()
        self._indicator_rows.clear()

    # ------------------------------------------------------------------ #
    # Condition row management
    # ------------------------------------------------------------------ #

    # Context keys available for value_ref (built-in + common sub-components)
    _VALUE_REF_OPTIONS = [
        "price", "volume", "hour", "minute",
        "prev_open", "prev_high", "prev_low", "prev_close",
        "prev_body_pct", "prev_range_pct", "prev_upper_wick_pct", "prev_lower_wick_pct",
        "gap_pct", "kospi_pct", "kosdaq_pct",
        "bollinger_upper", "bollinger_middle", "bollinger_lower",
        "macd_line", "macd_signal", "macd_histogram",
    ]

    def _add_condition_row(
        self,
        section: str,
        indicator: str = "",
        operator: str = "gt",
        value: float = 0,
        value_ref: str = "",
    ) -> None:
        """Add a condition row to entry or exit section."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        ind_combo = QComboBox()
        ind_combo.setEditable(True)
        ind_combo.setCurrentText(indicator)

        op_combo = QComboBox()
        op_combo.addItems(sorted(VALID_OPERATORS))
        op_combo.setCurrentText(operator)

        # Mode toggle: fixed value vs indicator reference
        mode_combo = QComboBox()
        mode_combo.addItems(["value", "ref"])
        mode_combo.setFixedWidth(50)

        val_spin = QDoubleSpinBox()
        val_spin.setRange(-99999, 99999)
        val_spin.setDecimals(2)
        val_spin.setValue(float(value))

        ref_combo = QComboBox()
        ref_combo.setEditable(True)
        ref_combo.addItems(self._VALUE_REF_OPTIONS)
        # Also add indicator names from current form
        for ind_row in self._indicator_rows:
            name = ind_row["name"].text()
            if name and name not in self._VALUE_REF_OPTIONS:
                ref_combo.addItem(name)

        btn_remove = QPushButton("X")
        btn_remove.setFixedWidth(30)

        row_layout.addWidget(ind_combo)
        row_layout.addWidget(op_combo)
        row_layout.addWidget(mode_combo)
        row_layout.addWidget(val_spin)
        row_layout.addWidget(ref_combo)
        row_layout.addWidget(btn_remove)

        # Toggle visibility based on mode
        def _toggle_mode():
            is_ref = mode_combo.currentText() == "ref"
            val_spin.setVisible(not is_ref)
            ref_combo.setVisible(is_ref)

        mode_combo.currentTextChanged.connect(lambda: _toggle_mode())

        # Set initial mode
        if value_ref:
            mode_combo.setCurrentText("ref")
            ref_combo.setCurrentText(value_ref)
        else:
            mode_combo.setCurrentText("value")
        _toggle_mode()

        row_data = {
            "widget": row_widget,
            "indicator": ind_combo,
            "operator": op_combo,
            "mode": mode_combo,
            "value": val_spin,
            "value_ref": ref_combo,
        }

        if section == "entry":
            self._entry_condition_rows.append(row_data)
            self._entry_conditions_layout.addWidget(row_widget)
        else:
            self._exit_condition_rows.append(row_data)
            self._exit_conditions_layout.addWidget(row_widget)

        btn_remove.clicked.connect(
            lambda: self._remove_condition_row(section, row_data)
        )

    def _remove_condition_row(self, section: str, row_data: dict) -> None:
        """Remove a condition row."""
        rows = (
            self._entry_condition_rows
            if section == "entry"
            else self._exit_condition_rows
        )
        if row_data in rows:
            rows.remove(row_data)
            row_data["widget"].setParent(None)
            row_data["widget"].deleteLater()

    def _clear_condition_rows(self, section: str) -> None:
        """Remove all condition rows in a section."""
        rows = (
            self._entry_condition_rows
            if section == "entry"
            else self._exit_condition_rows
        )
        for row in list(rows):
            row["widget"].setParent(None)
            row["widget"].deleteLater()
        rows.clear()

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def _on_save(self) -> None:
        """Validate, serialize, save config, and trigger reload."""
        # Collect form data
        indicators = []
        for row in self._indicator_rows:
            indicators.append({
                "name": row["name"].text(),
                "type": row["type"].currentText(),
                "period": row["period"].value(),
            })

        entry_conditions = []
        for row in self._entry_condition_rows:
            cond = {
                "indicator": row["indicator"].currentText(),
                "operator": row["operator"].currentText(),
            }
            if row["mode"].currentText() == "ref":
                cond["value_ref"] = row["value_ref"].currentText()
            else:
                cond["value"] = row["value"].value()
            entry_conditions.append(cond)

        exit_conditions = []
        for row in self._exit_condition_rows:
            cond = {
                "indicator": row["indicator"].currentText(),
                "operator": row["operator"].currentText(),
            }
            if row["mode"].currentText() == "ref":
                cond["value_ref"] = row["value_ref"].currentText()
            else:
                cond["value"] = row["value"].value()
            exit_conditions.append(cond)

        strategy = form_to_strategy_dict(
            name=self._name_edit.text(),
            enabled=self._enabled_check.isChecked(),
            priority=self._priority_spin.value(),
            cooldown_sec=self._cooldown_spin.value(),
            indicators=indicators,
            entry_conditions=entry_conditions,
            entry_logic=self._entry_logic_combo.currentText(),
            exit_conditions=exit_conditions,
            exit_logic=self._exit_logic_combo.currentText(),
        )

        # Validate
        errors = validate_strategy(strategy)
        if errors:
            QMessageBox.warning(
                self, "Validation Error",
                "\n".join(errors),
            )
            return

        # Update config
        strategies = self._settings._config.setdefault("strategies", [])
        if 0 <= self._current_strategy_index < len(strategies):
            strategies[self._current_strategy_index] = strategy
        else:
            strategies.append(strategy)

        self._settings.save()
        self._load_strategy_names()

        # Trigger hot-swap
        if self._on_strategy_reload:
            self._on_strategy_reload()

    # ------------------------------------------------------------------ #
    # Watchlist management
    # ------------------------------------------------------------------ #

    # Stock name resolver: set externally by main.py
    _stock_name_resolver = None  # Callable[[str], str] or None

    def _resolve_stock_name(self, code: str) -> str:
        """Get stock name for a code. Uses resolver → settings cache → local cache."""
        if self._stock_name_resolver:
            try:
                return self._stock_name_resolver(code)
            except Exception:
                pass
        # Fallback: settings shared cache → local cache
        return self._settings.get_stock_name(code) or self._stock_names_cache.get(code, "")

    def _load_watchlist(self) -> None:
        """Populate watchlist table from config."""
        ws = self._settings._config.get("watchlist_strategies", {})
        self._watchlist_table.setRowCount(len(ws))
        for row, (code, strats) in enumerate(ws.items()):
            name = self._resolve_stock_name(code)
            self._watchlist_table.setItem(row, 0, QTableWidgetItem(code))
            self._watchlist_table.setItem(row, 1, QTableWidgetItem(name))
            self._watchlist_table.setItem(
                row, 2, QTableWidgetItem(", ".join(strats)),
            )

    def _get_strategy_names(self) -> list[str]:
        """Get list of all strategy names from config."""
        return [s["name"] for s in self._settings._config.get("strategies", [])]

    def _show_strategy_picker(self, code: str, current: list[str] | None = None) -> list[str] | None:
        """Show dialog to pick strategies for a stock. Returns selected list or None if cancelled."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"전략 선택 — {code}")
        dialog.setMinimumWidth(300)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"종목 {code}에 적용할 전략을 선택하세요:"))

        checkboxes = []
        all_names = self._get_strategy_names()
        current = current or []
        for name in all_names:
            cb = QCheckBox(name)
            cb.setChecked(name in current)
            checkboxes.append((name, cb))
            layout.addWidget(cb)

        # Select all / none buttons
        btn_layout = QHBoxLayout()
        btn_all = QPushButton("전체 선택")
        btn_none = QPushButton("전체 해제")
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for _, cb in checkboxes])
        btn_none.clicked.connect(lambda: [cb.setChecked(False) for _, cb in checkboxes])
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        layout.addLayout(btn_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            return [name for name, cb in checkboxes if cb.isChecked()]
        return None

    def _on_add_stock(self) -> None:
        """Add stock code via dialog, then pick strategies."""
        code, ok = QInputDialog.getText(self, "종목 추가", "종목코드:")
        if not ok or not code.strip():
            return
        code = code.strip()

        # Pick strategies
        selected = self._show_strategy_picker(code, self._get_strategy_names())
        if selected is None:
            return

        watchlist_add_code(self._settings._config, code)
        watchlist_assign_strategy(self._settings._config, code, selected)
        self._settings.save()
        self._load_watchlist()

    def _on_remove_stock(self) -> None:
        """Remove selected stock from watchlist."""
        row = self._watchlist_table.currentRow()
        if row >= 0:
            code_item = self._watchlist_table.item(row, 0)
            if code_item:
                watchlist_remove_code(self._settings._config, code_item.text())
                self._settings.save()
                self._load_watchlist()

    def _on_watchlist_double_click(self, row: int, col: int) -> None:
        """Double-click watchlist row to edit strategy assignment."""
        code_item = self._watchlist_table.item(row, 0)
        if not code_item:
            return
        code = code_item.text()
        ws = self._settings._config.get("watchlist_strategies", {})
        current = ws.get(code, [])

        selected = self._show_strategy_picker(code, current)
        if selected is not None:
            watchlist_assign_strategy(self._settings._config, code, selected)
            self._settings.save()
            self._load_watchlist()

    # ------------------------------------------------------------------ #
    # Backtest
    # ------------------------------------------------------------------ #

    def _on_backtest_clicked(self) -> None:
        """Open backtest input dialog and trigger callback."""
        if not _HAS_PYQT5:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Backtest Settings")
        dialog.setMinimumWidth(350)
        layout = QFormLayout(dialog)

        code_edit = QLineEdit()
        code_edit.setPlaceholderText("e.g. 005930")
        layout.addRow("Stock Code:", code_edit)

        today = date.today()
        start_edit = QDateEdit()
        start_edit.setCalendarPopup(True)
        start_edit.setDate(QDate(today.year, today.month, today.day) .addMonths(-3))
        layout.addRow("Start Date:", start_edit)

        end_edit = QDateEdit()
        end_edit.setCalendarPopup(True)
        end_edit.setDate(QDate(today.year, today.month, today.day))
        layout.addRow("End Date:", end_edit)

        bt_cfg = self._settings._config.get("backtest", {})
        capital_spin = QSpinBox()
        capital_spin.setRange(1_000_000, 100_000_000)
        capital_spin.setSingleStep(1_000_000)
        capital_spin.setValue(bt_cfg.get("initial_capital", 10_000_000))
        capital_spin.setSuffix(" KRW")
        layout.addRow("Initial Capital:", capital_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            code = code_edit.text().strip()
            if not code:
                QMessageBox.warning(self, "Input Error", "Stock code is required.")
                return
            start_qdate = start_edit.date()
            end_qdate = end_edit.date()
            start_dt = date(start_qdate.year(), start_qdate.month(), start_qdate.day())
            end_dt = date(end_qdate.year(), end_qdate.month(), end_qdate.day())
            capital = capital_spin.value()

            if self._on_backtest_requested:
                self._on_backtest_requested(code, start_dt, end_dt, capital)
