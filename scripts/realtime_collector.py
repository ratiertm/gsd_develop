"""실시간 데이터 수집기 — nkrealtime.dat 전체 구조 기반

삼성전자(005930), 현대차(005380), SK하이닉스(000660)
체결 + 호가 + 거래원 + 프로그램매매 전체 수집

사용법 (Windows 32비트 Python):
    python scripts/realtime_collector.py
    python scripts/realtime_collector.py --types 체결         # 체결만
    python scripts/realtime_collector.py --types 체결,호가    # 체결+호가

출력: data/ 폴더 (CSV + SQLite)
"""

import argparse
import csv
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwoom_trader.api.kiwoom_api import KiwoomAPI
from kiwoom_trader.config.constants import FID, FID_NAMES, REALTIME_FIDS


# ── 설정 ──────────────────────────────────────────────
WATCH_LIST = {
    "005930": "삼성전자",
    "005380": "현대차",
    "000660": "SK하이닉스",
}

# 수집 대상 실시간 타입
COLLECT_TYPES = {
    "체결": {
        "real_type": "주식체결",
        "fids": REALTIME_FIDS["주식체결"]["fids"],
    },
    "호가": {
        "real_type": "주식호가잔량",
        "fids": REALTIME_FIDS["주식호가잔량"]["fids"],
    },
    "거래원": {
        "real_type": "주식당일거래원",
        "fids": REALTIME_FIDS["주식당일거래원"]["fids"],
    },
    "시간외": {
        "real_type": "주식시간외체결",
        "fids": REALTIME_FIDS["주식시간외체결"]["fids"],
    },
    "종목정보": {
        "real_type": "주식종목정보",
        "fids": REALTIME_FIDS["주식종목정보"]["fids"],
    },
    "장시작": {
        "real_type": "장시작시간",
        "fids": REALTIME_FIDS["장시작시간"]["fids"],
    },
}

# 출력 경로
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
TODAY = datetime.now().strftime("%Y%m%d")


