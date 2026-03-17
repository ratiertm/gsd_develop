"""FID codes, screen numbers, and login error codes for Kiwoom OpenAPI+.

Based on C:\\OpenAPI\\data\\nkrealtime.dat (실시간 데이터 레이아웃)
"""

from enum import Enum, auto


# ═══════════════════════════════════════════════════════
#  FID 정의 (nkrealtime.dat 기반 전체)
# ═══════════════════════════════════════════════════════

class FID:
    """Kiwoom real-time data Field IDs."""

    # ── 기본 시세 ──
    CURRENT_PRICE = 10       # 현재가
    PREV_CLOSE_DIFF = 11     # 전일대비
    DIFF_RATE = 12           # 등락율
    VOLUME = 13              # (누적)거래량
    TRADE_AMOUNT = 14        # 거래대금
    EXEC_VOLUME = 15         # 체결량
    OPEN_PRICE = 16          # 시가
    HIGH_PRICE = 17          # 고가
    LOW_PRICE = 18           # 저가
    EXEC_TIME = 20           # 체결시간 (HHMMSS)
    OFFER_TIME = 21          # 호가시간
    OFFER_EXEC_TIME = 22     # 호가/체결시간
    PREV_VOLUME = 23         # 전일거래량대비(계약,주)
    PREV_VOLUME_RATE = 24    # 전일거래량대비(비율)
    PREV_CLOSE_DIFF_SIGN = 25  # 전일대비기호
    CHANGE_SPEED = 26        # 체결가변동폭?
    ASK_PRICE_1 = 27         # (최우선)매도호가
    BID_PRICE_1 = 28         # (최우선)매수호가
    TOTAL_ASK_REMAIN = 29    # 매도호가총잔량
    TOTAL_BID_REMAIN = 30    # 매수호가총잔량
    BEST_ASK_CHANGE = 31     # 최우선매도호가잔량변동
    BEST_BID_CHANGE = 32     # 최우선매수호가잔량변동

    # ── 호가 10단계 (매도) ──
    ASK_PRICE_1_ = 41;  ASK_QTY_1 = 61;  ASK_COUNT_1 = 81
    ASK_PRICE_2 = 42;   ASK_QTY_2 = 62;  ASK_COUNT_2 = 82
    ASK_PRICE_3 = 43;   ASK_QTY_3 = 63;  ASK_COUNT_3 = 83
    ASK_PRICE_4 = 44;   ASK_QTY_4 = 64;  ASK_COUNT_4 = 84
    ASK_PRICE_5 = 45;   ASK_QTY_5 = 65;  ASK_COUNT_5 = 85
    ASK_PRICE_6 = 46;   ASK_QTY_6 = 66;  ASK_COUNT_6 = 86
    ASK_PRICE_7 = 47;   ASK_QTY_7 = 67;  ASK_COUNT_7 = 87
    ASK_PRICE_8 = 48;   ASK_QTY_8 = 68;  ASK_COUNT_8 = 88
    ASK_PRICE_9 = 49;   ASK_QTY_9 = 69;  ASK_COUNT_9 = 89
    ASK_PRICE_10 = 50;  ASK_QTY_10 = 70; ASK_COUNT_10 = 90

    # ── 호가 10단계 (매수) ──
    BID_PRICE_1_ = 51;  BID_QTY_1 = 71;  BID_COUNT_1 = 91
    BID_PRICE_2 = 52;   BID_QTY_2 = 72;  BID_COUNT_2 = 92
    BID_PRICE_3 = 53;   BID_QTY_3 = 73;  BID_COUNT_3 = 93
    BID_PRICE_4 = 54;   BID_QTY_4 = 74;  BID_COUNT_4 = 94
    BID_PRICE_5 = 55;   BID_QTY_5 = 75;  BID_COUNT_5 = 95
    BID_PRICE_6 = 56;   BID_QTY_6 = 76;  BID_COUNT_6 = 96
    BID_PRICE_7 = 57;   BID_QTY_7 = 77;  BID_COUNT_7 = 97
    BID_PRICE_8 = 58;   BID_QTY_8 = 78;  BID_COUNT_8 = 98
    BID_PRICE_9 = 59;   BID_QTY_9 = 79;  BID_COUNT_9 = 99
    BID_PRICE_10 = 60;  BID_QTY_10 = 80; BID_COUNT_10 = 100

    # ── 호가 잔량합계 ──
    TOTAL_ASK_QTY = 121      # 매도호가총잔량
    TOTAL_BID_QTY = 122      # 매수호가총잔량
    TOTAL_ASK_COUNT = 123    # 매도호가총건수
    TOTAL_ASK_CHANGE_QTY = 125  # 매도호가총잔량변동
    TOTAL_BID_CHANGE_QTY = 126  # 매수호가총잔량변동
    TOTAL_BID_COUNT = 127    # 매수호가총건수
    OFFER_RATE = 128         # 호가순잔량(비율)
    SPREAD = 137             # 스프레드
    TURNOVER_RATE = 138      # 회전율(매도)
    TURNOVER_RATE_BID = 139  # 회전율(매수)

    # ── 시간외호가 ──
    AFTER_ASK_PRICE_1 = 131  # 시간외매도호가1
    AFTER_BID_PRICE_1 = 132  # 시간외매수호가1
    AFTER_ASK_QTY_1 = 135    # 시간외매도호가잔량1
    AFTER_BID_QTY_1 = 136    # 시간외매수호가잔량1

    # ── 당일거래원 ──
    TRADER_ASK_1 = 141;  TRADER_BID_1 = 151
    TRADER_ASK_2 = 142;  TRADER_BID_2 = 152
    TRADER_ASK_3 = 143;  TRADER_BID_3 = 153
    TRADER_ASK_4 = 144;  TRADER_BID_4 = 154
    TRADER_ASK_5 = 145;  TRADER_BID_5 = 155
    TRADER_ASK_VOLUME_1 = 161; TRADER_BID_VOLUME_1 = 171
    TRADER_ASK_VOLUME_2 = 162; TRADER_BID_VOLUME_2 = 172
    TRADER_ASK_VOLUME_3 = 163; TRADER_BID_VOLUME_3 = 173
    TRADER_ASK_VOLUME_4 = 164; TRADER_BID_VOLUME_4 = 174
    TRADER_ASK_VOLUME_5 = 165; TRADER_BID_VOLUME_5 = 175
    TRADER_ASK_COLOR_1 = 166;  TRADER_BID_COLOR_1 = 176
    TRADER_ASK_COLOR_2 = 167;  TRADER_BID_COLOR_2 = 177
    TRADER_ASK_COLOR_3 = 168;  TRADER_BID_COLOR_3 = 178
    TRADER_ASK_COLOR_4 = 169;  TRADER_BID_COLOR_4 = 179
    TRADER_ASK_COLOR_5 = 170;  TRADER_BID_COLOR_5 = 180
    TRADER_ASK_NATION_1 = 146; TRADER_BID_NATION_1 = 156
    TRADER_ASK_NATION_2 = 147; TRADER_BID_NATION_2 = 157
    TRADER_ASK_NATION_3 = 148; TRADER_BID_NATION_3 = 158
    TRADER_ASK_NATION_4 = 149; TRADER_BID_NATION_4 = 159
    TRADER_ASK_NATION_5 = 150; TRADER_BID_NATION_5 = 160
    FOREIGN_ASK_QTY = 271;     FOREIGN_BID_QTY = 281
    FOREIGN_ASK_QTY_2 = 272;   FOREIGN_BID_QTY_2 = 282
    FOREIGN_ASK_QTY_3 = 273;   FOREIGN_BID_QTY_3 = 283
    FOREIGN_ASK_QTY_4 = 274;   FOREIGN_BID_QTY_4 = 284
    FOREIGN_ASK_QTY_5 = 275;   FOREIGN_BID_QTY_5 = 285
    TOTAL_ASK_PURE = 261     # 매도거래원합(순수)
    TOTAL_BID_PURE = 262     # 매수거래원합(순수)
    FOREIGN_PURE_QTY = 263   # 외국인순수
    INSTITUTION_PURE_QTY = 264  # 기관순수
    TRADER_ASK_PURE = 267    # 매도거래원합(순매수)
    TRADER_BID_PURE = 268    # 매수거래원합(순매수)

    # ── 체결강도/프로그램 ──
    EXEC_STRENGTH = 228      # 체결강도
    ASK_REMAIN_RATE = 200    # 매도잔량대비
    BID_REMAIN_RATE = 201    # 매수잔량대비
    PROGRAM_ASK = 291        # 프로그램매도
    PROGRAM_BID = 292        # 프로그램매수
    PROGRAM_NET_ASK = 293    # 프로그램순매도
    PROGRAM_NET_BID = 294    # 프로그램순매수?
    PROGRAM_TOTAL = 295      # 프로그램합계
    OFFER_PURE_RATE = 238    # 호가순잔량비율
    OFFER_PURE_QTY = 299     # 호가순잔량

    # ── 주식체결(0B) 추가 FID ──
    LISTING_QTY = 311        # 상장주식수
    MARKET_CAP = 290         # 시가총액(억)
    FOREIGN_HOLD_RATE = 691  # 외국인보유비율
    FLUCTUATION = 822        # 변동
    TRANS_TIME_1 = 567       # 거래시간1
    TRANS_TIME_2 = 568       # 거래시간2
    EXPECTED_PRICE = 851     # 예상체결가
    MARKET_WARNING = 732     # 시장경고
    HALT = 852               # 정지
    MARKET_ALARM = 337       # 시장알림

    # ── 프로그램매매 추가 ──
    PROGRAM_ASK_VOLUME = 1890   # 프로그램매도수량
    PROGRAM_BID_VOLUME = 1891   # 프로그램매수수량
    PROGRAM_NET_VOLUME = 1892   # 프로그램순매수수량
    PROGRAM_ASK_AMOUNT = 1030   # 프로그램매도금액
    PROGRAM_BID_AMOUNT = 1031   # 프로그램매수금액
    PROGRAM_NET_AMOUNT = 1032   # 프로그램순매수금액
    PROGRAM_ASK_COUNT = 1071    # 프로그램매도건수
    PROGRAM_BID_COUNT = 1072    # 프로그램매수건수

    # ── 투자자별 ──
    INVESTOR_ASK_1 = 1313    # 투자자별매도1
    INVESTOR_BID_1 = 1315    # 투자자별매수1
    INVESTOR_NET_1 = 1316    # 투자자별순매수1
    INVESTOR_TOTAL = 1314    # 투자자합계

    # ── 외국인 관련 ──
    FOREIGN_ORDER_QTY = 1497    # 외국인주문수량
    FOREIGN_ORDER_AMOUNT = 1498 # 외국인주문금액
    FOREIGN_NET = 620           # 외국인순매수

    # ── 업종/종목코드 ──
    STOCK_CODE = 9001        # 종목코드
    STOCK_NAME = 302         # 종목명
    VOLUME_POWER = 333       # 거래량파워
    SECTOR_CODE = 9076       # 업종코드

    # ── ETF NAV (0G) ──
    NAV = 36                 # NAV
    NAV_DIFF = 37            # NAV전일대비
    NAV_DIFF_RATE = 38       # NAV등락율
    TRACKING_ERROR = 39      # 추적오차율
    LP_HOLD_RATE = 768       # LP보유비중
    DEVIATION_RATE = 769     # 괴리율
    DEVIATION_RATE_SIGN = 770  # 괴리율부호
    NAV_HIGH = 265           # NAV고가
    NAV_LOW = 266            # NAV저가

    # ── 투자자별 상세 (0g 주식종목정보) ──
    PER = 297                # PER
    EPS = 592                # EPS
    ROE = 593                # ROE
    FACE_VALUE = 305         # 액면가
    LISTING_DATE = 306       # 상장일
    REF_PRICE = 307          # 기준가
    CREDIT_RATE = 689        # 신용비율
    BPS = 594                # BPS
    MARKET_RATE_52W = 382    # 52주최고가대비
    PBR = 370                # PBR
    EARNING_RATE = 330       # 수익률
    FOREIGN_LIMIT = 300      # 외국인한도
    TURNOVER = 1491          # 회전율

    # ── 장시작시간 (0s) ──
    MARKET_OP = 215          # 장운영구분
    MARKET_TIME = 214        # 시각

    # ── 업종지수 (0J) ──
    # CURRENT_PRICE(10), PREV_CLOSE_DIFF(11), DIFF_RATE(12) 공유

    # ── 업종등락 (0U) ──
    ADVANCE_COUNT = 252      # 상승
    UNCHANGED_COUNT = 251    # 보합
    DECLINE_COUNT = 253      # 하락
    UPPER_LIMIT = 255        # 상한
    LOWER_LIMIT = 254        # 하한
    UP_DOWN_52W = 256        # 52주신고가
    UP_DOWN_52W_LOW = 257    # 52주신저가

    # ── 환율 (0S) ──
    EXCHANGE_RATES = list(range(570, 585))  # FID 570~584

    # ── 상황/속보 (0T) ──
    NEWS_CATEGORY = 225      # 뉴스종류
    NEWS_CODE = 777          # 뉴스코드
    NEWS_TITLE = 222         # 뉴스제목
    NEWS_BODY = 223          # 뉴스본문
    NEWS_DATE = 224          # 뉴스날짜
    NEWS_TIME_2 = 249        # 뉴스시간
    NEWS_LINK = 250          # 뉴스링크
    NEWS_TICKER = 9407       # 뉴스티커

    # ── 조건검색 (02/03) ──
    CONDITION_INDEX = 841    # 조건식인덱스
    CONDITION_CODE = 843     # 조건식종목코드
    SIGNAL_TYPE = 840        # 신호종류
    CONDITION_STOCK_NAME = 842  # 종목명

    # ── 선물/옵션 체결 (0K/0O) 추가 ──
    SETTLE_PRICE = 195       # 정산가
    THEORETICAL = 182        # 이론가
    OPEN_INTEREST = 184      # 미결제약정
    BASIS = 183              # 베이시스
    SPREAD_FO = 186          # 스프레드
    YESTERDAY_SETTLE = 181   # 전일정산가
    KOSPI200 = 185           # KOSPI200
    IMPLIED_VOL = 197        # 내재변동성
    GAMMA = 246              # 감마
    THETA = 247              # 세타
    VEGA = 248               # 베가
    RHO = 196                # 로
    DELTA = 187              # 델타

    # ── 옵션 추가 (0O) ──
    STRIKE_PRICE = 190       # 행사가
    ATM_GUBUN = 191          # ATM구분
    KAPPA = 193              # 카파
    LAMBDA_FO = 192          # 람다
    CALL_PUT = 194           # 콜풋구분
    OPEN_INTEREST_CHANGE = 219  # 미결제변동
    TIME_VALUE = 188         # 시간가치
    INTRINSIC_VALUE = 189    # 내재가치

    # ── VI발동/해제 (1y, 1z) ──
    VI_TYPE = 1229           # VI종류
    VI_PRICE = 1227          # VI가격
    VI_DIFF = 1228           # VI전일대비
    VI_BASE_PRICE = 1487     # VI기준가
    VI_TRIGGER_PRICE = 1488  # VI발동가

    # ── 예탁금 (0v/0-) 실시간자산 ──
    DEPOSIT_1 = 8048;  DEPOSIT_2 = 8049;  DEPOSIT_3 = 8050
    DEPOSIT_4 = 8051;  DEPOSIT_5 = 8052;  DEPOSIT_6 = 8053
    DEPOSIT_7 = 8054;  DEPOSIT_8 = 8055;  DEPOSIT_9 = 8056
    DEPOSIT_10 = 8057; DEPOSIT_11 = 8058; DEPOSIT_12 = 8059
    DEPOSIT_13 = 8060; DEPOSIT_14 = 8061; DEPOSIT_15 = 8062
    DEPOSIT_16 = 8066; DEPOSIT_17 = 8063; DEPOSIT_18 = 8064
    DEPOSIT_19 = 8065; DEPOSIT_20 = 8067; DEPOSIT_21 = 8068

    # ── 호가잔량추가 (0D 확장 FID) ──
    ASK_LP_QTY_1 = 621;  ASK_LP_QTY_2 = 622;  ASK_LP_QTY_3 = 623
    ASK_LP_QTY_4 = 624;  ASK_LP_QTY_5 = 625;  ASK_LP_QTY_6 = 626
    ASK_LP_QTY_7 = 627;  ASK_LP_QTY_8 = 628;  ASK_LP_QTY_9 = 629
    ASK_LP_QTY_10 = 630
    BID_LP_QTY_1 = 631;  BID_LP_QTY_2 = 632;  BID_LP_QTY_3 = 633
    BID_LP_QTY_4 = 634;  BID_LP_QTY_5 = 635;  BID_LP_QTY_6 = 636
    BID_LP_QTY_7 = 637;  BID_LP_QTY_8 = 638;  BID_LP_QTY_9 = 639
    BID_LP_QTY_10 = 640

    # ── 실시간차트 (2R~2V) ──
    CHART_INDICATOR_TYPE = 7102   # 지표종류
    CHART_INDICATOR_VALUE = 7103  # 지표값
    CHART_OPEN = 1900        # 차트시가
    CHART_HIGH = 1901        # 차트고가
    CHART_LOW = 1902         # 차트저가
    CHART_CLOSE = 1903       # 차트종가
    CHART_VOLUME_2 = 1904    # 차트거래량
    CHART_AMOUNT = 1905      # 차트거래대금
    CHART_CHANGE = 1906      # 차트전일대비
    CHART_CHANGE_RATE = 1907 # 차트등락율
    CHART_DATE = 1908        # 차트날짜
    CHART_TIME_2 = 352       # 차트시간

    # ── 당일거래원 확장 (0F) ──
    TRADER_NET_ASK_VOLUME_1 = 1861; TRADER_NET_BID_VOLUME_1 = 1871
    TRADER_NET_ASK_VOLUME_2 = 1862; TRADER_NET_BID_VOLUME_2 = 1872
    TRADER_NET_ASK_VOLUME_3 = 1863; TRADER_NET_BID_VOLUME_3 = 1873
    TRADER_NET_ASK_VOLUME_4 = 1864; TRADER_NET_BID_VOLUME_4 = 1874
    TRADER_NET_ASK_VOLUME_5 = 1865; TRADER_NET_BID_VOLUME_5 = 1875
    FOREIGN_NET_PURE = 1261  # 외국인순수(순매수)
    INSTITUTION_NET_PURE = 1263  # 기관순수(순매수)
    PROGRAM_NET_PURE = 1267  # 프로그램순수(순매수)

    # ── 9081: 체결구분(0B 확장) ──
    EXEC_GUBUN = 9081        # 체결구분 (매수/매도)


