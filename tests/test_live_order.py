"""Phase 8 수동 테스트: 모의투자 주문 실행 확인.

장중에 실행:
    .venv32\\Scripts\\python.exe tests/test_live_order.py

Check 항목:
1. 삼성전자 1주 시장가 매수 주문 제출
2. OnReceiveChejanData 콜백으로 주문 상태 변경 수신
3. 체결 후 잔고 업데이트 수신
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from loguru import logger

from kiwoom_trader.api.kiwoom_api import KiwoomAPI
from kiwoom_trader.api.session_manager import SessionManager
from kiwoom_trader.config.constants import HogaGb
from kiwoom_trader.core.models import OrderSide
from kiwoom_trader.core.order_manager import OrderManager


def main():
    app = QApplication(sys.argv)
    logger.info("=== Phase 8: 모의투자 주문 테스트 ===")

    api = KiwoomAPI()
    session = SessionManager(api)

    def on_login(err_code):
        if err_code != 0:
            logger.error(f"로그인 실패: {err_code}")
            app.quit()
            return

        logger.info("로그인 성공")

        # Get account
        accounts = api.get_login_info("ACCNO")
        account_list = [a for a in accounts.split(";") if a.strip()]
        # Select stock account (suffix 31)
        account = account_list[0]
        for acc in account_list:
            if acc.endswith("31"):
                account = acc
                break
        logger.info(f"사용 계좌: {account}")

        # Create OrderManager
        om = OrderManager(api, account)

        # Wire chejan events
        api.chejan_data_received.connect(
            lambda gubun, item_cnt, fid_list: om.handle_chejan_data(
                gubun, item_cnt, fid_list
            )
        )

        # Log order events
        om.order_filled.connect(
            lambda no, code, qty, price: logger.info(
                f"[FILLED] 주문번호={no}, 종목={code}, 수량={qty}, 체결가={price}"
            )
        )
        om.order_rejected.connect(
            lambda no, reason: logger.error(f"[REJECTED] {no}: {reason}")
        )
        om.position_updated.connect(
            lambda code, qty, buy_price, cur: logger.info(
                f"[BALANCE] {code} 보유={qty} 매입가={buy_price} 현재가={cur}"
            )
        )

        # Submit test order: 삼성전자 1주 시장가 매수
        logger.info("삼성전자(005930) 1주 시장가 매수 주문 제출...")
        order = om.submit_order(
            code="005930",
            side=OrderSide.BUY,
            qty=1,
            price=0,  # 시장가는 price=0
            hoga_gb=HogaGb.MARKET,
        )
        logger.info(f"주문 상태: {order.state.name}")

        # Auto-quit after 30 seconds
        QTimer.singleShot(30000, lambda: (logger.info("30초 경과, 종료"), app.quit()))

    api.connected.connect(on_login)
    api.comm_connect()
    logger.info("로그인 대기 중...")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
