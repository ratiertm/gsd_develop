"""키움 데이터 수집기 — 분봉 조회 + 실시간 수집 통합

로그인 → 과거 분봉 조회(opt10080) → 실시간 데이터 수집 → 18시 자동 종료

사용법 (Windows 32비트 Python):
    .venv32\\Scripts\\python.exe scripts/collector.py
    .venv32\\Scripts\\python.exe scripts/collector.py --interval 3 --days 5
    .venv32\\Scripts\\python.exe scripts/collector.py --skip-history   # 분봉 조회 건너뛰기
    .venv32\\Scripts\\python.exe scripts/collector.py --types 체결,호가  # 실시간 타입 선택

출력: data/ 폴더 (CSV + SQLite)
"""

import argparse
import csv
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwoom_trader.api.kiwoom_api import KiwoomAPI
from kiwoom_trader.api.event_handler import EventHandlerRegistry
from kiwoom_trader.api.tr_request_queue import TRRequestQueue
from kiwoom_trader.config.constants import FID, FID_NAMES, REALTIME_FIDS


# ═══════════════════════════════════════════════════════
#  설정
# ═══════════════════════════════════════════════════════

WATCH_LIST = {
    "005930": "삼성전자",
    "005380": "현대차",
    "000660": "SK하이닉스",
}

# 시장 지수 (업종지수 실시간)
INDEX_LIST = {
    "001": "코스피",
    "101": "코스닥",
}

