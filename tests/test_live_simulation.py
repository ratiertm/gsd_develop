"""Phase 7~9 시뮬레이션 테스트: 샘플 데이터로 전체 파이프라인 검증.

실제 키움 API 없이 테스트:
1. 실시간 데이터 수신 → RealDataManager → 구독자 디스패치
2. 주문 제출 → chejan 콜백 → OrderManager 상태 전이
3. 잔고 업데이트 → PositionTracker 동기화
4. opw00018 잔고 조회 → PositionTracker 초기 동기화

실행:
    .venv32\\Scripts\\python.exe -m pytest tests/test_live_simulation.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from kiwoom_trader.config.constants import FID, CHEJAN_FID, HogaGb, ORDER_ERROR
from kiwoom_trader.core.models import (
    OrderSide, OrderState, RiskConfig, Candle,
)
from kiwoom_trader.core.order_manager import OrderManager
from kiwoom_trader.core.position_tracker import PositionTracker
from kiwoom_trader.api.real_data import RealDataManager


# ---------------------------------------------------------------------------
# Sample data: 삼성전자 09:05~09:10 체결 틱 5건
# ---------------------------------------------------------------------------
SAMPLE_TICKS = [
    {FID.CURRENT_PRICE: "+58000", FID.VOLUME: "1234567", FID.EXEC_VOLUME: "500",
     FID.OPEN_PRICE: "+57500", FID.HIGH_PRICE: "+58200", FID.LOW_PRICE: "+57300"},
    {FID.CURRENT_PRICE: "+58100", FID.VOLUME: "1235000", FID.EXEC_VOLUME: "433",
     FID.OPEN_PRICE: "+57500", FID.HIGH_PRICE: "+58200", FID.LOW_PRICE: "+57300"},
    {FID.CURRENT_PRICE: "-57900", FID.VOLUME: "1236200", FID.EXEC_VOLUME: "1200",
     FID.OPEN_PRICE: "+57500", FID.HIGH_PRICE: "+58200", FID.LOW_PRICE: "+57300"},
    {FID.CURRENT_PRICE: "+58300", FID.VOLUME: "1238000", FID.EXEC_VOLUME: "1800",
     FID.OPEN_PRICE: "+57500", FID.HIGH_PRICE: "+58300", FID.LOW_PRICE: "+57300"},
    {FID.CURRENT_PRICE: "+58500", FID.VOLUME: "1240000", FID.EXEC_VOLUME: "2000",
     FID.OPEN_PRICE: "+57500", FID.HIGH_PRICE: "+58500", FID.LOW_PRICE: "+57300"},
]


def _make_mock_api():
    """Create a mock KiwoomAPI that returns sample data for get_comm_real_data."""
    api = MagicMock()
    api.send_order.return_value = ORDER_ERROR.SUCCESS
    api.get_connect_state.return_value = 1
    # connected signal mock
    api.connected = MagicMock()
    api.tr_data_received = MagicMock()
    api.real_data_received = MagicMock()
    api.chejan_data_received = MagicMock()
    return api


# ===========================================================================
# Test 1: 실시간 데이터 수신 → RealDataManager 디스패치
# ===========================================================================
class TestRealDataReception:
    """Phase 7: 샘플 틱 데이터가 RealDataManager를 통해 구독자에게 전달되는지 검증."""

    def test_tick_data_dispatched_to_subscriber(self):
        """구독자에게 파싱된 FID dict가 전달된다."""
        api = _make_mock_api()
        rdm = RealDataManager(api)

        received = []
        rdm.register_subscriber("주식체결", lambda code, data: received.append((code, data)))

        # Simulate: OnReceiveRealData → on_real_data
        # Mock get_comm_real_data to return sample values
        tick = SAMPLE_TICKS[0]
        api.get_comm_real_data.side_effect = lambda code, fid: tick.get(fid, "")

        rdm.on_real_data("005930", "주식체결", "raw_data_unused")

        assert len(received) == 1
        code, data = received[0]
        assert code == "005930"
        assert data[FID.CURRENT_PRICE] == "+58000"
        assert data[FID.VOLUME] == "1234567"

    def test_multiple_ticks_dispatched(self):
        """5개 틱이 모두 전달된다."""
        api = _make_mock_api()
        rdm = RealDataManager(api)

        received = []
        rdm.register_subscriber("주식체결", lambda code, data: received.append(data))

        for tick in SAMPLE_TICKS:
            api.get_comm_real_data.side_effect = lambda code, fid, t=tick: t.get(fid, "")
            rdm.on_real_data("005930", "주식체결", "")

        assert len(received) == 5
        # Last tick price should be 58500
        assert received[-1][FID.CURRENT_PRICE] == "+58500"

    def test_first_reception_logged(self):
        """첫 수신 시 로그가 남는다 (두 번째부터는 안 남음)."""
        api = _make_mock_api()
        rdm = RealDataManager(api)
        rdm.register_subscriber("주식체결", lambda code, data: None)

        tick = SAMPLE_TICKS[0]
        api.get_comm_real_data.side_effect = lambda code, fid: tick.get(fid, "")

        # First call should set _seen_codes
        rdm.on_real_data("005930", "주식체결", "")
        assert "005930" in rdm._seen_codes

        # Second call should not add again
        rdm.on_real_data("005930", "주식체결", "")
        assert len(rdm._seen_codes) == 1

    def test_unsubscribed_type_ignored(self):
        """등록하지 않은 real_type은 무시된다."""
        api = _make_mock_api()
        rdm = RealDataManager(api)

        received = []
        rdm.register_subscriber("주식체결", lambda code, data: received.append(data))

        tick = SAMPLE_TICKS[0]
        api.get_comm_real_data.side_effect = lambda code, fid: tick.get(fid, "")
        rdm.on_real_data("005930", "주식호가", "")  # 다른 타입

        assert len(received) == 0


# ===========================================================================
# Test 2: 주문 제출 → chejan → OrderManager 상태 전이
# ===========================================================================
class TestOrderLifecycle:
    """Phase 8: 주문 제출 → chejan 콜백으로 상태 전이 검증."""

    def _make_om(self):
        api = _make_mock_api()
        om = OrderManager(api, "7033652731")
        return api, om

    def test_submit_order_success(self):
        """시장가 매수 주문 제출 → SUBMITTED 상태."""
        api, om = self._make_om()

        order = om.submit_order(
            code="005930", side=OrderSide.BUY,
            qty=1, price=0, hoga_gb=HogaGb.MARKET,
        )

        assert order.state == OrderState.SUBMITTED
        assert order.code == "005930"
        assert order.qty == 1
        api.send_order.assert_called_once()

    def test_submit_order_failure(self):
        """SendOrder 실패 → REJECTED 상태."""
        api, om = self._make_om()
        api.send_order.return_value = -308  # 주문전송 과부하

        order = om.submit_order(
            code="005930", side=OrderSide.BUY,
            qty=1, price=0, hoga_gb=HogaGb.MARKET,
        )

        assert order.state == OrderState.REJECTED

    def test_chejan_maps_real_order_no(self):
        """chejan 수신 시 임시 주문번호 → 실제 주문번호 매핑."""
        api, om = self._make_om()

        order = om.submit_order(
            code="005930", side=OrderSide.BUY,
            qty=1, price=0, hoga_gb=HogaGb.MARKET,
        )
        temp_id = order.order_no
        assert temp_id.startswith("ORD_")

        # Simulate chejan gubun=0 (주문접수)
        real_order_no = "0012345"
        chejan_data = {
            CHEJAN_FID.ORDER_NO: real_order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "접수",
            CHEJAN_FID.UNFILLED_QTY: "1",
            CHEJAN_FID.EXEC_PRICE: "",
            CHEJAN_FID.EXEC_QTY: "0",
        }
        api.get_chejan_data.side_effect = lambda fid: chejan_data.get(fid, "")

        om.handle_chejan_data("0", 6, "9203;9001;913;902;910;911")

        # Order should now be mapped to real order_no
        assert real_order_no in om._orders
        assert temp_id not in om._pending_orders
        assert om._orders[real_order_no].state == OrderState.ACCEPTED

    def test_chejan_full_fill(self):
        """접수 → 체결 전체 사이클."""
        api, om = self._make_om()

        order = om.submit_order(
            code="005930", side=OrderSide.BUY,
            qty=1, price=0, hoga_gb=HogaGb.MARKET,
        )

        filled_events = []
        om.order_filled.connect(
            lambda no, code, qty, price: filled_events.append((no, code, qty, price))
        )

        real_order_no = "0012345"

        # Step 1: 접수
        chejan_accept = {
            CHEJAN_FID.ORDER_NO: real_order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "접수",
            CHEJAN_FID.UNFILLED_QTY: "1",
            CHEJAN_FID.EXEC_PRICE: "",
            CHEJAN_FID.EXEC_QTY: "0",
        }
        api.get_chejan_data.side_effect = lambda fid: chejan_accept.get(fid, "")
        om.handle_chejan_data("0", 6, "")

        assert om._orders[real_order_no].state == OrderState.ACCEPTED

        # Step 2: 체결
        chejan_fill = {
            CHEJAN_FID.ORDER_NO: real_order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "체결",
            CHEJAN_FID.UNFILLED_QTY: "0",
            CHEJAN_FID.EXEC_PRICE: "+58000",
            CHEJAN_FID.EXEC_QTY: "1",
        }
        api.get_chejan_data.side_effect = lambda fid: chejan_fill.get(fid, "")
        om.handle_chejan_data("0", 6, "")

        assert om._orders[real_order_no].state == OrderState.FILLED
        assert om._orders[real_order_no].filled_qty == 1
        assert om._orders[real_order_no].filled_price == 58000
        assert len(filled_events) == 1

    def test_chejan_cancel(self):
        """접수 → 취소 사이클."""
        api, om = self._make_om()
        order = om.submit_order(
            code="005930", side=OrderSide.BUY,
            qty=1, price=58000, hoga_gb=HogaGb.LIMIT,
        )

        real_order_no = "0012346"

        # 접수
        api.get_chejan_data.side_effect = lambda fid: {
            CHEJAN_FID.ORDER_NO: real_order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "접수",
            CHEJAN_FID.UNFILLED_QTY: "1",
            CHEJAN_FID.EXEC_PRICE: "",
            CHEJAN_FID.EXEC_QTY: "0",
        }.get(fid, "")
        om.handle_chejan_data("0", 6, "")

        # 취소
        api.get_chejan_data.side_effect = lambda fid: {
            CHEJAN_FID.ORDER_NO: real_order_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "취소확인",
            CHEJAN_FID.UNFILLED_QTY: "1",
            CHEJAN_FID.EXEC_PRICE: "",
            CHEJAN_FID.EXEC_QTY: "0",
        }.get(fid, "")
        om.handle_chejan_data("0", 6, "")

        assert om._orders[real_order_no].state == OrderState.CANCELLED


# ===========================================================================
# Test 3: 잔고 업데이트 → PositionTracker 동기화
# ===========================================================================
class TestBalanceSync:
    """Phase 9 준비: chejan 잔고 통보 → PositionTracker 동기화."""

    def test_chejan_balance_creates_position(self):
        """gubun=1 잔고 통보로 PositionTracker에 포지션이 생성된다."""
        risk_config = RiskConfig()
        pt = PositionTracker(risk_config)

        # Simulate chejan balance update
        pt.update_from_chejan(
            code="005930", holding_qty=1,
            buy_price=58000, current_price=58500,
        )

        pos = pt.get_position("005930")
        assert pos is not None
        assert pos.qty == 1
        assert pos.avg_price == 58000
        assert pos.unrealized_pnl == 500  # (58500-58000)*1

    def test_chejan_balance_removes_on_zero(self):
        """보유수량 0이면 포지션이 제거된다."""
        risk_config = RiskConfig()
        pt = PositionTracker(risk_config)

        pt.update_from_chejan("005930", 1, 58000, 58500)
        assert pt.get_position("005930") is not None

        pt.update_from_chejan("005930", 0, 0, 0)
        assert pt.get_position("005930") is None

    def test_order_to_balance_e2e(self):
        """주문 체결 → 잔고 업데이트 전체 흐름."""
        api = _make_mock_api()
        om = OrderManager(api, "7033652731")
        risk_config = RiskConfig()
        pt = PositionTracker(risk_config)

        # Wire: OrderManager.position_updated → PositionTracker
        om.position_updated.connect(
            lambda code, qty, buy_price, cur: pt.update_from_chejan(
                code, qty, buy_price, cur
            )
        )

        # Submit order
        om.submit_order("005930", OrderSide.BUY, 1, 0, HogaGb.MARKET)

        # Chejan: 접수
        real_no = "0099999"
        api.get_chejan_data.side_effect = lambda fid: {
            CHEJAN_FID.ORDER_NO: real_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "접수",
            CHEJAN_FID.UNFILLED_QTY: "1",
            CHEJAN_FID.EXEC_PRICE: "",
            CHEJAN_FID.EXEC_QTY: "0",
        }.get(fid, "")
        om.handle_chejan_data("0", 6, "")

        # Chejan: 체결
        api.get_chejan_data.side_effect = lambda fid: {
            CHEJAN_FID.ORDER_NO: real_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "체결",
            CHEJAN_FID.UNFILLED_QTY: "0",
            CHEJAN_FID.EXEC_PRICE: "+58000",
            CHEJAN_FID.EXEC_QTY: "1",
        }.get(fid, "")
        om.handle_chejan_data("0", 6, "")

        # Chejan: 잔고 통보 (gubun=1)
        api.get_chejan_data.side_effect = lambda fid: {
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.HOLDING_QTY: "1",
            CHEJAN_FID.BUY_UNIT_PRICE: "+58000",
            CHEJAN_FID.CURRENT_PRICE: "+58500",
        }.get(fid, "")
        om.handle_chejan_data("1", 4, "")

        # Verify position created
        pos = pt.get_position("005930")
        assert pos is not None
        assert pos.qty == 1
        assert pos.unrealized_pnl == 500


# ===========================================================================
# Test 4: 매도 주문 → 포지션 제거
# ===========================================================================
class TestSellOrder:
    """매도 주문 체결 후 잔고 0 → 포지션 제거."""

    def test_sell_removes_position(self):
        api = _make_mock_api()
        om = OrderManager(api, "7033652731")
        risk_config = RiskConfig()
        pt = PositionTracker(risk_config)

        om.position_updated.connect(
            lambda code, qty, buy_price, cur: pt.update_from_chejan(
                code, qty, buy_price, cur
            )
        )

        # Start with a position
        pt.update_from_chejan("005930", 1, 58000, 58000)
        assert pt.get_position("005930") is not None

        # Submit sell
        om.submit_order("005930", OrderSide.SELL, 1, 0, HogaGb.MARKET)

        # Chejan: 접수 + 체결
        real_no = "0088888"
        api.get_chejan_data.side_effect = lambda fid: {
            CHEJAN_FID.ORDER_NO: real_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "접수",
            CHEJAN_FID.UNFILLED_QTY: "1",
            CHEJAN_FID.EXEC_PRICE: "",
            CHEJAN_FID.EXEC_QTY: "0",
        }.get(fid, "")
        om.handle_chejan_data("0", 6, "")

        api.get_chejan_data.side_effect = lambda fid: {
            CHEJAN_FID.ORDER_NO: real_no,
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.ORDER_STATUS: "체결",
            CHEJAN_FID.UNFILLED_QTY: "0",
            CHEJAN_FID.EXEC_PRICE: "+58500",
            CHEJAN_FID.EXEC_QTY: "1",
        }.get(fid, "")
        om.handle_chejan_data("0", 6, "")

        # 잔고: 보유수량 0
        api.get_chejan_data.side_effect = lambda fid: {
            CHEJAN_FID.CODE: "A005930",
            CHEJAN_FID.HOLDING_QTY: "0",
            CHEJAN_FID.BUY_UNIT_PRICE: "0",
            CHEJAN_FID.CURRENT_PRICE: "0",
        }.get(fid, "")
        om.handle_chejan_data("1", 4, "")

        # Position should be removed
        assert pt.get_position("005930") is None


# ===========================================================================
# Test 5: opw00018 잔고 조회 → PositionTracker 초기 동기화
# ===========================================================================
class TestBalanceQuery:
    """Phase 9: 잔고 조회 TR → PositionTracker 동기화."""

    def _make_balance_query(self):
        api = _make_mock_api()
        tr_queue = MagicMock()
        event_registry = MagicMock()

        from kiwoom_trader.api.balance_query import BalanceQuery
        bq = BalanceQuery(api, tr_queue, event_registry)
        return api, tr_queue, event_registry, bq

    def test_query_enqueues_tr(self):
        """query() 호출 시 TR 큐에 요청이 등록된다."""
        api, tr_queue, registry, bq = self._make_balance_query()

        bq.query("7033652731")

        tr_queue.enqueue.assert_called_once()
        call_kwargs = tr_queue.enqueue.call_args
        assert call_kwargs[1]["tr_code"] == "opw00018"

    def test_response_parses_positions(self):
        """TR 응답에서 보유 종목 목록이 파싱된다."""
        api, tr_queue, registry, bq = self._make_balance_query()

        # Sample: 삼성전자 10주, 카카오 5주
        sample_data = {
            ("opw00018", "", 0, "종목번호"): " A005930",
            ("opw00018", "", 0, "종목명"): "삼성전자",
            ("opw00018", "", 0, "보유수량"): "10",
            ("opw00018", "", 0, "매입가"): "58000",
            ("opw00018", "", 0, "현재가"): "59000",
            ("opw00018", "", 0, "평가손익"): "10000",
            ("opw00018", "", 0, "수익률(%)"): "1.72",
            ("opw00018", "", 1, "종목번호"): " A035720",
            ("opw00018", "", 1, "종목명"): "카카오",
            ("opw00018", "", 1, "보유수량"): "5",
            ("opw00018", "", 1, "매입가"): "45000",
            ("opw00018", "", 1, "현재가"): "44000",
            ("opw00018", "", 1, "평가손익"): "-5000",
            ("opw00018", "", 1, "수익률(%)"): "-2.22",
        }

        api.get_repeat_cnt.return_value = 2
        api.get_comm_data.side_effect = lambda tc, rn, idx, item: \
            sample_data.get((tc, rn, idx, item), "")

        results = []
        bq.query("7033652731", on_complete=lambda pos: results.extend(pos))

        # Simulate TR response callback
        bq._on_receive("3000", "계좌평가잔고내역요청", "opw00018", "", "0", 0, "", "", "")

        assert len(results) == 2
        assert results[0]["code"] == "005930"
        assert results[0]["qty"] == 10
        assert results[0]["buy_price"] == 58000
        assert results[0]["current_price"] == 59000
        assert results[1]["code"] == "035720"
        assert results[1]["qty"] == 5

    def test_balance_to_position_tracker(self):
        """잔고 조회 결과 → PositionTracker 반영 E2E."""
        api, tr_queue, registry, bq = self._make_balance_query()
        risk_config = RiskConfig()
        pt = PositionTracker(risk_config)

        sample_data = {
            ("opw00018", "", 0, "종목번호"): " A005930",
            ("opw00018", "", 0, "종목명"): "삼성전자",
            ("opw00018", "", 0, "보유수량"): "10",
            ("opw00018", "", 0, "매입가"): "58000",
            ("opw00018", "", 0, "현재가"): "59000",
            ("opw00018", "", 0, "평가손익"): "10000",
            ("opw00018", "", 0, "수익률(%)"): "1.72",
        }

        api.get_repeat_cnt.return_value = 1
        api.get_comm_data.side_effect = lambda tc, rn, idx, item: \
            sample_data.get((tc, rn, idx, item), "")

        def on_complete(positions_list):
            for pos in positions_list:
                pt.update_from_chejan(
                    pos["code"], pos["qty"], pos["buy_price"], pos["current_price"]
                )

        bq.query("7033652731", on_complete=on_complete)
        bq._on_receive("3000", "계좌평가잔고내역요청", "opw00018", "", "0", 0, "", "", "")

        pos = pt.get_position("005930")
        assert pos is not None
        assert pos.qty == 10
        assert pos.avg_price == 58000
        assert pos.unrealized_pnl == 10000  # (59000-58000)*10

    def test_empty_balance(self):
        """보유 종목 없을 때 빈 목록 반환."""
        api, tr_queue, registry, bq = self._make_balance_query()

        api.get_repeat_cnt.return_value = 0

        results = []
        bq.query("7033652731", on_complete=lambda pos: results.extend(pos))
        bq._on_receive("3000", "계좌평가잔고내역요청", "opw00018", "", "0", 0, "", "", "")

        assert len(results) == 0
