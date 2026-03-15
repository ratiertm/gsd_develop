"""Dashboard tab: real-time positions, orders, P&L, system status, and log panel."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QFont, QTextCursor
    from PyQt5.QtWidgets import (
        QComboBox,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMessageBox,
        QPushButton,
        QSplitter,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    _HAS_PYQT5 = True
except ImportError:
    from unittest.mock import MagicMock

    Qt = MagicMock()
    QColor = MagicMock
    QFont = MagicMock
    QTextCursor = MagicMock()
    QComboBox = MagicMock
    QFormLayout = MagicMock
    QGroupBox = MagicMock
    QHBoxLayout = MagicMock
    QMessageBox = MagicMock
    QPushButton = MagicMock
    QHeaderView = MagicMock()
    QLabel = MagicMock
    QSplitter = MagicMock
    QTabWidget = MagicMock
    QTableWidget = MagicMock
    QTableWidgetItem = MagicMock
    QTextEdit = MagicMock
    QVBoxLayout = MagicMock
    QWidget = object

    _HAS_PYQT5 = False

if TYPE_CHECKING:
    from kiwoom_trader.core.models import Order, Position

# Maximum number of log lines to keep in the log panel
_MAX_LOG_LINES = 500

# Korean stock convention: red = up (상승), blue = down (하락)
_COLOR_POSITIVE = "#EF5350"  # red for gains
_COLOR_NEGATIVE = "#42A5F5"  # blue for losses


def pnl_color(value: int | float) -> str | None:
    """Return color hex string for P&L value. None for zero.

    Korean stock convention: positive = red (#EF5350), negative = blue (#42A5F5).
    """
    if value > 0:
        return _COLOR_POSITIVE
    elif value < 0:
        return _COLOR_NEGATIVE
    return None


def _format_price(value: int) -> str:
    """Format integer price with comma separators."""
    return f"{value:,}"


def _format_pct(value: float) -> str:
    """Format percentage with 2 decimal places."""
    return f"{value:.2f}"


class DashboardTab(QWidget if _HAS_PYQT5 else object):
    """Dashboard tab showing positions, orders, P&L, system status, and log.

    All data updates happen via method calls. The parent window (or controller)
    wires pyqtSignal connections to these methods for real-time push updates.
    """

    POSITION_COLUMNS = [
        "종목코드", "종목명", "수량", "매입가", "현재가",
        "평가손익", "수익률(%)", "비중(%)",
    ]

    ORDER_COLUMNS = [
        "주문번호", "종목코드", "매매구분", "주문유형", "주문수량",
        "주문가격", "상태", "체결수량", "체결가격",
    ]

    # Terminal states for order filtering
    _TERMINAL_STATES: set = set()

    def __init__(self, parent=None):
        if _HAS_PYQT5:
            super().__init__(parent)
        # Lazily import terminal states
        try:
            from kiwoom_trader.core.models import OrderState
            self._TERMINAL_STATES = {
                OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED,
            }
        except ImportError:
            pass

        # Internal data stores
        self._pnl_data: dict = {
            "daily_pnl": 0.0,
            "unrealized_pnl": 0,
            "total_invested": 0,
        }
        self._status_data: dict = {
            "connected": False,
            "market_state": "CLOSED",
            "strategy_count": 0,
            "mode": "paper",
        }
        self._log_lines: list[str] = []

        if _HAS_PYQT5:
            self._setup_ui()

    def _setup_ui(self):
        """Build the full dashboard layout."""
        layout = QVBoxLayout(self)

        # --- Top section (60%): positions + status/P&L ---
        top_splitter = QSplitter(Qt.Horizontal)

        # Positions table (left, ~60%)
        self._positions_table = QTableWidget()
        self._positions_table.setColumnCount(len(self.POSITION_COLUMNS))
        self._positions_table.setHorizontalHeaderLabels(self.POSITION_COLUMNS)
        self._positions_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch,
        )
        self._positions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        top_splitter.addWidget(self._positions_table)

        # Right panel: system status + P&L summary
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # System status group
        status_group = QGroupBox("시스템 상태")
        status_form = QFormLayout()
        self._lbl_connected = QLabel("--")
        self._lbl_market_state = QLabel("--")
        self._lbl_strategy_count = QLabel("--")
        self._cmb_account = QComboBox()
        self._lbl_user_name = QLabel("--")

        # Mode toggle button
        self._btn_mode = QPushButton("모의투자")
        self._btn_mode.setCheckable(True)
        self._btn_mode.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-weight: bold; padding: 4px 12px; border-radius: 4px; }"
            "QPushButton:checked { background-color: #EF5350; }"
        )
        self._btn_mode.clicked.connect(self._on_mode_toggle)
        self._on_mode_change = None  # external callback

        status_form.addRow("연결 상태:", self._lbl_connected)
        status_form.addRow("사용자:", self._lbl_user_name)
        status_form.addRow("계좌:", self._cmb_account)
        status_form.addRow("장 상태:", self._lbl_market_state)
        status_form.addRow("활성 전략:", self._lbl_strategy_count)
        status_form.addRow("모드:", self._btn_mode)
        status_group.setLayout(status_form)
        right_layout.addWidget(status_group)

        # P&L summary group
        pnl_group = QGroupBox("손익 요약")
        pnl_form = QFormLayout()
        self._lbl_daily_pnl = QLabel("0")
        self._lbl_unrealized_pnl = QLabel("0")
        self._lbl_total_invested = QLabel("0")
        pnl_form.addRow("일일 실현손익:", self._lbl_daily_pnl)
        pnl_form.addRow("평가손익:", self._lbl_unrealized_pnl)
        pnl_form.addRow("총 투자금액:", self._lbl_total_invested)
        pnl_group.setLayout(pnl_form)
        right_layout.addWidget(pnl_group)

        right_layout.addStretch()
        top_splitter.addWidget(right_panel)
        top_splitter.setStretchFactor(0, 6)  # positions 60%
        top_splitter.setStretchFactor(1, 4)  # right panel 40%

        layout.addWidget(top_splitter, stretch=6)

        # --- Middle section (25%): orders tabs ---
        orders_tabs = QTabWidget()

        self._pending_table = QTableWidget()
        self._pending_table.setColumnCount(len(self.ORDER_COLUMNS))
        self._pending_table.setHorizontalHeaderLabels(self.ORDER_COLUMNS)
        self._pending_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch,
        )
        self._pending_table.setEditTriggers(QTableWidget.NoEditTriggers)
        orders_tabs.addTab(self._pending_table, "대기 주문")

        self._filled_table = QTableWidget()
        self._filled_table.setColumnCount(len(self.ORDER_COLUMNS))
        self._filled_table.setHorizontalHeaderLabels(self.ORDER_COLUMNS)
        self._filled_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch,
        )
        self._filled_table.setEditTriggers(QTableWidget.NoEditTriggers)
        orders_tabs.addTab(self._filled_table, "체결 내역")

        layout.addWidget(orders_tabs, stretch=25)

        # --- Bottom section (15%): log panel ---
        self._log_panel = QTextEdit()
        self._log_panel.setReadOnly(True)
        self._log_panel.setFont(QFont("Courier New", 9))
        self._log_panel.setMaximumHeight(200)
        layout.addWidget(self._log_panel, stretch=15)

    # ------------------------------------------------------------------ #
    # Public data update methods
    # ------------------------------------------------------------------ #

    def build_position_rows(
        self, positions: dict[str, Position], total_invested: int,
    ) -> list[list]:
        """Convert Position dict into table row data.

        Returns list of [code, name, qty, avg_price, current_price,
        unrealized_pnl, pnl_pct, weight_pct] lists.
        """
        rows = []
        for code, pos in positions.items():
            # Derive current price from avg_price + per-share pnl
            current_price = (
                pos.avg_price + pos.unrealized_pnl // pos.qty
                if pos.qty > 0
                else pos.avg_price
            )
            pnl_pct = (
                (pos.unrealized_pnl / (pos.avg_price * pos.qty) * 100)
                if pos.avg_price * pos.qty > 0
                else 0.0
            )
            weight = (
                (pos.avg_price * pos.qty / total_invested * 100)
                if total_invested > 0
                else 0.0
            )
            rows.append([
                code,
                "",  # name placeholder -- resolved by code-name mapping
                pos.qty,
                pos.avg_price,
                current_price,
                pos.unrealized_pnl,
                round(pnl_pct, 2),
                round(weight, 2),
            ])
        return rows

    def update_positions(
        self, positions: dict[str, Position], total_invested: int,
    ) -> None:
        """Refresh the positions table with current data."""
        rows = self.build_position_rows(positions, total_invested)
        if _HAS_PYQT5:
            self._positions_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    if isinstance(val, int) and c >= 3:
                        text = _format_price(val)
                    elif isinstance(val, float):
                        text = _format_pct(val)
                    else:
                        text = str(val)
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter
                        if isinstance(val, (int, float))
                        else Qt.AlignLeft | Qt.AlignVCenter
                    )
                    # Color P&L columns
                    if c == 5:  # unrealized_pnl
                        color = pnl_color(val)
                        if color:
                            item.setForeground(QColor(color))
                    if c == 6:  # pnl_pct
                        color = pnl_color(val)
                        if color:
                            item.setForeground(QColor(color))
                    self._positions_table.setItem(r, c, item)

    def split_orders(self, orders: list[Order]) -> tuple[list[Order], list[Order]]:
        """Split orders into (pending, filled) lists.

        Pending: orders not in terminal states (FILLED, CANCELLED, REJECTED).
        Filled: orders in FILLED state only.
        """
        from kiwoom_trader.core.models import OrderState

        pending = [
            o for o in orders
            if o.state not in {OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED}
        ]
        filled = [o for o in orders if o.state == OrderState.FILLED]
        return pending, filled

    def update_orders(self, orders: list[Order]) -> None:
        """Refresh both pending and filled order tables."""
        pending, filled = self.split_orders(orders)
        if _HAS_PYQT5:
            self._populate_order_table(self._pending_table, pending)
            self._populate_order_table(self._filled_table, filled)

    def _populate_order_table(self, table, orders: list[Order]) -> None:
        """Fill a QTableWidget with order data."""
        table.setRowCount(len(orders))
        for r, order in enumerate(orders):
            values = [
                order.order_no,
                order.code,
                order.side.name,
                str(order.order_type),
                str(order.qty),
                _format_price(order.price),
                order.state.name,
                str(order.filled_qty),
                _format_price(order.filled_price),
            ]
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                table.setItem(r, c, item)

    def update_pnl(
        self, daily_pnl: float, unrealized_pnl: int, total_invested: int,
    ) -> None:
        """Update P&L summary display."""
        self._pnl_data["daily_pnl"] = daily_pnl
        self._pnl_data["unrealized_pnl"] = unrealized_pnl
        self._pnl_data["total_invested"] = total_invested

        if _HAS_PYQT5:
            self._lbl_daily_pnl.setText(_format_price(int(daily_pnl)))
            color = pnl_color(daily_pnl)
            if color:
                self._lbl_daily_pnl.setStyleSheet(f"color: {color};")
            else:
                self._lbl_daily_pnl.setStyleSheet("")

            self._lbl_unrealized_pnl.setText(_format_price(unrealized_pnl))
            color = pnl_color(unrealized_pnl)
            if color:
                self._lbl_unrealized_pnl.setStyleSheet(f"color: {color};")
            else:
                self._lbl_unrealized_pnl.setStyleSheet("")

            self._lbl_total_invested.setText(_format_price(total_invested))

    def _on_mode_toggle(self, checked: bool):
        """Handle mode button toggle with confirmation dialog."""
        if checked:
            # Switching to live
            reply = QMessageBox.warning(
                self, "실전투자 전환",
                "실전투자 모드로 전환하시겠습니까?\n실제 주문이 실행됩니다.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                self._btn_mode.setChecked(False)
                return
            self._btn_mode.setText("실전투자")
            new_mode = "live"
        else:
            self._btn_mode.setText("모의투자")
            new_mode = "paper"

        if self._on_mode_change:
            self._on_mode_change(new_mode)

    def get_mode(self) -> str:
        """Return current mode: 'paper' or 'live'."""
        return "live" if _HAS_PYQT5 and self._btn_mode.isChecked() else "paper"

    def set_accounts(
        self,
        accounts: list[str],
        user_name: str = "",
        server_label: str = "",
    ) -> None:
        """Populate account combo box after login.

        Args:
            accounts: List of account numbers from GetLoginInfo("ACCNO").
            user_name: User name from GetLoginInfo("USER_NAME").
            server_label: "모의투자" or "실거래".
        """
        if _HAS_PYQT5:
            self._cmb_account.clear()
            # Label accounts by suffix convention
            # 모의투자: 끝자리 31=주식, 11=선물옵션
            for acc in accounts:
                suffix = acc[-2:] if len(acc) >= 2 else ""
                if suffix == "31":
                    label = f"{acc} (주식)"
                elif suffix == "11":
                    label = f"{acc} (선물옵션)"
                else:
                    label = acc
                self._cmb_account.addItem(label, acc)
            if user_name:
                self._lbl_user_name.setText(f"{user_name} ({server_label})")

    def get_selected_account(self) -> str:
        """Return the currently selected account number."""
        if _HAS_PYQT5:
            return self._cmb_account.currentData() or ""
        return ""

    def update_status(
        self,
        connected: bool,
        market_state: str,
        strategy_count: int,
        mode: str,
    ) -> None:
        """Update system status display."""
        self._status_data["connected"] = connected
        self._status_data["market_state"] = market_state
        self._status_data["strategy_count"] = strategy_count
        self._status_data["mode"] = mode

        if _HAS_PYQT5:
            conn_text = "연결됨" if connected else "연결 안됨"
            conn_color = "#4CAF50" if connected else "#EF5350"
            self._lbl_connected.setText(conn_text)
            self._lbl_connected.setStyleSheet(f"color: {conn_color}; font-weight: bold;")
            self._lbl_market_state.setText(market_state)
            self._lbl_strategy_count.setText(str(strategy_count))
            is_live = mode == "live"
            self._btn_mode.setChecked(is_live)
            self._btn_mode.setText("실전투자" if is_live else "모의투자")

    def append_log(self, text: str) -> None:
        """Append a timestamped log line. Trims to 500 lines max."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {text}"
        self._log_lines.append(line)

        # Trim oldest lines if exceeding max
        if len(self._log_lines) > _MAX_LOG_LINES:
            self._log_lines = self._log_lines[-_MAX_LOG_LINES:]

        if _HAS_PYQT5:
            self._log_panel.append(line)
            # Auto-scroll to bottom
            cursor = self._log_panel.textCursor()
            cursor.movePosition(QTextCursor.End)
            self._log_panel.setTextCursor(cursor)

            # Trim visual log panel if needed
            if self._log_panel.document().blockCount() > _MAX_LOG_LINES:
                cursor = self._log_panel.textCursor()
                cursor.movePosition(QTextCursor.Start)
                cursor.movePosition(
                    QTextCursor.Down, QTextCursor.KeepAnchor,
                    self._log_panel.document().blockCount() - _MAX_LOG_LINES,
                )
                cursor.removeSelectedText()
                cursor.deleteChar()  # Remove trailing newline