class RealtimeCollector:
    def __init__(self, collect_types=None):
        self.api = KiwoomAPI()
        self.tick_counts = {}
        self.csv_writers = {}
        self.csv_files = {}
        self.db_conn = None

        # 수집할 타입 결정
        if collect_types:
            self.active_types = {k: v for k, v in COLLECT_TYPES.items() if k in collect_types}
        else:
            self.active_types = COLLECT_TYPES

        self._init_storage()

        # 이벤트 연결
        self.api.connected.connect(self._on_login)
        self.api.real_data_received.connect(self._on_real_data)

    def _init_storage(self):
        """CSV + SQLite 초기화"""
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
                # 헤더에 FID 이름도 같이 기록
                writer.writerow({
                    "timestamp": "# FID이름",
                    "code": "",
                    "name": "",
                    "real_type": "",
                    **{f"fid_{fid}": FID_NAMES.get(fid, f"FID{fid}") for fid in fids}
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
                    timestamp TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    real_type TEXT,
                    {col_defs}
                )
            """)
            # 인덱스
            self.db_conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{type_name}_code_ts
                ON {type_name}(code, timestamp)
            """)

        self.db_conn.commit()
        logger.info(f"저장소 초기화 완료: {DATA_DIR}")
        logger.info(f"수집 타입: {list(self.active_types.keys())}")

    def start(self):
        logger.info("로그인 시도...")
        self.api.comm_connect()

    def _on_login(self, err_code):
        if err_code != 0:
            logger.error(f"로그인 실패: {err_code}")
            return

        user = self.api.get_login_info("USER_NAME")
        acct = self.api.get_login_info("ACCNO")
        key_type = self.api.get_login_info("KEY_BSECGB")
        server = "모의투자" if key_type == "0" else "실거래"
        logger.info(f"로그인 성공: {user} | 계좌: {acct} | {server}")

        # 실시간 등록 — 타입별 FID 통합
        codes = ";".join(WATCH_LIST.keys())
        all_fids = set()
        for type_info in self.active_types.values():
            all_fids.update(type_info["fids"])

        fid_str = ";".join(str(f) for f in sorted(all_fids))
        self.api.set_real_reg("5000", codes, fid_str, "0")
        logger.info(f"실시간 등록: {codes} | FID {len(all_fids)}개")
        logger.info("데이터 수신 대기중...")

    def _on_real_data(self, code, real_type, real_data):
        if code not in WATCH_LIST:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # real_type에 맞는 수집 타입 찾기
        matched = None
        for type_name, type_info in self.active_types.items():
            if type_info["real_type"] == real_type:
                matched = type_name
                break

        if matched is None:
            return

        fids = self.active_types[matched]["fids"]

        # FID 데이터 추출
        fid_data = {}
        for fid in fids:
            raw = self.api.get_comm_real_data(code, fid)
            fid_data[f"fid_{fid}"] = raw.strip() if raw else ""

        # CSV 기록
        row = {
            "timestamp": now,
            "code": code,
            "name": WATCH_LIST[code],
            "real_type": real_type,
            **fid_data,
        }
        self.csv_writers[matched].writerow(row)
        self.tick_counts[matched] += 1

        # SQLite 기록
        cols = ["timestamp", "code", "name", "real_type"] + [f"fid_{fid}" for fid in fids]
        vals = [now, code, WATCH_LIST[code], real_type] + [fid_data[f"fid_{fid}"] for fid in fids]
        placeholders = ",".join(["?"] * len(cols))
        col_names = ",".join(cols)
        self.db_conn.execute(f"INSERT INTO {matched} ({col_names}) VALUES ({placeholders})", vals)

        # 50틱마다 flush
        total = sum(self.tick_counts.values())
        if total % 50 == 0:
            for f in self.csv_files.values():
                f.flush()
            self.db_conn.commit()

            price = fid_data.get(f"fid_{FID.CURRENT_PRICE}", "?")
            vol = fid_data.get(f"fid_{FID.VOLUME}", "?")
            logger.info(
                f"[{total}틱] {matched} | {WATCH_LIST[code]} "
                f"현재가={price} 거래량={vol}"
            )

    def cleanup(self):
        for f in self.csv_files.values():
            f.flush()
            f.close()
        if self.db_conn:
            self.db_conn.commit()
            self.db_conn.close()
        total = sum(self.tick_counts.values())
        logger.info(f"수집 완료: 총 {total}틱")
        for name, cnt in self.tick_counts.items():
            logger.info(f"  {name}: {cnt}틱")
        logger.info(f"저장: {DATA_DIR}")

    def print_status(self):
        """주기적 상태 출력"""
        total = sum(self.tick_counts.values())
        parts = [f"{k}={v}" for k, v in self.tick_counts.items() if v > 0]
        if parts:
            logger.info(f"[상태] 총 {total}틱 | {' | '.join(parts)}")


def main():
    parser = argparse.ArgumentParser(description="키움 실시간 데이터 수집기")
    parser.add_argument(
        "--types", type=str, default=None,
        help="수집 타입 (쉼표 구분): 체결,호가,거래원,시간외,종목정보,장시작"
    )
    args = parser.parse_args()

    collect_types = None
    if args.types:
        collect_types = [t.strip() for t in args.types.split(",")]

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {message}")
    logger.add(
        DATA_DIR / f"collector_{TODAY}.log",
        level="DEBUG",
        rotation="10 MB",
    )

    app = QApplication(sys.argv)
    collector = RealtimeCollector(collect_types)

    # 장 종료 체크 + 상태 출력
    def periodic_check():
        now = datetime.now()
        # 18:00 이후 자동 종료
        if now.hour >= 18:
            logger.info("18:00 — 자동 종료")
            collector.cleanup()
            app.quit()
            return
        # 5분마다 상태 출력
        if now.minute % 5 == 0 and now.second < 10:
            collector.print_status()

    timer = QTimer()
    timer.timeout.connect(periodic_check)
    timer.start(10_000)  # 10초마다

    # DB 주기적 커밋
    def db_commit():
        if collector.db_conn:
            collector.db_conn.commit()

    commit_timer = QTimer()
    commit_timer.timeout.connect(db_commit)
    commit_timer.start(5_000)  # 5초마다 커밋

    app.aboutToQuit.connect(collector.cleanup)
    collector.start()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
