"""계좌평가잔고내역(opw00018) TR 조회 및 PositionTracker 동기화.

로그인 직후 호출하여 기존 보유 잔고를 앱에 반영한다.
TRRequestQueue를 통해 3.6초 제한을 준수한다.
"""

from loguru import logger


# opw00018 응답 필드명 (GetCommData item_name)
_FIELDS = {
    "code": "종목번호",
    "name": "종목명",
    "qty": "보유수량",
    "buy_price": "매입가",
    "current_price": "현재가",
    "pnl": "평가손익",
    "pnl_rate": "수익률(%)",
}


class BalanceQuery:
    """opw00018 TR을 통해 계좌 보유 잔고를 조회한다.

    사용법:
        bq = BalanceQuery(api, tr_queue, event_registry)
        bq.query(account_no, on_complete=callback)
    """

    TR_CODE = "opw00018"
    RQ_NAME = "계좌평가잔고내역요청"
    SCREEN_NO = "3000"

    def __init__(self, kiwoom_api, tr_queue, event_registry):
        self._api = kiwoom_api
        self._tr_queue = tr_queue
        self._event_registry = event_registry
        self._on_complete = None
        self._positions = []

    def query(self, account_no: str, on_complete=None):
        """잔고 조회 TR 요청을 큐에 등록한다.

        Args:
            account_no: 계좌번호
            on_complete: 조회 완료 시 호출될 콜백 — callback(positions_list)
                positions_list: [{"code", "name", "qty", "buy_price",
                                  "current_price", "pnl", "pnl_rate"}, ...]
        """
        self._on_complete = on_complete
        self._positions = []

        # Register TR response handler
        self._event_registry.register_tr_handler(
            self.RQ_NAME, self._on_receive
        )

        # Enqueue TR request
        self._tr_queue.enqueue(
            tr_code=self.TR_CODE,
            rq_name=self.RQ_NAME,
            screen_no=self.SCREEN_NO,
            inputs={
                "계좌번호": account_no,
                "비밀번호": "0000",
                "비밀번호입력매체구분": "00",
                "조회구분": "1",
            },
        )
        logger.info(f"잔고 조회 TR 요청: {account_no}")

    def _on_receive(self, screen_no, rq_name, tr_code, record_name,
                    prev_next, data_len, err_code, msg1, msg2):
        """opw00018 TR 응답 처리."""
        count = self._api.get_repeat_cnt(tr_code, record_name)
        logger.info(f"잔고 조회 응답: {count}건")

        for i in range(count):
            raw_code = self._api.get_comm_data(
                tr_code, record_name, i, _FIELDS["code"]
            )
            # Strip leading "A" and spaces
            code = raw_code.replace("A", "").strip()
            if not code:
                continue

            name = self._api.get_comm_data(
                tr_code, record_name, i, _FIELDS["name"]
            ).strip()

            qty = self._parse_int(
                self._api.get_comm_data(
                    tr_code, record_name, i, _FIELDS["qty"]
                )
            )
            buy_price = self._parse_price(
                self._api.get_comm_data(
                    tr_code, record_name, i, _FIELDS["buy_price"]
                )
            )
            current_price = self._parse_price(
                self._api.get_comm_data(
                    tr_code, record_name, i, _FIELDS["current_price"]
                )
            )
            pnl = self._parse_int_signed(
                self._api.get_comm_data(
                    tr_code, record_name, i, _FIELDS["pnl"]
                )
            )
            pnl_rate = self._api.get_comm_data(
                tr_code, record_name, i, _FIELDS["pnl_rate"]
            ).strip()

            if qty > 0:
                pos = {
                    "code": code,
                    "name": name,
                    "qty": qty,
                    "buy_price": buy_price,
                    "current_price": current_price,
                    "pnl": pnl,
                    "pnl_rate": pnl_rate,
                }
                self._positions.append(pos)
                logger.info(
                    f"  보유: {code} {name} | {qty}주 | "
                    f"매입가 {buy_price:,} | 현재가 {current_price:,} | "
                    f"손익 {pnl:,}"
                )

        # Handle pagination (prev_next == "2" means more data)
        if str(prev_next) == "2":
            logger.info("잔고 조회 연속 요청...")
            self._tr_queue.enqueue(
                tr_code=self.TR_CODE,
                rq_name=self.RQ_NAME,
                screen_no=self.SCREEN_NO,
                inputs={
                    "계좌번호": "",
                    "비밀번호": "0000",
                    "비밀번호입력매체구분": "00",
                    "조회구분": "1",
                },
                prev_next=2,
            )
        else:
            logger.info(f"잔고 조회 완료: 총 {len(self._positions)}종목")
            if self._on_complete:
                self._on_complete(self._positions)

    @staticmethod
    def _parse_int(value: str) -> int:
        value = value.strip()
        if not value:
            return 0
        try:
            return abs(int(value))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_price(value: str) -> int:
        value = value.strip()
        if not value:
            return 0
        try:
            return abs(int(value))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_int_signed(value: str) -> int:
        """부호를 유지하는 정수 파싱 (손익 등)."""
        value = value.strip()
        if not value:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
