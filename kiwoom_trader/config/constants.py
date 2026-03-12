"""FID codes, screen numbers, and login error codes for Kiwoom OpenAPI+."""


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
