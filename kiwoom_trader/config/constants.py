"""FID codes, screen numbers, and login error codes for Kiwoom OpenAPI+."""

from enum import Enum, auto


class FID:
    """Kiwoom real-time data Field IDs."""

    # Stock Execution (주식체결) real type
    CURRENT_PRICE = 10  # 현재가
    PREV_CLOSE_DIFF = 11  # 전일대비
    DIFF_RATE = 12  # 등락율
    VOLUME = 13  # (누적)거래량
    TRADE_AMOUNT = 14  # 거래대금
    EXEC_VOLUME = 15  # 체결량
    OPEN_PRICE = 16  # 시가
    HIGH_PRICE = 17  # 고가
    LOW_PRICE = 18  # 저가
    EXEC_TIME = 20  # 체결시간 (HHMMSS)
    PREV_CLOSE_DIFF_SIGN = 25  # 전일대비기호
    ASK_PRICE_1 = 27  # 매도호가1
    BID_PRICE_1 = 28  # 매수호가1
    EXEC_STRENGTH = 228  # 체결강도

    # Stock Orderbook (주식호가) real type
    ASK_PRICES = [41, 61, 62, 63, 64, 65, 66, 67, 68, 69]
    BID_PRICES = [51, 71, 72, 73, 74, 75, 76, 77, 78, 79]

    # Market Time (장시작시간) real type
    MARKET_OP = 215  # 장운영구분
    MARKET_TIME = 20  # 체결시간


class SCREEN:
    """Screen numbers for Kiwoom API calls."""

    LOGIN = "0000"
    TR_BASE = 1000  # Auto-increment from here
    REAL_BASE = 5000
    ORDER_BASE = 2000  # 주문용 화면번호 시작


class LOGIN_ERROR:
    """OnEventConnect error codes."""

    SUCCESS = 0
    PASSWORD_ERROR = -100
    ACCOUNT_DIFF = -101
    MONTHLY_FEE_UNPAID = -102
    IP_RESTRICTED = -103
    VERSION_MISMATCH = -104
    AUTH_ERROR = -105
    USER_LOCKED = -106


class CHEJAN_FID:
    """FID numbers for GetChejanData() calls."""

    # --- gubun=0: 주문체결통보 ---
    ACCOUNT_NO = 9201  # 계좌번호
    ORDER_NO = 9203  # 주문번호
    ADMIN_NO = 9205  # 관리자사번
    CODE = 9001  # 종목코드, 업종코드
    ORDER_CATEGORY = 912  # 주문업무분류
    ORDER_STATUS = 913  # 주문상태(접수, 확인, 체결)
    STOCK_NAME = 302  # 종목명
    ORDER_QTY = 900  # 주문수량
    ORDER_PRICE = 901  # 주문가격
    UNFILLED_QTY = 902  # 미체결수량
    EXEC_CUMUL_AMOUNT = 903  # 체결누계금액
    ORG_ORDER_NO = 904  # 원주문번호
    ORDER_GUBUN = 905  # 주문구분(+현금매수,-현금매도...)
    TRADE_GUBUN = 906  # 매매구분(보통,시장가...)
    SELL_BUY = 907  # 매도수구분 (1:매도, 2:매수)
    ORDER_EXEC_TIME = 908  # 주문/체결시간(HHMMSSMS)
    EXEC_NO = 909  # 체결번호
    EXEC_PRICE = 910  # 체결가
    EXEC_QTY = 911  # 체결량
    CURRENT_PRICE = 10  # 현재가, 체결가, 실시간종가
    BEST_ASK = 27  # (최우선)매도호가
    BEST_BID = 28  # (최우선)매수호가
    UNIT_EXEC_PRICE = 914  # 단위체결가
    UNIT_EXEC_QTY = 915  # 단위체결량
    DAY_COMMISSION = 938  # 당일매매 수수료
    DAY_TAX = 939  # 당일매매세금

    # --- gubun=1: 잔고통보 ---
    HOLDING_QTY = 930  # 보유수량
    BUY_UNIT_PRICE = 931  # 매입단가
    TOTAL_BUY_PRICE = 932  # 총매입가
    ORDERABLE_QTY = 933  # 주문가능수량
    DAY_NET_BUY_QTY = 945  # 당일순매수량
    SELL_BUY_GUBUN = 946  # 매도/매수구분
    DAY_TOTAL_SELL_PNL = 950  # 당일 총 매도 손익
    DEPOSIT = 951  # 예수금
    REFERENCE_PRICE = 307  # 기준가
    PNL_RATE = 8019  # 손익률


class OrderType:
    """nOrderType parameter for SendOrder."""

    NEW_BUY = 1  # 신규매수
    NEW_SELL = 2  # 신규매도
    CANCEL_BUY = 3  # 매수취소
    CANCEL_SELL = 4  # 매도취소
    MODIFY_BUY = 5  # 매수정정
    MODIFY_SELL = 6  # 매도정정


