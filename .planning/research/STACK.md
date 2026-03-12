# Stack Research

**Domain:** Kiwoom Securities OpenAPI+ Automated Day-Trading System (Python/Windows)
**Researched:** 2026-03-13
**Confidence:** MEDIUM -- WebSearch/WebFetch/Bash unavailable; versions based on training data (cutoff May 2025). Verify all version numbers before installing.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.10.x | Runtime language | 3.10 is the sweet spot for Kiwoom OpenAPI+ compatibility. 3.11+ has issues with some COM interop and 32-bit requirement. Kiwoom OCX is 32-bit, so **32-bit Python is mandatory**. |
| PyQt5 | 5.15.x | GUI framework + COM bridge | Kiwoom OpenAPI+ is a Windows COM/OCX control. PyQt5's QAxWidget is the only reliable way to host the OCX in Python. This is not optional -- it is the connectivity layer. PyQt6 dropped QAxWidget support for COM. |
| pykiwoom | 0.1.x | Kiwoom API wrapper | Simplifies TR request/response patterns, login flow, and real-time data subscription. Built on PyQt5's QAxWidget. Reduces boilerplate significantly. |
| pandas | 2.1.x+ | Data manipulation | Industry standard for time-series financial data. OHLCV candle data, portfolio tracking, backtest result analysis all use DataFrame operations. |
| SQLite (via sqlite3) | built-in | Local database | Zero-config persistent storage for trade logs, strategy configs, historical candle data cache. No external DB server needed for a single-user desktop app. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ta (Technical Analysis) | 0.11.x | Technical indicators | RSI, MACD, Bollinger Bands, SMA/EMA, etc. Pure Python, no C dependency. Use this over TA-Lib for simpler installation. |
| numpy | 1.26.x+ | Numerical computation | Underlying array operations for pandas and indicator calculations. Installed as pandas dependency. |
| matplotlib | 3.8.x+ | Charting/plotting | Backtest result visualization, equity curves, drawdown charts. Integrates with PyQt5 via matplotlib.backends.backend_qt5agg. |
| pyqtgraph | 0.13.x | Real-time charting | Live candlestick charts and real-time price plotting in the GUI. Much faster than matplotlib for real-time updates. |
| requests | 2.31.x+ | HTTP client | Discord webhook notifications, external data API calls. |
| schedule | 1.2.x | Task scheduling | Market open/close routines, periodic health checks. Simpler than APScheduler for this use case. |
| loguru | 0.7.x | Logging | Structured logging with rotation, better than stdlib logging. Trade execution logs are critical for debugging and audit. |
| pyyaml | 6.0.x | Configuration | Strategy parameter files in YAML format. More readable than JSON for trading strategy configs with comments. |
| pyinstaller | 6.x | Packaging | Bundle into standalone .exe for distribution. Optional but useful for deployment. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Unit/integration testing | Test strategy logic, order management, indicator calculations in isolation |
| black | Code formatting | Consistent formatting across the codebase |
| mypy | Type checking | Catch type errors early; trading systems need reliability |
| ruff | Linting | Fast Python linter, replaces flake8+isort+pyflakes |
| pre-commit | Git hooks | Run black/ruff/mypy before each commit |

## Installation