# ═══════════════════════════════════════════════════════
#  실시간 타입별 FID 맵 (nkrealtime.dat 원본 기준)
# ═══════════════════════════════════════════════════════

REALTIME_FIDS = {
    # 1. 주식
    "주식예상체결": {  # 0A, 22 FIDs
        "fids": [10, 11, 12, 27, 28, 13, 14, 16, 17, 18, 25, 26, 29, 30, 31, 32, 311, 822, 567, 568, 732, 852],
    },
    "주식체결": {  # 0B, 44 FIDs
        "fids": [20, 10, 11, 12, 27, 28, 15, 13, 14, 16, 17, 18, 25, 26, 29, 30, 31, 32, 228, 311, 290, 691, 822, 567, 568, 851, 1890, 1891, 1892, 1030, 1031, 1032, 1071, 1072, 1313, 1315, 1316, 1314, 1497, 1498, 620, 732, 852, 9081],
    },
    "주식우선호가": {  # 0C, 2 FIDs
        "fids": [27, 28],
    },
    "주식호가잔량": {  # 0D, 163 FIDs (확장)
        "fids": [21, 41, 61, 81, 51, 71, 91,
                 42, 62, 82, 52, 72, 92, 43, 63, 83, 53, 73, 93,
                 44, 64, 84, 54, 74, 94, 45, 65, 85, 55, 75, 95,
                 46, 66, 86, 56, 76, 96, 47, 67, 87, 57, 77, 97,
                 48, 68, 88, 58, 78, 98, 49, 69, 89, 59, 79, 99,
                 50, 70, 90, 60, 80, 100,
                 121, 122, 125, 126, 23, 24, 128, 129, 138, 139,
                 200, 201, 238, 291, 292, 293, 294, 295,
                 621, 631, 622, 632, 623, 633, 624, 634, 625, 635,
                 626, 636, 627, 637, 628, 638, 629, 639, 630, 640,
                 13, 299, 215, 216],
    },
    "주식시간외호가": {  # 0E, 5 FIDs
        "fids": [21, 131, 132, 135, 136],
    },
    "주식당일거래원": {  # 0F, 88 FIDs
        "fids": [141, 161, 166, 146, 271, 151, 171, 176, 156, 281,
                 142, 162, 167, 147, 272, 152, 172, 177, 157, 282,
                 143, 163, 168, 148, 273, 153, 173, 178, 158, 283,
                 144, 164, 169, 149, 274, 154, 174, 179, 159, 284,
                 145, 165, 170, 150, 275, 155, 175, 180, 160, 285,
                 261, 262, 263, 264, 267, 268, 337, 13,
                 1861, 1862, 1863, 1864, 1865,
                 1871, 1872, 1873, 1874, 1875,
                 1261, 1263, 1267,
                 1876, 1877, 1878, 1879, 1880,
                 1881, 1882, 1883, 1884, 1885,
                 1264, 1265, 1266,
                 1886, 1887, 1888, 1889],
    },
    "ETF NAV": {  # 0G, 15 FIDs
        "fids": [36, 37, 38, 39, 20, 10, 11, 12, 13, 25, 768, 769, 770, 265, 266],
    },
    "주식시간외체결": {  # 0H, 8 FIDs
        "fids": [20, 10, 11, 12, 15, 13, 25, 9081],
    },
    "주식종목정보": {  # 0g, 13 FIDs
        "fids": [297, 592, 593, 305, 306, 307, 689, 594, 382, 370, 330, 300, 1491],
    },
    "주식거래원": {  # 0Q, 16 FIDs
        "fids": [9001, 9026, 302, 334, 20, 203, 207, 210, 211, 260, 337, 10, 11, 12, 25, 1319],
    },

    # 2. 선물
    "선물체결": {  # 0K, 43 FIDs
        "fids": [20, 10, 11, 12, 27, 28, 15, 13, 14, 16, 17, 18, 195, 182, 184, 183, 186, 181, 185, 25, 197, 26, 246, 247, 248, 30, 196, 845, 848, 846, 849, 847, 850, 851, 1365, 1366, 1367, 305, 306, 228, 232, 234, 236],
    },
    "선물호가잔량": {  # 0L, 61 FIDs
        "fids": [21, 27, 28, 41, 61, 81, 101, 51, 71, 91, 111,
                 42, 62, 82, 102, 52, 72, 92, 112,
                 43, 63, 83, 103, 53, 73, 93, 113,
                 44, 64, 84, 104, 54, 74, 94, 114,
                 45, 65, 85, 105, 55, 75, 95, 115,
                 121, 122, 123, 125, 126, 127, 137, 128,
                 13, 23, 238, 200, 201, 291, 293, 294, 295, 292],
    },

    # 3. 옵션
    "옵션체결": {  # 0O, 53 FIDs
        "fids": [20, 10, 11, 12, 27, 28, 15, 13, 14, 16, 17, 18, 195, 182, 186, 190, 191, 193, 192, 194, 181, 25, 26, 137, 187, 197, 246, 247, 248, 219, 196, 188, 189, 30, 391, 392, 393, 845, 848, 846, 849, 847, 850, 851, 1365, 1366, 1367, 305, 306, 228, 232, 234, 236],
    },
    "옵션호가잔량": {  # 0P, 61 FIDs
        "fids": [21, 27, 28, 41, 61, 81, 101, 51, 71, 91, 111,
                 42, 62, 82, 102, 52, 72, 92, 112,
                 43, 63, 83, 103, 53, 73, 93, 113,
                 44, 64, 84, 104, 54, 74, 94, 114,
                 45, 65, 85, 105, 55, 75, 95, 115,
                 121, 122, 123, 125, 126, 127, 137, 128,
                 13, 23, 238, 200, 201, 291, 293, 294, 295, 292],
    },

    # 4. 업종
    "업종지수": {  # 0J, 12 FIDs
        "fids": [20, 10, 11, 12, 15, 13, 14, 16, 17, 18, 25, 26],
    },
    "업종등락": {  # 0U, 14 FIDs
        "fids": [20, 252, 251, 253, 255, 254, 13, 14, 10, 11, 12, 256, 257, 25],
    },

    # 5. 티커/장시간
    "장시작시간": {  # 0s, 3 FIDs
        "fids": [215, 20, 214],
    },
    "상황/속보": {  # 0T, 12 FIDs
        "fids": [225, 777, 222, 223, 9001, 302, 224, 20, 22, 249, 250, 9407],
    },

    # 6. 조건검색
    "조건검색": {  # 02, 6 FIDs
        "fids": [841, 9001, 843, 20, 907, 9081],
    },
    "일반신호": {  # 03, 7 FIDs
        "fids": [841, 9001, 302, 907, 20, 840, 842],
    },

    # 주문체결 (00)
    "주문체결": {
        "fids": [9201, 9203, 9205, 9001, 912, 913, 302, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 10, 27, 28, 914, 915, 938, 939, 919, 920, 921, 922, 923, 949, 10010, 969, 819, 2134, 2135, 2136, 2137, 2138],
    },
    # 잔고변경 (01)
    "잔고변경": {
        "fids": [9201, 9001, 302, 10, 930, 931, 932, 933, 945, 946, 950, 951, 27, 28, 307, 8019, 397, 305, 306, 947],
    },
}


