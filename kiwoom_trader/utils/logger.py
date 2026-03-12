"""Multi-sink loguru configuration for KiwoomDayTrader."""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_dir: str = "logs"):
    """Configure loguru with purpose-specific daily-rotated log files.

    Sinks:
    1. Console (stderr) - INFO level
    2. System log - DEBUG level, 30-day retention, default log_type
    3. Trade log - INFO level, 365-day retention, log_type="trade"
    4. Error log - WARNING level, 90-day retention, includes exception info
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console output
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level:<8} | {message}",
    )

    # System log: general application events
    logger.add(
        log_path / "system-{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        filter=lambda record: record["extra"].get("log_type", "system") == "system",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {module}:{function}:{line} | {message}",
    )

    # Trade log: order/execution events only
    logger.add(
        log_path / "trade-{time:YYYY-MM-DD}.log",
        level="INFO",
        rotation="00:00",
        retention="365 days",
        filter=lambda record: record["extra"].get("log_type") == "trade",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}",
    )

    # Error log: warnings and above
    logger.add(
        log_path / "error-{time:YYYY-MM-DD}.log",
        level="WARNING",
        rotation="00:00",
        retention="90 days",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {module}:{function}:{line} | {message}\n{exception}",
    )
