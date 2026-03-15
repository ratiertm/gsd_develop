"""Kiwoom OpenAPI+ QAxWidget COM wrapper.

ALL COM calls happen on the main thread where the OCX was instantiated
(STA COM model). This class wraps dynamicCall for type safety and logging.

Note: Cannot be unit-tested without Windows + Kiwoom OpenAPI+ installed.
Use mock_kiwoom_api fixture from conftest.py for dependent module tests.
"""

from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import pyqtSignal, QObject

from loguru import logger


class KiwoomAPI(QObject):
    """Kiwoom OCX wrapper. ALL COM calls happen on the main thread."""

    # Signals for cross-component communication
    connected = pyqtSignal(int)  # err_code from OnEventConnect
    disconnected = pyqtSignal()
    tr_data_received = pyqtSignal(
        str, str, str, str, str, int, str, str, str
    )  # screen_no, rq_name, tr_code, record_name, prev_next, data_len, err_code, msg1, msg2
    real_data_received = pyqtSignal(str, str, str)  # code, real_type, real_data
    chejan_data_received = pyqtSignal(str, int, str)  # gubun, item_cnt, fid_list

    def __init__(self):
        super().__init__()
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")

        # Verify OCX control loaded successfully
        ctrl = self.ocx.control()
        if not ctrl:
            logger.error(
                "OCX control failed to load. "
                "Check: 1) OpenAPI+ installed? 2) 32-bit Python? 3) Run as admin?"
            )
            raise RuntimeError(
                "KHOPENAPI.KHOpenAPICtrl.1 로드 실패. "
                "OpenAPI+ 설치 여부, 32비트 Python 여부를 확인하세요."
            )
        logger.info(f"OCX control loaded: {ctrl}")

        self._connect_events()
        logger.info("KiwoomAPI initialized")

    def _connect_events(self):
        """Connect OCX COM events to internal signal emitters."""
        self.ocx.OnEventConnect.connect(self._on_event_connect)
        self.ocx.OnReceiveTrData.connect(self._on_receive_tr_data)
        self.ocx.OnReceiveRealData.connect(self._on_receive_real_data)
        self.ocx.OnReceiveChejanData.connect(self._on_receive_chejan_data)
        logger.debug("OCX events connected")

    # --- Login ---

    def comm_connect(self):
        """Open Kiwoom login dialog. Result comes via connected signal."""
        logger.debug("CommConnect() called")
        self.ocx.dynamicCall("CommConnect()")

    def get_connect_state(self) -> int:
        """Return connection state: 0=disconnected, 1=connected."""
        state = self.ocx.dynamicCall("GetConnectState()")
        logger.debug(f"GetConnectState() -> {state}")
        return state

    # --- Login Info ---

    def get_login_info(self, tag: str) -> str:
        """Get login information after successful connection.

        Args:
            tag: One of "ACCNO", "USER_ID", "USER_NAME", "KEY_BSECGB"
                 (0: 모의투자, 1: 실거래), "FIESSION_COUNT", etc.

        Returns:
            Requested info as stripped string.
        """
        ret = self.ocx.dynamicCall("GetLoginInfo(QString)", tag)
        result = ret.strip() if ret else ""
        logger.debug(f"GetLoginInfo({tag}) -> {result}")
        return result

    # --- TR Request ---

    def set_input_value(self, id: str, value: str):
        """Set input value for the next TR request."""
        logger.debug(f"SetInputValue({id}, {value})")
        self.ocx.dynamicCall("SetInputValue(QString, QString)", id, value)

    def comm_rq_data(
        self, rq_name: str, tr_code: str, prev_next: int, screen_no: str
    ) -> int:
        """Submit a TR data request. Returns 0 on success."""
        logger.debug(f"CommRqData({rq_name}, {tr_code}, {prev_next}, {screen_no})")
        return self.ocx.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            rq_name,
            tr_code,
            prev_next,
            screen_no,
        )

    def get_repeat_cnt(self, tr_code: str, record_name: str) -> int:
        """Get the number of data rows in a multi-row TR response."""
        ret = self.ocx.dynamicCall(
            "GetRepeatCnt(QString, QString)", tr_code, record_name
        )
        return int(ret)

    def get_comm_data(
        self, tr_code: str, record_name: str, index: int, item_name: str
    ) -> str:
        """Get data from a TR response. Always returns stripped string."""
        ret = self.ocx.dynamicCall(
            "GetCommData(QString, QString, int, QString)",
            tr_code,
            record_name,
            index,
            item_name,
        )
        return ret.strip()

    # --- Order ---

    def send_order(
        self,
        rq_name: str,
        screen_no: str,
        account_no: str,
        order_type: int,
        code: str,
        qty: int,
        price: int,
        hoga_gb: str,
        org_order_no: str,
    ) -> int:
        """Submit an order via SendOrder. Returns 0 on acceptance, negative on error."""
        logger.info(
            f"SendOrder({rq_name}, {screen_no}, {account_no}, "
            f"order_type={order_type}, code={code}, qty={qty}, "
            f"price={price}, hoga_gb={hoga_gb}, org_order_no={org_order_no})"
        )
        ret = self.ocx.dynamicCall(
            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
            rq_name,
            screen_no,
            account_no,
            order_type,
            code,
            qty,
            price,
            hoga_gb,
            org_order_no,
        )
        if ret != 0:
            logger.error(f"SendOrder failed: ret={ret}")
        else:
            logger.info(f"SendOrder accepted: ret={ret}")
        return ret

    def get_chejan_data(self, fid: int) -> str:
        """Get chejan (order/execution) data for a FID. Returns stripped string."""
        ret = self.ocx.dynamicCall("GetChejanData(int)", fid)
        return ret.strip()

    # --- Real-time ---

    def set_real_reg(
        self, screen_no: str, code_list: str, fid_list: str, real_type: str
    ):
        """Register for real-time data.

        Args:
            screen_no: 4-digit screen number string
            code_list: Semicolon-separated stock codes
            fid_list: Semicolon-separated FID numbers
            real_type: "0" = replace existing, "1" = add to existing
        """
        logger.debug(
            f"SetRealReg({screen_no}, {code_list}, {fid_list}, {real_type})"
        )
        self.ocx.dynamicCall(
            "SetRealReg(QString, QString, QString, QString)",
            screen_no,
            code_list,
            fid_list,
            real_type,
        )

    def get_comm_real_data(self, code: str, fid: int) -> str:
        """Get real-time data for a FID. Must be called within OnReceiveRealData context.

        Always returns stripped string.
        """
        ret = self.ocx.dynamicCall("GetCommRealData(QString, int)", code, fid)
        return ret.strip()

    def set_real_remove(self, screen_no: str, code: str):
        """Remove real-time data registration for a stock code on a screen."""
        logger.debug(f"SetRealRemove({screen_no}, {code})")
        self.ocx.dynamicCall(
            "SetRealRemove(QString, QString)", screen_no, code
        )

    # --- OCX Event Handlers (emit signals) ---

    def _on_event_connect(self, err_code: int):
        """Handle OnEventConnect COM event."""
        if err_code == 0:
            logger.info("OnEventConnect: Login successful")
        else:
            logger.error(f"OnEventConnect: Login failed (err_code={err_code})")
        self.connected.emit(err_code)

    def _on_receive_tr_data(
        self,
        screen_no,
        rq_name,
        tr_code,
        record_name,
        prev_next,
        data_len,
        err_code,
        msg1,
        msg2,
    ):
        """Handle OnReceiveTrData COM event."""
        logger.debug(f"OnReceiveTrData: rq_name={rq_name}, tr_code={tr_code}")
        self.tr_data_received.emit(
            screen_no,
            rq_name,
            tr_code,
            record_name,
            prev_next,
            int(data_len),
            err_code,
            msg1,
            msg2,
        )

    def _on_receive_real_data(self, code, real_type, real_data):
        """Handle OnReceiveRealData COM event."""
        logger.debug(f"OnReceiveRealData: code={code}, real_type={real_type}")
        self.real_data_received.emit(code, real_type, real_data)

    def _on_receive_chejan_data(self, gubun, item_cnt, fid_list):
        """Handle OnReceiveChejanData COM event."""
        logger.debug(
            f"OnReceiveChejanData: gubun={gubun}, item_cnt={item_cnt}"
        )
        self.chejan_data_received.emit(str(gubun), int(item_cnt), str(fid_list))
