"""Dashboard tab: real-time positions, orders, P&L, system status, and log panel."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QFont, QTextCursor
    from PyQt5.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QInputDialog,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMessageBox,
        QPushButton,
        QSpinBox,
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


class CopyableTable(QTableWidget if _HAS_PYQT5 else object):
    """QTableWidget with Ctrl+C to copy entire grid as tab-separated text."""

    def keyPressEvent(self, event):
        if _HAS_PYQT5 and event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self._copy_all()
        else:
            super().keyPressEvent(event)

    def _copy_all(self):
        """Copy entire table (headers + all rows) to clipboard."""
        from PyQt5.QtWidgets import QApplication
        lines = []
        # Headers
        headers = []
        for c in range(self.columnCount()):
            h = self.horizontalHeaderItem(c)
            headers.append(h.text() if h else "")
        lines.append("\t".join(headers))
        # Rows
        for r in range(self.rowCount()):
            row = []
            for c in range(self.columnCount()):
                item = self.item(r, c)
                row.append(item.text() if item else "")
            lines.append("\t".join(row))
        QApplication.clipboard().setText("\n".join(lines))


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
        """Professional trading dashboard — 4-tier layout."""
        from PyQt5.QtCore import QDate
        from PyQt5.QtWidgets import QFrame

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ══════════════════════════════════════════════════════════
        # TIER 1: P&L BAR (96px 고정, 항상 보임)
        # ══════════════════════════════════════════════════════════
        tier1 = QWidget()
        tier1.setObjectName("tier1_pnl_bar")
        tier1.setMinimumHeight(96)
        tier1.setMaximumHeight(96)
        t1 = QHBoxLayout(tier1)
        t1.setSpacing(20)
        t1.setContentsMargins(16, 8, 16, 8)

        # Daily P&L
        d_box = QVBoxLayout()
        d_lbl = QLabel("일일손익")
        d_lbl.setStyleSheet("color:#999; font-size:10pt;")
        self._lbl_daily_pnl = QLabel("0")
        self._lbl_daily_pnl.setFont(QFont("Courier New", 16, QFont.Bold))
        self._lbl_daily_pnl.setAlignment(Qt.AlignCenter)
        d_box.addWidget(d_lbl)
        d_box.addWidget(self._lbl_daily_pnl)
        t1.addLayout(d_box, stretch=1)

        # Unrealized
        u_box = QVBoxLayout()
        u_lbl = QLabel("평가손익")
        u_lbl.setStyleSheet("color:#999; font-size:10pt;")
        self._lbl_unrealized_pnl = QLabel("0")
        self._lbl_unrealized_pnl.setFont(QFont("Courier New", 14, QFont.Bold))
        self._lbl_unrealized_pnl.setAlignment(Qt.AlignCenter)
        u_box.addWidget(u_lbl)
        u_box.addWidget(self._lbl_unrealized_pnl)
        t1.addLayout(u_box, stretch=1)

        # Invested
        i_box = QVBoxLayout()
        i_lbl = QLabel("투자금")
        i_lbl.setStyleSheet("color:#999; font-size:10pt;")
        self._lbl_total_invested = QLabel("0")
        self._lbl_total_invested.setFont(QFont("Courier New", 12, QFont.Bold))
        self._lbl_total_invested.setAlignment(Qt.AlignCenter)
        i_box.addWidget(i_lbl)
        i_box.addWidget(self._lbl_total_invested)
        t1.addLayout(i_box, stretch=1)

        # Status: 연결 | 장 | 전략 | 모드
        s_box = QHBoxLayout()
        s_box.setSpacing(12)
        self._lbl_connected = QLabel("--")
        self._lbl_connected.setFont(QFont("", 11, QFont.Bold))
        self._lbl_market_state = QLabel("--")
        self._lbl_strategy_count = QLabel("--")
        self._lbl_user_name = QLabel("--")
        self._lbl_user_name.setStyleSheet("color:#999;")
        self._cmb_account = QComboBox()
        self._cmb_account.setMaximumWidth(120)
        self._btn_mode = QPushButton("모의투자")
        self._btn_mode.setCheckable(True)
        self._btn_mode.setFixedWidth(80)
        self._btn_mode.setStyleSheet(
            "QPushButton{background:#4CAF50;color:white;font-weight:bold;padding:4px;border-radius:3px}"
            "QPushButton:checked{background:#EF5350}"
        )
        self._btn_mode.clicked.connect(self._on_mode_toggle)
        self._on_mode_change = None
        s_box.addWidget(self._lbl_connected)
        s_box.addWidget(self._lbl_market_state)
        s_box.addWidget(self._lbl_strategy_count)
        s_box.addWidget(self._cmb_account)
        s_box.addWidget(self._btn_mode)
        t1.addLayout(s_box, stretch=2)

        main_layout.addWidget(tier1)

        # ══════════════════════════════════════════════════════════
        # TIER 2: MAIN AREA (Watchlist | Positions 가로 스플리터)
        # ══════════════════════════════════════════════════════════
        tier2_splitter = QSplitter(Qt.Vertical)

        # --- Watchlist(35%) | Positions(65%) ---
        wl_pos_splitter = QSplitter(Qt.Horizontal)

        # LEFT: Watchlist
        wl_widget = QWidget()
        wl_layout = QVBoxLayout(wl_widget)
        wl_layout.setSpacing(4)
        wl_layout.setContentsMargins(4, 4, 4, 4)

        wl_hdr = QHBoxLayout()
        wl_title = QLabel("Watchlist")
        wl_title.setFont(QFont("", 11, QFont.Bold))
        wl_hdr.addWidget(wl_title)
        wl_hdr.addStretch()
        btn_add = QPushButton("추가")
        btn_add.setFixedSize(50, 22)
        btn_add.clicked.connect(self._on_add_stock)
        btn_del = QPushButton("제거")
        btn_del.setFixedSize(50, 22)
        btn_del.clicked.connect(self._on_remove_stock)
        wl_hdr.addWidget(btn_add)
        wl_hdr.addWidget(btn_del)
        wl_layout.addLayout(wl_hdr)

        self._watchlist_table = CopyableTable()
        self._watchlist_table.setColumnCount(3)
        self._watchlist_table.setHorizontalHeaderLabels(["종목코드", "종목명", "적용전략(가중치)"])
        self._watchlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._watchlist_table.verticalHeader().setDefaultSectionSize(26)
        self._watchlist_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._watchlist_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._watchlist_table.cellDoubleClicked.connect(self._on_watchlist_double_click)
        wl_layout.addWidget(self._watchlist_table, stretch=1)
        wl_widget.setMinimumWidth(250)
        self._on_strategy_reload = None

        # RIGHT: Positions
        pos_widget = QWidget()
        pos_layout = QVBoxLayout(pos_widget)
        pos_layout.setSpacing(4)
        pos_layout.setContentsMargins(4, 4, 4, 4)

        pos_title = QLabel("포지션")
        pos_title.setFont(QFont("", 11, QFont.Bold))
        pos_layout.addWidget(pos_title)

        self._positions_table = CopyableTable()
        self._positions_table.setColumnCount(len(self.POSITION_COLUMNS))
        self._positions_table.setHorizontalHeaderLabels(self.POSITION_COLUMNS)
        self._positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._positions_table.verticalHeader().setDefaultSectionSize(26)
        self._positions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._positions_table.setAlternatingRowColors(True)
        self._positions_table.setFont(QFont("Courier New", 11))
        pos_layout.addWidget(self._positions_table, stretch=1)
        pos_widget.setMinimumWidth(400)

        wl_pos_splitter.addWidget(wl_widget)
        wl_pos_splitter.addWidget(pos_widget)
        wl_pos_splitter.setStretchFactor(0, 3)
        wl_pos_splitter.setStretchFactor(1, 6)
        tier2_splitter.addWidget(wl_pos_splitter)

        # --- Orders/시뮬 탭 (4탭: 대기주문, 시뮬거래, 체결내역, 시뮬설정) ---
        orders_tabs = QTabWidget()
        orders_tabs.setMinimumHeight(140)

        self._pending_table = CopyableTable()
        self._pending_table.setColumnCount(len(self.ORDER_COLUMNS))
        self._pending_table.setHorizontalHeaderLabels(self.ORDER_COLUMNS)
        self._pending_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._pending_table.verticalHeader().setDefaultSectionSize(26)
        self._pending_table.setEditTriggers(QTableWidget.NoEditTriggers)
        orders_tabs.addTab(self._pending_table, "대기주문")

        self._TRADE_LOG_COLUMNS = ["시간", "종목", "매매", "전략", "가격", "수량", "손익", "잔고"]
        self._trade_log_table = CopyableTable()
        self._trade_log_table.setColumnCount(len(self._TRADE_LOG_COLUMNS))
        self._trade_log_table.setHorizontalHeaderLabels(self._TRADE_LOG_COLUMNS)
        self._trade_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._trade_log_table.verticalHeader().setDefaultSectionSize(26)
        self._trade_log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        orders_tabs.addTab(self._trade_log_table, "시뮬거래")

        self._filled_table = CopyableTable()
        self._filled_table.setColumnCount(len(self.ORDER_COLUMNS))
        self._filled_table.setHorizontalHeaderLabels(self.ORDER_COLUMNS)
        self._filled_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._filled_table.verticalHeader().setDefaultSectionSize(26)
        self._filled_table.setEditTriggers(QTableWidget.NoEditTriggers)
        orders_tabs.addTab(self._filled_table, "체결내역")

        # Tab 4: 시뮬설정 + 수동주문 (인라인)
        sim_tab = QWidget()
        sim_h = QHBoxLayout(sim_tab)
        sim_h.setSpacing(12)
        sim_h.setContentsMargins(8, 6, 8, 6)

        # 시뮬 파라미터
        sf = QFormLayout()
        sf.setSpacing(4)
        self._sim_date_edit = QDateEdit()
        self._sim_date_edit.setCalendarPopup(True)
        self._sim_date_edit.setDate(QDate.currentDate().addDays(-1))
        self._sim_date_edit.setDisplayFormat("yyyy-MM-dd")
        self._sim_interval_combo = QComboBox()
        self._sim_interval_combo.addItems(["1분", "3분", "5분", "10분"])
        self._sim_interval_combo.setCurrentIndex(1)
        self._sim_speed_combo = QComboBox()
        self._sim_speed_combo.addItems(["최대속도", "빠르게", "보통(1봉/초)", "천천히(1봉/3초)"])
        self._sim_speed_combo.setCurrentIndex(2)
        self._sim_day_strategy_combo = QComboBox()
        self._sim_day_strategy_combo.addItems([
            "기본전략(config)", "ORB", "VWAP_BOUNCE", "PREV_DAY_BRK",
            "GAP_TRADE", "ORDER_FLOW", "전체(ALL)",
        ])
        sf.addRow("날짜:", self._sim_date_edit)
        sf.addRow("전략:", self._sim_day_strategy_combo)
        sf.addRow("봉:", self._sim_interval_combo)
        sf.addRow("속도:", self._sim_speed_combo)
        sf_w = QWidget()
        sf_w.setLayout(sf)
        sim_h.addWidget(sf_w, stretch=2)

        self._btn_sim_start = QPushButton("시뮬\n시작")
        self._btn_sim_start.setStyleSheet(
            "QPushButton{background:#FF9800;color:white;font-weight:bold;padding:8px;border-radius:4px;font-size:10pt}"
        )
        self._btn_sim_start.setFixedSize(60, 60)
        self._btn_sim_start.clicked.connect(self._on_sim_start)
        self._on_sim_requested = None
        sim_h.addWidget(self._btn_sim_start)

        # 구분선
        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setStyleSheet("color:#444;")
        sim_h.addWidget(div)

        # 수동주문
        of = QFormLayout()
        of.setSpacing(4)
        self._order_code_edit = QComboBox()
        self._order_code_edit.setEditable(True)
        self._order_code_edit.setPlaceholderText("종목코드")
        self._order_qty_spin = QSpinBox()
        self._order_qty_spin.setRange(1, 9999)
        self._order_qty_spin.setValue(1)
        self._order_qty_spin.setMaximumWidth(80)
        self._order_price_spin = QSpinBox()
        self._order_price_spin.setRange(0, 99999999)
        self._order_price_spin.setSingleStep(100)
        self._order_price_spin.setSpecialValueText("시장가")
        self._order_price_spin.setMaximumWidth(100)
        of.addRow("종목:", self._order_code_edit)
        of.addRow("수량:", self._order_qty_spin)
        of.addRow("가격:", self._order_price_spin)
        of_w = QWidget()
        of_w.setLayout(of)
        sim_h.addWidget(of_w, stretch=2)

        btn_col = QVBoxLayout()
        self._btn_buy = QPushButton("매수")
        self._btn_buy.setStyleSheet(
            "QPushButton{background:#EF5350;color:white;font-weight:bold;padding:6px;border-radius:4px;font-size:10pt}"
        )
        self._btn_buy.setFixedSize(60, 30)
        self._btn_buy.clicked.connect(lambda: self._on_manual_order("BUY"))
        self._btn_sell = QPushButton("매도")
        self._btn_sell.setStyleSheet(
            "QPushButton{background:#42A5F5;color:white;font-weight:bold;padding:6px;border-radius:4px;font-size:10pt}"
        )
        self._btn_sell.setFixedSize(60, 30)
        self._btn_sell.clicked.connect(lambda: self._on_manual_order("SELL"))
        btn_col.addWidget(self._btn_buy)
        btn_col.addWidget(self._btn_sell)
        sim_h.addLayout(btn_col)
        self._on_order_requested = None

        orders_tabs.addTab(sim_tab, "시뮬설정")

        tier2_splitter.addWidget(orders_tabs)
        tier2_splitter.setStretchFactor(0, 6)
        tier2_splitter.setStretchFactor(1, 3)

        main_layout.addWidget(tier2_splitter, stretch=6)

        # ══════════════════════════════════════════════════════════
        # TIER 3: LOG (최대 150px)
        # ══════════════════════════════════════════════════════════
        self._log_panel = QTextEdit()
        self._log_panel.setReadOnly(True)
        self._log_panel.setFont(QFont("Courier New", 9))
        self._log_panel.setMinimumHeight(60)
        self._log_panel.setMaximumHeight(150)
        main_layout.addWidget(self._log_panel, stretch=1)

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

        self._apply_mode_theme(new_mode)
        if self._on_mode_change:
            self._on_mode_change(new_mode)

    def _apply_mode_theme(self, mode: str) -> None:
        """Change UI appearance based on trading mode."""
        if not _HAS_PYQT5:
            return
        # Find TIER1 (P&L bar) — it's the first child widget
        tier1 = self.findChild(QWidget, "tier1_pnl_bar")
        main_window = self.window()

        if mode == "live":
            # LIVE: red accent on TIER1, window title warning
            if tier1:
                tier1.setStyleSheet(
                    "QWidget#tier1_pnl_bar { background-color: #3A1515; "
                    "border-bottom: 3px solid #EF5350; }"
                )
            if main_window:
                main_window.setWindowTitle("KiwoomDayTrader [실전투자]")
                main_window.statusBar().setStyleSheet(
                    "QStatusBar { background-color: #3A1515; color: #EF5350; "
                    "border-top: 2px solid #EF5350; font-weight: bold; }"
                )
        else:
            # PAPER/REPLAY: normal dark theme
            if tier1:
                tier1.setStyleSheet("")
            if main_window:
                title = "KiwoomDayTrader"
                if hasattr(self, "_settings") and self._settings:
                    m = self._settings._config.get("mode", "paper")
                    if m == "paper":
                        title += " [모의투자]"
                main_window.setWindowTitle(title)
                main_window.statusBar().setStyleSheet("")

        # Enable/disable panels based on mode
        is_live = mode == "live"
        # 수동주문: 실거래만
        self._btn_buy.setEnabled(is_live)
        self._btn_sell.setEnabled(is_live)
        self._order_code_edit.setEnabled(is_live)
        self._order_qty_spin.setEnabled(is_live)
        self._order_price_spin.setEnabled(is_live)
        # 시뮬: 실거래 아닐 때만
        self._sim_date_edit.setEnabled(not is_live)
        self._sim_interval_combo.setEnabled(not is_live)
        self._sim_speed_combo.setEnabled(not is_live)
        self._btn_sim_start.setEnabled(not is_live)

    def _on_sim_start(self) -> None:
        """Handle simulation start button click."""
        if not self._sim_date_edit:
            return
        date_str = self._sim_date_edit.date().toString("yyyyMMdd")

        interval_map = {"1분": 1, "3분": 3, "5분": 5, "10분": 10}
        interval = interval_map.get(self._sim_interval_combo.currentText(), 3)

        # Speed = ticks per second (higher = faster)
        # 1분봉 = ~600틱, so 10000 tps → ~1봉/0.06초, 600 → 1봉/초, 200 → 1봉/3초
        speed_map = {"최대 속도": 0, "빠르게": 50000, "보통 (1봉/초)": 600, "천천히 (1봉/3초)": 200}
        speed = speed_map.get(self._sim_speed_combo.currentText(), 600)

        # Clear previous simulation data
        self._trade_log_table.setRowCount(0)
        self._positions_table.setRowCount(0)
        self._lbl_daily_pnl.setText("0")
        self._lbl_daily_pnl.setStyleSheet("")

        # Day strategy selection
        day_strat_text = self._sim_day_strategy_combo.currentText()
        day_strat_map = {
            "기본전략(config)": None,
            "ORB": "ORB", "VWAP_BOUNCE": "VWAP_BOUNCE",
            "PREV_DAY_BRK": "PREV_DAY_BRK", "GAP_TRADE": "GAP_TRADE",
            "ORDER_FLOW": "ORDER_FLOW", "전체(ALL)": "ALL",
        }
        day_strategy = day_strat_map.get(day_strat_text)

        if self._on_sim_requested:
            self._on_sim_requested(date_str, interval, speed, day_strategy)
        else:
            QMessageBox.warning(self, "시뮬레이션", "시뮬레이션 엔진이 연결되지 않았습니다.")

    # Two-step order confirmation state
    _order_confirm_state: str | None = None

    def _on_manual_order(self, side: str) -> None:
        """Two-step order confirmation. First click → warning state, second click → execute."""
        from PyQt5.QtCore import QTimer

        code = self._order_code_edit.currentText().strip()
        if not code:
            QMessageBox.warning(self, "주문 오류", "종목코드를 입력하세요.")
            return

        btn = self._btn_buy if side == "BUY" else self._btn_sell
        expected = f"{side}_CONFIRM"

        if self._order_confirm_state == expected:
            # Step 2: execute
            self._order_confirm_state = None
            btn.setText("매수" if side == "BUY" else "매도")
            self._restore_order_btn_style(btn, side)

            qty = self._order_qty_spin.value() if self._order_qty_spin else 1
            price = self._order_price_spin.value() if self._order_price_spin else 0
            if self._on_order_requested:
                self._on_order_requested(code, side, qty, price)
        else:
            # Step 1: enter confirmation mode
            self._order_confirm_state = expected
            qty = self._order_qty_spin.value() if self._order_qty_spin else 1
            price = self._order_price_spin.value() if self._order_price_spin else 0
            price_str = f"{price:,}" if price > 0 else "시장가"
            btn.setText(f"{code} {qty}주 {price_str} — 다시 클릭")
            btn.setStyleSheet(
                "QPushButton { background-color: #FFC107; color: #000; "
                "font-weight: bold; padding: 8px; border-radius: 4px; font-size: 11pt; }"
            )
            # Auto-reset after 3 seconds
            QTimer.singleShot(3000, lambda: self._reset_order_confirm(btn, side))

    def _reset_order_confirm(self, btn, side: str) -> None:
        """Reset order confirmation state after timeout."""
        if self._order_confirm_state == f"{side}_CONFIRM":
            self._order_confirm_state = None
            btn.setText("매수" if side == "BUY" else "매도")
            self._restore_order_btn_style(btn, side)

    def _restore_order_btn_style(self, btn, side: str) -> None:
        """Restore original button color."""
        if side == "BUY":
            btn.setStyleSheet(
                "QPushButton { background-color: #EF5350; color: white; "
                "font-weight: bold; padding: 6px; border-radius: 4px; }"
            )
        else:
            btn.setStyleSheet(
                "QPushButton { background-color: #42A5F5; color: white; "
                "font-weight: bold; padding: 6px; border-radius: 4px; }"
            )

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

    # Log level color mapping
    _LOG_COLORS = {
        "ERROR": "#F44336",
        "WARNING": "#FF9800",
        "BUY": "#26A69A",
        "SELL": "#EF5350",
    }

    def append_log(self, text: str) -> None:
        """Append a timestamped, color-coded log line."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {text}"
        self._log_lines.append(line)

        if len(self._log_lines) > _MAX_LOG_LINES:
            self._log_lines = self._log_lines[-_MAX_LOG_LINES:]

        if _HAS_PYQT5:
            # Detect color from content
            color = "#E0E0E0"  # default
            for keyword, c in self._LOG_COLORS.items():
                if keyword in text:
                    color = c
                    break
            self._log_panel.append(f'<span style="color:{color}">{line}</span>')
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

    def add_trade_record(self, trade) -> None:
        """Add a TradeRecord to the simulation trade log table."""
        if not _HAS_PYQT5:
            return
        row = self._trade_log_table.rowCount()
        self._trade_log_table.insertRow(row)
        ts = trade.timestamp.strftime("%H:%M:%S") if hasattr(trade.timestamp, "strftime") else str(trade.timestamp)
        values = [
            ts, trade.code, trade.side, trade.strategy,
            _format_price(trade.price), str(trade.qty),
            _format_price(trade.pnl) if trade.pnl else "",
            _format_price(trade.balance),
        ]
        for c, text in enumerate(values):
            item = QTableWidgetItem(text)
            if trade.side == "SELL" and c == 6 and trade.pnl:
                color = pnl_color(trade.pnl)
                if color:
                    item.setForeground(QColor(color))
            self._trade_log_table.setItem(row, c, item)
        self._trade_log_table.scrollToBottom()

    # ------------------------------------------------------------------ #
    # Watchlist management
    # ------------------------------------------------------------------ #

    def _get_strategy_names(self) -> list[str]:
        """Get list of all strategy names from config."""
        if not hasattr(self, "_settings") or self._settings is None:
            return []
        return [s["name"] for s in self._settings._config.get("strategies", [])]

    def _get_strategy_priority(self, name: str) -> int:
        """Get priority for a strategy by name."""
        if not hasattr(self, "_settings") or self._settings is None:
            return 0
        for s in self._settings._config.get("strategies", []):
            if s["name"] == name:
                return s.get("priority", 0)
        return 0

    def _resolve_stock_name(self, code: str) -> str:
        """Get stock name from settings cache."""
        if hasattr(self, "_settings") and hasattr(self._settings, "get_stock_name"):
            return self._settings.get_stock_name(code)
        return ""

    def load_watchlist(self) -> None:
        """Populate watchlist table from config with priority weights."""
        if not _HAS_PYQT5 or not hasattr(self, "_watchlist_table"):
            return
        ws = {}
        if hasattr(self, "_settings") and self._settings:
            ws = self._settings._config.get("watchlist_strategies", {})
        self._watchlist_table.setRowCount(len(ws))
        for row, (code, strats) in enumerate(ws.items()):
            name = self._resolve_stock_name(code)
            # Format: "RSI(10), MA(1), MACD(20)"
            strat_display = ", ".join(
                f"{s}({self._get_strategy_priority(s)})" for s in strats
            )
            self._watchlist_table.setItem(row, 0, QTableWidgetItem(code))
            self._watchlist_table.setItem(row, 1, QTableWidgetItem(name))
            self._watchlist_table.setItem(row, 2, QTableWidgetItem(strat_display))

    def _show_strategy_picker(self, code: str, current: list[str] | None = None) -> list[str] | None:
        """Show dialog to pick strategies and adjust priorities for a stock.

        Returns selected strategy names or None if cancelled.
        Priority changes are saved to config immediately.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(f"전략 선택 — {code}")
        dialog.setMinimumWidth(400)
        dlg_layout = QVBoxLayout(dialog)

        name = self._resolve_stock_name(code)
        dlg_layout.addWidget(QLabel(f"{code} {name}"))

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("전략"), stretch=4)
        header.addWidget(QLabel("가중치"), stretch=2)
        dlg_layout.addLayout(header)

        # Strategy rows with checkbox + priority spinbox
        rows = []
        all_names = self._get_strategy_names()
        current = current or []
        for sname in all_names:
            row_layout = QHBoxLayout()
            cb = QCheckBox(sname)
            cb.setChecked(sname in current)

            spin = QSpinBox()
            spin.setRange(1, 100)
            spin.setValue(self._get_strategy_priority(sname))
            spin.setFixedWidth(60)

            row_layout.addWidget(cb, stretch=4)
            row_layout.addWidget(spin, stretch=2)
            dlg_layout.addLayout(row_layout)
            rows.append((sname, cb, spin))

        btn_row = QHBoxLayout()
        btn_all = QPushButton("전체 선택")
        btn_none = QPushButton("전체 해제")
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for _, cb, _ in rows])
        btn_none.clicked.connect(lambda: [cb.setChecked(False) for _, cb, _ in rows])
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        dlg_layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dlg_layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            # Save priority changes
            if hasattr(self, "_settings") and self._settings:
                for sname, cb, spin in rows:
                    for s in self._settings._config.get("strategies", []):
                        if s["name"] == sname:
                            s["priority"] = spin.value()
                            break
                self._settings.save()
            return [sname for sname, cb, _ in rows if cb.isChecked()]
        return None

    def _on_add_stock(self) -> None:
        """Add stock code with strategy picker."""
        code, ok = QInputDialog.getText(self, "종목 추가", "종목코드:")
        if not ok or not code.strip():
            return
        code = code.strip()
        selected = self._show_strategy_picker(code, self._get_strategy_names())
        if selected is None:
            return
        if hasattr(self, "_settings") and self._settings:
            ws = self._settings._config.setdefault("watchlist_strategies", {})
            ws[code] = selected
            self._settings.save()
            self.load_watchlist()
            if self._on_strategy_reload:
                self._on_strategy_reload()

    def _on_remove_stock(self) -> None:
        """Remove selected stock from watchlist."""
        row = self._watchlist_table.currentRow()
        if row >= 0:
            code_item = self._watchlist_table.item(row, 0)
            if code_item and hasattr(self, "_settings") and self._settings:
                ws = self._settings._config.get("watchlist_strategies", {})
                ws.pop(code_item.text(), None)
                self._settings.save()
                self.load_watchlist()
                if self._on_strategy_reload:
                    self._on_strategy_reload()

    def _on_watchlist_double_click(self, row: int, col: int) -> None:
        """Double-click to edit strategy assignment."""
        code_item = self._watchlist_table.item(row, 0)
        if not code_item or not hasattr(self, "_settings"):
            return
        code = code_item.text()
        ws = self._settings._config.get("watchlist_strategies", {})
        current = ws.get(code, [])
        selected = self._show_strategy_picker(code, current)
        if selected is not None:
            ws[code] = selected
            self._settings.save()
            self.load_watchlist()
            if self._on_strategy_reload:
                self._on_strategy_reload()

    # ------------------------------------------------------------------ #
    # Simulation position/P&L display
    # ------------------------------------------------------------------ #

    def update_sim_positions(self, positions: dict, capital: float, initial: int,
                            last_prices: dict | None = None) -> None:
        """Update positions and P&L from ReplayEngine state.

        Args:
            positions: {code: {"qty": int, "avg_price": int, "highest_price": int}}
            capital: Current cash balance.
            initial: Initial capital.
            last_prices: {code: last_close_price} for unrealized P&L calculation.
        """
        if not _HAS_PYQT5:
            return
        last_prices = last_prices or {}

        # Positions table
        self._positions_table.setRowCount(len(positions))
        total_invested = 0
        total_unrealized = 0
        for r, (code, pos) in enumerate(positions.items()):
            qty = pos.get("qty", 0)
            avg = pos.get("avg_price", 0)
            current = last_prices.get(code, avg)
            invested = avg * qty
            unrealized = (current - avg) * qty
            pnl_pct = (current - avg) / avg * 100 if avg > 0 else 0
            total_invested += invested
            total_unrealized += unrealized

            name = ""
            if hasattr(self, "_settings") and hasattr(self._settings, "get_stock_name"):
                name = self._settings.get_stock_name(code)
            values = [
                code, name, str(qty), _format_price(avg), _format_price(current),
                _format_price(int(unrealized)), f"{pnl_pct:.2f}", "",
            ]
            # Row background: tint red for losing positions
            row_bg = QColor("#2A1515") if unrealized < 0 else QColor("#1F1F1F") if r % 2 == 0 else QColor("#252525")

            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item.setBackground(row_bg)
                if c in (3, 4):  # price columns — bold mono
                    item.setFont(QFont("Courier New", 11, QFont.Bold))
                if c == 5:  # unrealized P&L
                    item.setFont(QFont("Courier New", 11, QFont.Bold))
                    color = pnl_color(unrealized)
                    if color:
                        item.setForeground(QColor(color))
                if c == 6:  # pnl %
                    item.setFont(QFont("Courier New", 11, QFont.Bold))
                    color = pnl_color(pnl_pct)
                    if color:
                        item.setForeground(QColor(color))
                self._positions_table.setItem(r, c, item)

        # P&L summary
        daily_pnl = capital - initial + total_unrealized
        self._lbl_daily_pnl.setText(_format_price(int(daily_pnl)))
        color = pnl_color(daily_pnl)
        self._lbl_daily_pnl.setStyleSheet(
            f"color: {color}; font-weight: bold;" if color else ""
        )
        self._lbl_unrealized_pnl.setText(_format_price(int(total_unrealized)))
        ucolor = pnl_color(total_unrealized)
        self._lbl_unrealized_pnl.setStyleSheet(
            f"color: {ucolor}; font-weight: bold;" if ucolor else ""
        )
        self._lbl_total_invested.setText(_format_price(int(total_invested)))
