# KiwoomDayTrader

키움증권 OpenAPI+를 활용한 Python 주식 데이트레이딩 자동매매 시스템

## Features

- **자동매매 엔진** - 기술적 지표(SMA, EMA, RSI, MACD, 볼린저밴드, VWAP, OBV) 기반 복합 조건으로 자동 매수/매도
- **리스크 관리** - 손절/익절, 트레일링 스탑, 분할매매, 포지션 제한, 일일 손실 한도
- **실시간 GUI** - PyQt5 대시보드 (보유종목, 주문현황, 수익률, 실시간 캔들차트)
- **백테스트** - 과거 데이터로 전략 시뮬레이션, 성과 분석(수익률, MDD, 승률, 샤프비율), 결과 시각화
- **알림 시스템** - GUI 토스트 팝업, 로그 파일, Discord 웹훅

## Requirements

- Windows 10/11 (키움 OpenAPI+ COM 기반)
- Python 3.10+
- 키움증권 OpenAPI+ 설치
- 키움증권 계좌

## Installation

```bash
git clone https://github.com/ratiertm/gsd_develop.git
cd gsd_develop
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
# 앱 실행
python -m kiwoom_trader.main

# 테스트 실행
python -m pytest tests/ -x -q
```

## Architecture

```
kiwoom_trader/
  api/          키움 OpenAPI+ 연동 (OCX, 이벤트 핸들러, TR 큐, 세션)
  config/       설정 관리 (config.json, 상수 정의)
  core/         매매 엔진 (주문, 리스크, 인디케이터, 전략, 포지션)
  gui/          PyQt5 GUI (대시보드, 차트, 전략탭, 알림)
  backtest/     백테스트 (DataSource, 비용모델, 엔진, 성과분석)
  utils/        유틸리티 (로깅)
  main.py       진입점
tests/          테스트 (369+ test cases)
```

## Key Components

| Component | Description |
|-----------|-------------|
| `KiwoomAPI` | 키움 OpenAPI+ OCX 래퍼 |
| `TRRequestQueue` | TR 요청 스로틀링 (3.6초/건 제한 준수) |
| `StrategyManager` | 전략 로드, 인디케이터 관리, 조건 평가, 신호 생성 |
| `RiskManager` | 6-check pre-trade validation (손절/익절/트레일링/포지션제한/일일한도/장시간) |
| `BacktestEngine` | 과거 봉 데이터 리플레이, 동일 전략/리스크 로직 적용 |
| `MainWindow` | 3-tab GUI (Dashboard, Chart, Strategy) |

## Configuration

모든 설정은 `config.json`으로 관리:

```json
{
  "tr_interval_ms": 3600,
  "risk": {
    "stop_loss_pct": -2.0,
    "take_profit_pct": 3.0,
    "trailing_stop_pct": 1.5,
    "max_positions": 5,
    "daily_loss_limit_pct": 3.0
  },
  "backtest": {
    "buy_commission_pct": 0.015,
    "sell_commission_pct": 0.015,
    "tax_pct": 0.18,
    "slippage_bp": 5.0,
    "initial_capital": 10000000
  }
}
```

## Development

이 프로젝트는 [GSD (Get Shit Done)](https://github.com/cline/get-shit-done) 워크플로우로 개발되었습니다.

### Phase Status (v1.0)

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | API Foundation | Complete |
| 2 | Order Execution & Risk Management | Complete |
| 3 | Data Pipeline & Strategy Engine | Complete |
| 4 | Monitoring & Operations (GUI) | Complete |
| 5 | Backtest & Validation | Complete |

## License

Private - All rights reserved