# ═══════════════════════════════════════════════════════
#  FID 이름 맵 (한글 매핑)
# ═══════════════════════════════════════════════════════

FID_NAMES = {
    10: "현재가", 11: "전일대비", 12: "등락율", 13: "누적거래량", 14: "거래대금",
    15: "체결량", 16: "시가", 17: "고가", 18: "저가", 20: "체결시간",
    21: "호가시간", 22: "호가/체결시간", 23: "전일거래량대비", 24: "전일거래량비율",
    25: "전일대비기호", 26: "체결가변동", 27: "매도호가1", 28: "매수호가1",
    29: "매도호가총잔량", 30: "매수호가총잔량", 31: "매도호가잔량변동", 32: "매수호가잔량변동",
    36: "NAV", 37: "NAV전일대비", 38: "NAV등락율", 39: "추적오차율",
    41: "매도호가1", 42: "매도호가2", 43: "매도호가3", 44: "매도호가4", 45: "매도호가5",
    46: "매도호가6", 47: "매도호가7", 48: "매도호가8", 49: "매도호가9", 50: "매도호가10",
    51: "매수호가1", 52: "매수호가2", 53: "매수호가3", 54: "매수호가4", 55: "매수호가5",
    56: "매수호가6", 57: "매수호가7", 58: "매수호가8", 59: "매수호가9", 60: "매수호가10",
    61: "매도잔량1", 62: "매도잔량2", 63: "매도잔량3", 64: "매도잔량4", 65: "매도잔량5",
    66: "매도잔량6", 67: "매도잔량7", 68: "매도잔량8", 69: "매도잔량9", 70: "매도잔량10",
    71: "매수잔량1", 72: "매수잔량2", 73: "매수잔량3", 74: "매수잔량4", 75: "매수잔량5",
    76: "매수잔량6", 77: "매수잔량7", 78: "매수잔량8", 79: "매수잔량9", 80: "매수잔량10",
    81: "매도건수1", 82: "매도건수2", 83: "매도건수3", 84: "매도건수4", 85: "매도건수5",
    86: "매도건수6", 87: "매도건수7", 88: "매도건수8", 89: "매도건수9", 90: "매도건수10",
    91: "매수건수1", 92: "매수건수2", 93: "매수건수3", 94: "매수건수4", 95: "매수건수5",
    96: "매수건수6", 97: "매수건수7", 98: "매수건수8", 99: "매수건수9", 100: "매수건수10",
    121: "매도총잔량", 122: "매수총잔량", 123: "매도총건수", 125: "매도총잔량변동", 126: "매수총잔량변동",
    127: "매수총건수", 128: "호가순잔량비율", 131: "시간외매도호가1", 132: "시간외매수호가1",
    135: "시간외매도잔량1", 136: "시간외매수잔량1", 137: "스프레드", 138: "회전율(매도)", 139: "회전율(매수)",
    182: "이론가", 183: "베이시스", 184: "미결제약정", 185: "KOSPI200", 186: "스프레드",
    187: "델타", 188: "시간가치", 189: "내재가치", 190: "행사가", 191: "ATM구분",
    192: "람다", 193: "카파", 194: "콜풋구분", 195: "정산가", 196: "로", 197: "내재변동성",
    200: "매도잔량대비", 201: "매수잔량대비", 214: "시각", 215: "장운영구분",
    219: "미결제변동", 222: "뉴스제목", 223: "뉴스본문", 224: "뉴스날짜", 225: "뉴스종류",
    228: "체결강도", 238: "호가순잔량비율",
    246: "감마", 247: "세타", 248: "베가", 249: "뉴스시간", 250: "뉴스링크",
    251: "보합", 252: "상승", 253: "하락", 254: "하한", 255: "상한", 256: "52주신고가", 257: "52주신저가",
    261: "매도거래원합", 262: "매수거래원합", 263: "외국인순수", 264: "기관순수",
    265: "NAV고가", 266: "NAV저가", 267: "매도순매수합", 268: "매수순매수합",
    290: "시가총액", 291: "프로그램매도", 292: "프로그램매수", 293: "프로그램순매도",
    294: "프로그램순매수", 295: "프로그램합계", 297: "PER", 299: "호가순잔량", 300: "외국인한도",
    302: "종목명", 305: "액면가", 306: "상장일", 307: "기준가", 311: "상장주식수",
    330: "수익률", 333: "거래량파워", 337: "시장알림", 370: "PBR", 382: "52주최고가대비",
    567: "거래시간1", 568: "거래시간2", 592: "EPS", 593: "ROE", 594: "BPS",
    620: "외국인순매수", 621: "LP매도잔량1", 631: "LP매수잔량1",
    689: "신용비율", 691: "외국인보유비율", 732: "시장경고",
    768: "LP보유비중", 769: "괴리율", 770: "괴리율부호", 777: "뉴스코드",
    822: "변동", 841: "조건식인덱스", 843: "조건식종목코드", 851: "예상체결가", 852: "정지",
    900: "주문수량", 901: "주문가격", 902: "미체결수량", 903: "체결누계금액",
    904: "원주문번호", 905: "주문구분", 906: "매매구분", 907: "매도수구분",
    908: "주문/체결시간", 909: "체결번호", 910: "체결가", 911: "체결량(주문)",
    912: "주문업무분류", 913: "주문상태", 914: "단위체결가", 915: "단위체결량",
    930: "보유수량", 931: "매입단가", 932: "총매입가", 933: "주문가능수량",
    938: "당일매매수수료", 939: "당일매매세금", 945: "당일순매수량", 946: "매도/매수구분",
    950: "당일총매도손익", 951: "예수금",
    1030: "프로그램매도금액", 1031: "프로그램매수금액", 1032: "프로그램순매수금액",
    1071: "프로그램매도건수", 1072: "프로그램매수건수",
    1261: "외국인순수(순매수)", 1263: "기관순수(순매수)", 1267: "프로그램순수(순매수)",
    1313: "투자자별매도", 1314: "투자자합계", 1315: "투자자별매수", 1316: "투자자별순매수",
    1491: "회전율", 1497: "외국인주문수량", 1498: "외국인주문금액",
    1890: "프로그램매도수량", 1891: "프로그램매수수량", 1892: "프로그램순매수수량",
    9001: "종목코드", 9076: "업종코드", 9081: "체결구분",
    9201: "계좌번호", 9203: "주문번호", 9205: "관리자사번",
    8019: "손익률",
}