```bash
# IMPORTANT: Must use 32-bit Python 3.10.x on Windows
# Download from https://www.python.org/downloads/ -- select "Windows installer (32-bit)"

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Core -- Kiwoom connectivity + GUI
pip install PyQt5==5.15.10
pip install pykiwoom

# Data handling
pip install pandas numpy

# Technical indicators
pip install ta

# Charting
pip install matplotlib pyqtgraph

# Notifications & utilities
pip install requests loguru pyyaml schedule

# Dev dependencies
pip install -D pytest black mypy ruff pre-commit pyinstaller
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| PyQt5 | PyQt6 | NEVER for this project. PyQt6 removed QAxWidget (COM/OCX hosting). Kiwoom API cannot work without it. |
| PyQt5 | PySide2 | Only if PyQt5 licensing is a concern (GPL vs LGPL). PySide2 QAxWidget works but has a smaller Kiwoom community. |
| pykiwoom | Direct QAxWidget calls | When you need fine-grained control over every TR call, or pykiwoom doesn't support a specific TR. Start with pykiwoom, drop down to raw calls as needed. |
| ta (Python) | TA-Lib (C wrapper) | When you need maximum indicator calculation speed for backtesting large datasets. TA-Lib requires separate C library installation (painful on Windows). |
| SQLite | PostgreSQL | NEVER for v1. This is a single-user desktop app. PostgreSQL adds deployment complexity for zero benefit. |
| pyqtgraph | mplfinance | When you only need static charts. pyqtgraph is far superior for real-time candlestick updates. |
| schedule | APScheduler | When you need cron-like expressions or persistent job storage. Overkill for market-hours scheduling. |
| loguru | stdlib logging | When you want zero external dependencies. loguru is worth the dependency for its rotation and formatting. |
| YAML config | TOML config | Either works. YAML allows comments inline with strategy parameters which traders find more natural. |
| backtrader | vectorbt | When doing vectorized backtesting for speed. backtrader is event-driven (closer to live trading logic) but unmaintained since 2021. See "What NOT to Use" below. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PyQt6 | Removed QAxWidget COM support. Kiwoom OCX cannot be hosted. | PyQt5 5.15.x |
| Python 3.11+ (64-bit) | Kiwoom OpenAPI+ OCX is 32-bit COM. 64-bit Python cannot load 32-bit COM objects. Some users report 3.11 COM issues even in 32-bit. | Python 3.10.x 32-bit |
| backtrader | Last release 2021, unmaintained, Python 3.10+ compatibility issues. | Custom backtest engine using pandas, or vectorbt |
| Tkinter | Technically possible but cannot host COM/OCX controls. No QAxWidget equivalent. | PyQt5 |
| win32com (pywin32) | Can call COM methods but cannot host OCX visual controls needed for Kiwoom's event-driven architecture. | PyQt5 QAxWidget |
| jupyter notebook for live trading | Not suitable for production trading. Use for analysis/backtest only. | PyQt5 GUI application |
| asyncio for Kiwoom API | Kiwoom OCX requires a Qt event loop, not asyncio. Mixing them causes deadlocks. | PyQt5 QApplication event loop |
| MongoDB | Over-engineered for local trade logging. Adds a service dependency. | SQLite |
| ccxt | Cryptocurrency exchange library. Does not support Korean stock brokerages. | pykiwoom |

## Stack Patterns by Variant

**If backtesting only (no live trading):**
- Skip PyQt5 QAxWidget integration
- Use pandas + ta for indicator calculation on CSV/DB data
- Use matplotlib/mplfinance for result visualization
- Can use 64-bit Python and any version

**If live trading with minimal GUI:**
- PyQt5 is still required for COM bridge (even headless)
- Must create QApplication even without visible windows
- Kiwoom login dialog will appear (cannot be fully headless)

**If scaling to multi-strategy:**
- Use YAML config per strategy with a strategy registry pattern
- SQLite per-strategy tables or separate DB files
- Consider moving backtest data to DuckDB for analytical queries

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| PyQt5 5.15.x | Python 3.10 32-bit | Verified combination for Kiwoom. Do NOT upgrade PyQt independently. |
| pykiwoom | PyQt5 5.15.x | pykiwoom imports PyQt5 internally. Version mismatch causes import errors. |
| pandas 2.x | numpy 1.26.x+ | pandas 2.x requires numpy >= 1.23. Install pandas first, it pulls compatible numpy. |
| pyqtgraph 0.13.x | PyQt5 5.15.x | pyqtgraph auto-detects Qt binding. Ensure PyQt5 is installed first. |
| matplotlib 3.8.x | PyQt5 5.15.x | Use `matplotlib.backends.backend_qt5agg` for embedding in PyQt5 windows. |
| ta 0.11.x | pandas 2.x | ta library outputs pandas Series/DataFrames. Compatible with pandas 2.x. |

## Critical Notes

### 32-bit Python Requirement
This is the single most important constraint. Kiwoom OpenAPI+ is a 32-bit Windows COM/OCX control. You MUST use:
- Windows OS (not macOS, not Linux, not WSL)
- 32-bit Python (not 64-bit)
- Python 3.10.x (safest for COM compatibility)

Attempting to use 64-bit Python will result in the OCX control failing to register or load silently.

### Qt Event Loop is Non-Negotiable
Even if you don't want a GUI, the Kiwoom API requires a Qt event loop (`QApplication.exec_()`) to process COM events. All real-time data and order responses come through Qt signal/slot mechanism. Never try to replace this with threading or asyncio.

### pykiwoom vs Raw QAxWidget
Start with pykiwoom for rapid development. It handles:
- Login flow and connection management
- TR request/response pairing with callbacks
- Real-time data subscription helpers

Drop to raw `QAxWidget.dynamicCall()` only when pykiwoom doesn't expose a specific Kiwoom function you need.

## Sources

- Training data knowledge (May 2025 cutoff) -- MEDIUM confidence
- Kiwoom OpenAPI+ official documentation pattern (well-established, stable API since ~2015)
- Korean quant trading community conventions (widely documented pattern: Python 3.10 32-bit + PyQt5)
- **NOTE:** All version numbers should be verified against PyPI before installation. WebSearch/WebFetch/Bash tools were unavailable during this research session.

---
*Stack research for: Kiwoom Securities OpenAPI+ Automated Day-Trading System*
*Researched: 2026-03-13*
