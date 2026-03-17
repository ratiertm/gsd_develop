"""키움 API로 분봉 데이터 조회 + 저장

opt10080 (주식분봉차트조회) 사용.
삼성전자, 현대차, SK하이닉스 최근 N일 분봉 데이터를 SQLite + CSV로 저장.

사용법 (Windows 32비트 Python):
    .venv32\\Scripts\\python.exe scripts/fetch_minute_candles.py
    .venv32\\Scripts\\python.exe scripts/fetch_minute_candles.py --interval 3 --days 5
    .venv32\\Scripts\\python.exe scripts/fetch_minute_candles.py --codes 005930
"""

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwoom_trader.api.kiwoom_api import KiwoomAPI
from kiwoom_trader.api.event_handler import EventHandlerRegistry
from kiwoom_trader.api.tr_request_queue import TRRequestQueue


# ── 설정 ──────────────────────────────────────────────
STOCK_MAP = {
    "005930": "삼성전자",
    "005380": "현대차",
    "000660": "SK하이닉스",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
TODAY = datetime.now().strftime("%Y%m%d")

CANDLE_FIELDS = ["체결시간", "현재가", "시가", "고가", "저가", "거래량"]


class MinuteCandleFetcher:
    """opt10080으로 분봉 데이터 조회 후 저장."""

    def __init__(self, codes: list[str], interval: int = 1, days: int = 3):
        self.codes = codes
        self.interval = interval  # 분봉 간격 (1, 3, 5, 10, 15, 30, 60)
        self.days = days

        self.api = KiwoomAPI()
        self.event_registry = EventHandlerRegistry()
        self.tr_queue = TRRequestQueue(self.api, interval_ms=4000)

        # TR 응답 연결
        self.api.tr_data_received.connect(
            lambda *args: self.event_registry.handle_tr_data(args[1], *args)
        )
        self.api.connected.connect(self._on_login)

        # 상태
        self._current_code_idx = 0
        self._current_code = ""
        self._candles = []  # 현재 종목 분봉
        self._prev_next = 0
        self._page = 0
        self._total_saved = 0

        # 저장소
        db_path = DATA_DIR / f"minute_{interval}m_{TODAY}.db"
        self.db_conn = sqlite3.connect(str(db_path))
        self.db_conn.execute("PRAGMA journal_mode=WAL")
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                datetime TEXT NOT NULL,
                open INTEGER,
                high INTEGER,
                low INTEGER,
                close INTEGER,
                volume INTEGER,
                UNIQUE(code, datetime)
            )
        """)
        self.db_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_candles_code_dt
            ON candles(code, datetime)
        """)
        self.db_conn.commit()

        self.csv_path = DATA_DIR / f"minute_{interval}m_{TODAY}.csv"
        self._csv_file = None
        self._csv_writer = None

    def start(self):
        logger.info("로그인 시도...")
        self.api.comm_connect()

    def _on_login(self, err_code):
        if err_code != 0:
            logger.error(f"로그인 실패: {err_code}")
            return

        user = self.api.get_login_info("USER_NAME")
        server_type = self.api.get_login_info("GetServerGubun")
        server = "모의투자" if server_type == "1" else "실거래"
        logger.info(f"로그인 성공: {user} | {server}")

        # CSV 초기화
        file_exists = self.csv_path.exists()
        self._csv_file = open(self.csv_path, "a", newline="", encoding="utf-8")
        self._csv_writer = csv.writer(self._csv_file)
        if not file_exists:
            self._csv_writer.writerow(
                ["code", "name", "datetime", "open", "high", "low", "close", "volume"]
            )
            self._csv_file.flush()

        # 첫 종목부터 조회 시작
        self._fetch_next_code()

    def _fetch_next_code(self):
        """다음 종목 분봉 조회 시작."""
        if self._current_code_idx >= len(self.codes):
            self._finish()
            return

        self._current_code = self.codes[self._current_code_idx]
        self._candles = []
        self._prev_next = 0
        self._page = 0
        name = STOCK_MAP.get(self._current_code, self._current_code)
        logger.info(f"조회 시작: {name} ({self._current_code}) {self.interval}분봉")
        self._request_candles()

    def _request_candles(self):
        """opt10080 TR 요청."""
        rq_name = f"분봉_{self._current_code}_{self._page}"

        # TR 핸들러 등록 (매번 갱신)
        self.event_registry.register_tr_handler(
            rq_name, self._on_tr_response
        )

        inputs = {
            "종목코드": self._current_code,
            "틱범위": str(self.interval),
            "수정주가구분": "1",
        }
        self.tr_queue.enqueue(
            tr_code="opt10080",
            rq_name=rq_name,
            screen_no="4010",
            inputs=inputs,
            prev_next=self._prev_next,
        )

    def _on_tr_response(self, *args):
        """opt10080 응답 파싱."""
        # args: screen_no, rq_name, tr_code, record_name, prev_next, data_len, err_code, msg1, msg2
        prev_next_str = args[4] if len(args) > 4 else "0"
        has_next = str(prev_next_str) == "2"

        count = self.api.get_repeat_cnt("opt10080", "주식분봉차트조회")
        if count == 0:
            logger.info(f"  {self._current_code} 데이터 없음 (page {self._page})")
            self._save_and_next()
            return

        # 날짜 필터 기준
        cutoff = datetime.now()
        try:
            from datetime import timedelta
            cutoff_start = cutoff - timedelta(days=self.days)
        except Exception:
            cutoff_start = None

        oldest_dt = None
        new_count = 0
        for i in range(count):
            dt_str = self.api.get_comm_data("opt10080", "주식분봉차트조회", i, "체결시간").strip()
            close = abs(int(self.api.get_comm_data("opt10080", "주식분봉차트조회", i, "현재가").strip() or "0"))
            open_p = abs(int(self.api.get_comm_data("opt10080", "주식분봉차트조회", i, "시가").strip() or "0"))
            high = abs(int(self.api.get_comm_data("opt10080", "주식분봉차트조회", i, "고가").strip() or "0"))
            low = abs(int(self.api.get_comm_data("opt10080", "주식분봉차트조회", i, "저가").strip() or "0"))
            volume = abs(int(self.api.get_comm_data("opt10080", "주식분봉차트조회", i, "거래량").strip() or "0"))

            try:
                dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            except ValueError:
                continue

            # 날짜 필터
            if cutoff_start and dt < cutoff_start:
                oldest_dt = dt
                break

            oldest_dt = dt
            self._candles.append({
                "code": self._current_code,
                "name": STOCK_MAP.get(self._current_code, ""),
                "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "open": open_p,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            })
            new_count += 1

        self._page += 1
        name = STOCK_MAP.get(self._current_code, self._current_code)
        logger.info(
            f"  {name} page {self._page}: {new_count}건 "
            f"(누적 {len(self._candles)}건, 최고 ~{oldest_dt})"
        )

        # 계속 조회할지 결정
        if has_next and (cutoff_start is None or (oldest_dt and oldest_dt >= cutoff_start)):
            self._prev_next = 2
            # 다음 페이지 요청 (TR 큐가 4초 간격 보장)
            QTimer.singleShot(100, self._request_candles)
        else:
            self._save_and_next()

    def _save_and_next(self):
        """현재 종목 데이터 저장 후 다음 종목으로."""
        name = STOCK_MAP.get(self._current_code, self._current_code)

        if self._candles:
            # SQLite 저장
            for c in self._candles:
                try:
                    self.db_conn.execute(
                        "INSERT OR IGNORE INTO candles "
                        "(code, name, datetime, open, high, low, close, volume) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (c["code"], c["name"], c["datetime"],
                         c["open"], c["high"], c["low"], c["close"], c["volume"]),
                    )
                except sqlite3.Error as e:
                    logger.warning(f"DB insert error: {e}")
            self.db_conn.commit()

            # CSV 저장
            for c in self._candles:
                self._csv_writer.writerow([
                    c["code"], c["name"], c["datetime"],
                    c["open"], c["high"], c["low"], c["close"], c["volume"],
                ])
            self._csv_file.flush()

            self._total_saved += len(self._candles)
            logger.info(f"  {name} 저장 완료: {len(self._candles)}건")
        else:
            logger.warning(f"  {name} 저장할 데이터 없음")

        # 다음 종목
        self._current_code_idx += 1
        QTimer.singleShot(500, self._fetch_next_code)

    def _finish(self):
        """전체 완료."""
        if self._csv_file:
            self._csv_file.close()
        self.db_conn.close()

        logger.info("=" * 50)
        logger.info(f"전체 조회 완료: {self._total_saved}건")
        logger.info(f"SQLite: {DATA_DIR / f'minute_{self.interval}m_{TODAY}.db'}")
        logger.info(f"CSV:    {self.csv_path}")
        logger.info("=" * 50)

        QApplication.instance().quit()


def main():
    parser = argparse.ArgumentParser(description="키움 분봉 데이터 조회기")
    parser.add_argument("--interval", type=int, default=1, help="분봉 간격 (1,3,5,10,15,30,60)")
    parser.add_argument("--days", type=int, default=3, help="조회 기간 (일)")
    parser.add_argument("--codes", type=str, default=None, help="종목코드 (쉼표 구분)")
    args = parser.parse_args()

    codes = list(STOCK_MAP.keys())
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",")]

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {message}")
    logger.add(DATA_DIR / f"fetch_{TODAY}.log", level="DEBUG")

    app = QApplication(sys.argv)
    fetcher = MinuteCandleFetcher(codes, interval=args.interval, days=args.days)
    fetcher.start()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