class SCREEN:
    """Screen numbers for Kiwoom API calls."""

    LOGIN = "0000"
    TR_BASE = 1000
    REAL_BASE = 5000
    ORDER_BASE = 2000


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
    ACCOUNT_NO = 9201
    ORDER_NO = 9203
    ADMIN_NO = 9205
    CODE = 9001
    ORDER_CATEGORY = 912
    ORDER_STATUS = 913
    STOCK_NAME = 302
    ORDER_QTY = 900
    ORDER_PRICE = 901
    UNFILLED_QTY = 902
    EXEC_CUMUL_AMOUNT = 903
    ORG_ORDER_NO = 904
    ORDER_GUBUN = 905
    TRADE_GUBUN = 906
    SELL_BUY = 907
    ORDER_EXEC_TIME = 908
    EXEC_NO = 909
    EXEC_PRICE = 910
    EXEC_QTY = 911
    CURRENT_PRICE = 10
    BEST_ASK = 27
    BEST_BID = 28
    UNIT_EXEC_PRICE = 914
    UNIT_EXEC_QTY = 915
    DAY_COMMISSION = 938
    DAY_TAX = 939

    # --- gubun=1: 잔고통보 ---
    HOLDING_QTY = 930
    BUY_UNIT_PRICE = 931
    TOTAL_BUY_PRICE = 932
    ORDERABLE_QTY = 933
    DAY_NET_BUY_QTY = 945
    SELL_BUY_GUBUN = 946
    DAY_TOTAL_SELL_PNL = 950
    DEPOSIT = 951
    REFERENCE_PRICE = 307
    PNL_RATE = 8019