COLLECT_TYPES = {
    "체결": {"real_type": "주식체결", "fids": REALTIME_FIDS["주식체결"]["fids"]},
    "호가": {"real_type": "주식호가잔량", "fids": REALTIME_FIDS["주식호가잔량"]["fids"]},
    "거래원": {"real_type": "주식당일거래원", "fids": REALTIME_FIDS["주식당일거래원"]["fids"]},
    "시간외": {"real_type": "주식시간외체결", "fids": REALTIME_FIDS["주식시간외체결"]["fids"]},
    "종목정보": {"real_type": "주식종목정보", "fids": REALTIME_FIDS["주식종목정보"]["fids"]},
    "장시작": {"real_type": "장시작시간", "fids": REALTIME_FIDS["장시작시간"]["fids"]},
    "업종지수": {"real_type": "업종지수", "fids": REALTIME_FIDS["업종지수"]["fids"]},
    "업종등락": {"real_type": "업종등락", "fids": REALTIME_FIDS["업종등락"]["fids"]},
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
TODAY = datetime.now().strftime("%Y%m%d")


# ═══════════════════════════════════════════════════════
#  Phase 1: 분봉 조회기
# ═══════════════════════════════════════════════════════

class MinuteCandleFetcher:
    """opt10080으로 분봉 데이터 조회 후 저장. 완료되면 on_done 콜백 호출."""

    def __init__(self, api, event_registry, tr_queue,
                 codes, interval=1, days=3, on_done=None):
        self.api = api
        self.event_registry = event_registry
        self.tr_queue = tr_queue
        self.codes = codes
        self.interval = interval
        self.days = days
        self.on_done = on_done

        self._current_idx = 0
        self._current_code = ""
        self._candles = []
        self._prev_next = 0
        self._page = 0
        self._total_saved = 0
        self._cutoff = datetime.now() - timedelta(days=days)

        # SQLite
        db_path = DATA_DIR / f"minute_{interval}m_{TODAY}.db"
        self.db_conn = sqlite3.connect(str(db_path))
        self.db_conn.execute("PRAGMA journal_mode=WAL")
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                datetime TEXT NOT NULL,
                open INTEGER, high INTEGER, low INTEGER, close INTEGER,
                volume INTEGER,
                UNIQUE(code, datetime)
            )
        """)
        self.db_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_candles_code_dt ON candles(code, datetime)"
        )
        self.db_conn.commit()

        # CSV
        self.csv_path = DATA_DIR / f"minute_{interval}m_{TODAY}.csv"
        file_exists = self.csv_path.exists()
        self._csv_file = open(self.csv_path, "a", newline="", encoding="utf-8")
        self._csv_writer = csv.writer(self._csv_file)
        if not file_exists:
            self._csv_writer.writerow(
                ["code", "name", "datetime", "open", "high", "low", "close", "volume"]
            )
            self._csv_file.flush()

    def start(self):
        logger.info(f"=== 분봉 조회 시작 ({self.interval}분봉, 최근 {self.days}일) ===")
        self._fetch_next_code()

    def _fetch_next_code(self):
        if self._current_idx >= len(self.codes):
            self._finish()
            return

        self._current_code = self.codes[self._current_idx]
        self._candles = []
        self._prev_next = 0
        self._page = 0
        name = WATCH_LIST.get(self._current_code, self._current_code)
        logger.info(f"  조회: {name} ({self._current_code})")
        self._request()

    def _request(self):
        rq_name = f"분봉_{self._current_code}_{self._page}"
        self.event_registry.register_tr_handler(rq_name, self._on_response)
        self.tr_queue.enqueue(
            tr_code="opt10080",
            rq_name=rq_name,
            screen_no="4010",
            inputs={"종목코드": self._current_code, "틱범위": str(self.interval), "수정주가구분": "1"},
            prev_next=self._prev_next,
        )

    def _on_response(self, *args):
        has_next = str(args[4]) == "2" if len(args) > 4 else False
        count = self.api.get_repeat_cnt("opt10080", "주식분봉차트조회")

        if count == 0:
            self._save_and_next()
            return

        oldest_dt = None
        hit_cutoff = False
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

            if dt < self._cutoff:
                hit_cutoff = True
                break

            oldest_dt = dt
            self._candles.append((
                self._current_code,
                WATCH_LIST.get(self._current_code, ""),
                dt.strftime("%Y-%m-%d %H:%M:%S"),
                open_p, high, low, close, volume,
            ))

        self._page += 1
        name = WATCH_LIST.get(self._current_code, self._current_code)
        logger.info(f"    page {self._page}: +{count}건 (누적 {len(self._candles)})")

        if has_next and not hit_cutoff:
            self._prev_next = 2
            QTimer.singleShot(100, self._request)
        else:
            self._save_and_next()

    def _save_and_next(self):
        name = WATCH_LIST.get(self._current_code, self._current_code)
        if self._candles:
            self.db_conn.executemany(
                "INSERT OR IGNORE INTO candles "
                "(code, name, datetime, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                self._candles,
            )
            self.db_conn.commit()
            for row in self._candles:
                self._csv_writer.writerow(row)
            self._csv_file.flush()
            self._total_saved += len(self._candles)
            logger.info(f"  {name} 저장: {len(self._candles)}건")

        self._current_idx += 1
        QTimer.singleShot(500, self._fetch_next_code)

    def _finish(self):
        self._csv_file.close()
        self.db_conn.close()
        logger.info(f"=== 분봉 조회 완료: 총 {self._total_saved}건 ===")
        logger.info(f"  DB:  {DATA_DIR / f'minute_{self.interval}m_{TODAY}.db'}")
        logger.info(f"  CSV: {self.csv_path}")
        if self.on_done:
            self.on_done()


# ═══════════════════════════════════════════════════════
#  Phase 2: 실시간 수집기
# ═══════════════════════════════════════════════════════

class RealtimeCollector:
    """실시간 데이터 수집. start()로 등록, 18시 자동 종료."""

    def __init__(self, api, collect_types=None):
        self.api = api
        self.tick_counts = {}
        self.csv_writers = {}
        self.csv_files = {}

        if collect_types:
            self.active_types = {k: v for k, v in COLLECT_TYPES.items() if k in collect_types}
        else:
            self.active_types = COLLECT_TYPES

        # SQLite
        db_path = DATA_DIR / f"realtime_{TODAY}.db"
        self.db_conn = sqlite3.connect(str(db_path))
        self.db_conn.execute("PRAGMA journal_mode=WAL")
        self.db_conn.execute("PRAGMA synchronous=NORMAL")

        for type_name, type_info in self.active_types.items():
            fids = type_info["fids"]
            fid_cols = [f"fid_{fid}" for fid in fids]

            # CSV
            csv_path = DATA_DIR / f"{type_name}_{TODAY}.csv"
            file_exists = csv_path.exists()
            f = open(csv_path, "a", newline="", encoding="utf-8")
            fields = ["timestamp", "code", "name", "real_type"] + fid_cols
            writer = csv.DictWriter(f, fieldnames=fields)
            if not file_exists:
                writer.writerow({
                    "timestamp": "# FID이름", "code": "", "name": "", "real_type": "",
                    **{f"fid_{fid}": FID_NAMES.get(fid, f"FID{fid}") for fid in fids},
                })
                writer.writeheader()
                f.flush()
            self.csv_writers[type_name] = writer
            self.csv_files[type_name] = f
            self.tick_counts[type_name] = 0

            # SQLite 테이블
            col_defs = ", ".join([f"fid_{fid} TEXT" for fid in fids])
            self.db_conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {type_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL, code TEXT NOT NULL,
                    name TEXT, real_type TEXT, {col_defs}
                )
            """)
            self.db_conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{type_name}_code_ts
                ON {type_name}(code, timestamp)
            """)
        self.db_conn.commit()

        # 실시간 이벤트 연결
        self.api.real_data_received.connect(self._on_real_data)

    def start(self):
        """실시간 등록."""
        logger.info("=== 실시간 수집 시작 ===")
        codes = ";".join(WATCH_LIST.keys())
        all_fids = set()
        for type_info in self.active_types.values():
            all_fids.update(type_info["fids"])

        fid_str = ";".join(str(f) for f in sorted(all_fids))
        self.api.set_real_reg("5000", codes, fid_str, "0")
        logger.info(f"실시간 등록: {list(WATCH_LIST.values())} | FID {len(all_fids)}개")

        # 시장 지수 별도 화면으로 등록
        if INDEX_LIST:
            index_codes = ";".join(INDEX_LIST.keys())
            index_fids = set()
            for t in ["업종지수", "업종등락"]:
                if t in self.active_types:
                    index_fids.update(self.active_types[t]["fids"])
            if index_fids:
                idx_fid_str = ";".join(str(f) for f in sorted(index_fids))
                self.api.set_real_reg("5001", index_codes, idx_fid_str, "0")
                logger.info(f"지수 등록: {list(INDEX_LIST.values())} | FID {len(index_fids)}개")

        logger.info(f"수집 타입: {list(self.active_types.keys())}")
        logger.info("데이터 수신 대기중... (18시 자동 종료)")

    def _on_real_data(self, code, real_type, real_data):
        # 종목 또는 지수 코드만 수신
        all_known = {**WATCH_LIST, **INDEX_LIST}
        if code not in all_known:
            return

        matched = None
        for type_name, type_info in self.active_types.items():
            if type_info["real_type"] == real_type:
                matched = type_name
                break
        if matched is None:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        fids = self.active_types[matched]["fids"]

        fid_data = {}
        for fid in fids:
            raw = self.api.get_comm_real_data(code, fid)
            fid_data[f"fid_{fid}"] = raw.strip() if raw else ""

        # CSV
        row = {"timestamp": now, "code": code, "name": all_known[code],
               "real_type": real_type, **fid_data}
        self.csv_writers[matched].writerow(row)
        self.tick_counts[matched] += 1

        # SQLite
        cols = ["timestamp", "code", "name", "real_type"] + [f"fid_{fid}" for fid in fids]
        vals = [now, code, all_known[code], real_type] + [fid_data[f"fid_{fid}"] for fid in fids]
        self.db_conn.execute(
            f"INSERT INTO {matched} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})", vals
        )

        # 50틱마다 flush
        total = sum(self.tick_counts.values())
        if total % 50 == 0:
            for f in self.csv_files.values():
                f.flush()
            self.db_conn.commit()
            price = fid_data.get(f"fid_{FID.CURRENT_PRICE}", "?")
            logger.info(f"[{total}틱] {matched} | {all_known[code]} 현재가={price}")

    def cleanup(self):
        for f in self.csv_files.values():
            f.flush()
            f.close()
        if self.db_conn:
            self.db_conn.commit()
            self.db_conn.close()
        total = sum(self.tick_counts.values())
        logger.info(f"실시간 수집 종료: 총 {total}틱")
        for name, cnt in self.tick_counts.items():
            if cnt > 0:
                logger.info(f"  {name}: {cnt}틱")

    def print_status(self):
        total = sum(self.tick_counts.values())
        parts = [f"{k}={v}" for k, v in self.tick_counts.items() if v > 0]
        if parts:
            logger.info(f"[상태] 총 {total}틱 | {' | '.join(parts)}")


# ═══════════════════════════════════════════════════════
#  메인
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="키움 데이터 수집기 (분봉 조회 + 실시간)")
    parser.add_argument("--interval", type=int, default=1, help="분봉 간격 (1,3,5,10,15,30,60)")
    parser.add_argument("--days", type=int, default=3, help="분봉 조회 기간 (일)")
    parser.add_argument("--codes", type=str, default=None, help="종목코드 (쉼표 구분)")
    parser.add_argument("--types", type=str, default=None, help="실시간 타입 (쉼표 구분)")
    parser.add_argument("--skip-history", action="store_true", help="분봉 조회 건너뛰기")
    args = parser.parse_args()

    codes = list(WATCH_LIST.keys())
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",")]

    collect_types = None
    if args.types:
        collect_types = [t.strip() for t in args.types.split(",")]

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {message}")
    logger.add(DATA_DIR / f"collector_{TODAY}.log", level="DEBUG", rotation="10 MB")

    app = QApplication(sys.argv)

    # 공유 API 인스턴스
    api = KiwoomAPI()
    event_registry = EventHandlerRegistry()
    tr_queue = TRRequestQueue(api, interval_ms=4000)
    api.tr_data_received.connect(
        lambda *a: event_registry.handle_tr_data(a[1], *a)
    )

    # 실시간 수집기 (로그인 후 분봉 완료 시 시작)
    realtime = RealtimeCollector(api, collect_types)

    def start_realtime():
        realtime.start()

    # 분봉 조회기
    fetcher = None
    if not args.skip_history:
        fetcher = MinuteCandleFetcher(
            api, event_registry, tr_queue,
            codes=codes, interval=args.interval, days=args.days,
            on_done=start_realtime,
        )

    def on_login(err_code):
        if err_code != 0:
            logger.error(f"로그인 실패: {err_code}")
            return

        user = api.get_login_info("USER_NAME")
        server_type = api.get_login_info("GetServerGubun")
        server = "모의투자" if server_type == "1" else "실거래"
        logger.info(f"로그인 성공: {user} | {server}")

        if fetcher:
            fetcher.start()
        else:
            start_realtime()

    api.connected.connect(on_login)

    # 주기적 체크 (상태 + 18시 종료 + DB 커밋)
    def periodic():
        now = datetime.now()
        if now.hour >= 18:
            logger.info("18:00 — 자동 종료")
            realtime.cleanup()
            app.quit()
            return
        if now.minute % 5 == 0 and now.second < 10:
            realtime.print_status()

    timer = QTimer()
    timer.timeout.connect(periodic)
    timer.start(10_000)

    commit_timer = QTimer()
    commit_timer.timeout.connect(
        lambda: realtime.db_conn.commit() if realtime.db_conn else None
    )
    commit_timer.start(5_000)

    app.aboutToQuit.connect(realtime.cleanup)

    logger.info("로그인 시도...")
    api.comm_connect()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