class HogaGb:
    """sHogaGb (거래구분) parameter for SendOrder."""

    LIMIT = "00"  # 지정가
    MARKET = "03"  # 시장가
    CONDITIONAL_LIMIT = "05"  # 조건부지정가
    BEST_LIMIT = "06"  # 최유리지정가
    FIRST_LIMIT = "07"  # 최우선지정가
    LIMIT_IOC = "10"  # 지정가IOC
    MARKET_IOC = "13"  # 시장가IOC
    BEST_IOC = "16"  # 최유리IOC
    LIMIT_FOK = "20"  # 지정가FOK
    MARKET_FOK = "23"  # 시장가FOK
    BEST_FOK = "26"  # 최유리FOK
    PRE_MARKET_CLOSE = "61"  # 장전시간외종가
    AFTER_HOURS = "62"  # 시간외단일가
    POST_MARKET_CLOSE = "81"  # 장후시간외종가


class ORDER_ERROR:
    """SendOrder and general API error codes."""

    SUCCESS = 0  # OP_ERR_NONE: 정상처리
    FAIL = -10  # OP_ERR_FAIL: 실패
    LOGIN_FAIL = -100  # OP_ERR_LOGIN: 사용자정보 교환실패
    CONNECT_FAIL = -101  # OP_ERR_CONNECT: 서버접속 실패
    VERSION_FAIL = -102  # OP_ERR_VERSION: 버전처리 실패
    FIREWALL_FAIL = -103  # OP_ERR_FIREWALL: 개인방화벽 실패
    MEMORY_FAIL = -104  # OP_ERR_MEMORY: 메모리보호 실패
    INPUT_FAIL = -105  # OP_ERR_INPUT: 함수입력값 오류
    SOCKET_CLOSED = -106  # OP_ERR_SOCKET_CLOSED: 통신 연결종료
    SISE_OVERFLOW = -200  # OP_ERR_SISE_OVERFLOW: 시세조회 과부하
    RQ_STRUCT_FAIL = -201  # 전문작성 초기화 실패
    RQ_STRING_FAIL = -202  # 전문작성 입력값 오류
    NO_DATA = -203  # OP_ERR_NO_DATA: 데이터 없음
    OVER_MAX_DATA = -204  # 조회 가능한 종목수 초과
    DATA_RCV_FAIL = -205  # 데이터수신 실패
    OVER_MAX_FID = -206  # 조회 가능한 FID수 초과
    REAL_CANCEL = -207  # 실시간 해제 오류
    ORD_WRONG_INPUT = -300  # OP_ERR_ORD_WRONG_INPUT: 입력값 오류
    ORD_WRONG_ACCTNO = -301  # 계좌 비밀번호 없음
    OTHER_ACC_USE = -302  # 타인계좌사용 오류
    MIS_2BILL_EXC = -303  # 주문가격이 20억원을 초과
    MIS_5BILL_EXC = -304  # 주문가격이 50억원을 초과
    MIS_1PER_EXC = -305  # 주문수량이 총발행주수의 1% 초과오류
    MIS_3PER_EXC = -306  # 주문수량이 총발행주수의 3% 초과오류
    SEND_FAIL = -307  # OP_ERR_SEND_FAIL: 주문전송 실패
    ORD_OVERFLOW = -308  # 주문전송 과부하
    MIS_300CNT_EXC = -309  # 주문수량 300계약 초과
    MIS_500CNT_EXC = -310  # 주문수량 500계약 초과
    ORD_WRONG_ACCTINFO = -340  # 계좌정보없음
    ORD_SYMCODE_EMPTY = -500  # 종목코드없음


class MarketState(Enum):
    """Market time-of-day states for trading control."""

    PRE_MARKET_AUCTION = auto()  # 08:30~09:00 동시호가 -- 주문 차단
    MARKET_OPEN_BUFFER = auto()  # 09:00~09:05 안정화 대기 -- 주문 차단
    TRADING = auto()  # 09:05~15:15 정규 매매
    CLOSING = auto()  # 15:15~15:20 신규매수 중단, 청산 진행
    CLOSING_AUCTION = auto()  # 15:20~15:30 장종료 동시호가 -- 주문 차단
    CLOSED = auto()  # 15:30~ 장 종료


class MarketOperation:
    """FID 215 장운영구분 values from Kiwoom API."""

    PRE_MARKET = "0"  # 장시작전
    CLOSE_APPROACHING = "2"  # 장종료전
    MARKET_OPEN = "3"  # 장시작
    MARKET_CLOSE_48 = "4"  # 장종료 (4 또는 8)
    MARKET_CLOSE_9 = "9"  # 장마감