class OrderType:
    """nOrderType parameter for SendOrder."""

    NEW_BUY = 1
    NEW_SELL = 2
    CANCEL_BUY = 3
    CANCEL_SELL = 4
    MODIFY_BUY = 5
    MODIFY_SELL = 6


class HogaGb:
    """sHogaGb (거래구분) parameter for SendOrder."""

    LIMIT = "00"
    MARKET = "03"
    CONDITIONAL_LIMIT = "05"
    BEST_LIMIT = "06"
    FIRST_LIMIT = "07"
    LIMIT_IOC = "10"
    MARKET_IOC = "13"
    BEST_IOC = "16"
    LIMIT_FOK = "20"
    MARKET_FOK = "23"
    BEST_FOK = "26"
    PRE_MARKET_CLOSE = "61"
    AFTER_HOURS = "62"
    POST_MARKET_CLOSE = "81"


class ORDER_ERROR:
    """SendOrder and general API error codes."""

    SUCCESS = 0
    FAIL = -10
    LOGIN_FAIL = -100
    CONNECT_FAIL = -101
    VERSION_FAIL = -102
    FIREWALL_FAIL = -103
    MEMORY_FAIL = -104
    INPUT_FAIL = -105
    SOCKET_CLOSED = -106
    SISE_OVERFLOW = -200
    RQ_STRUCT_FAIL = -201
    RQ_STRING_FAIL = -202
    NO_DATA = -203
    OVER_MAX_DATA = -204
    DATA_RCV_FAIL = -205
    OVER_MAX_FID = -206
    REAL_CANCEL = -207
    ORD_WRONG_INPUT = -300
    ORD_WRONG_ACCTNO = -301
    OTHER_ACC_USE = -302
    MIS_2BILL_EXC = -303
    MIS_5BILL_EXC = -304
    MIS_1PER_EXC = -305
    MIS_3PER_EXC = -306
    SEND_FAIL = -307
    ORD_OVERFLOW = -308
    MIS_300CNT_EXC = -309
    MIS_500CNT_EXC = -310
    ORD_WRONG_ACCTINFO = -340
    ORD_SYMCODE_EMPTY = -500


class MarketState(Enum):
    """Market time-of-day states for trading control."""

    PRE_MARKET_AUCTION = auto()
    MARKET_OPEN_BUFFER = auto()
    TRADING = auto()
    CLOSING = auto()
    CLOSING_AUCTION = auto()
    CLOSED = auto()


class MarketOperation:
    """FID 215 장운영구분 values from Kiwoom API."""

    PRE_MARKET = "0"
    CLOSE_APPROACHING = "2"
    MARKET_OPEN = "3"
    MARKET_CLOSE_48 = "4"
    MARKET_CLOSE_9 = "9"
