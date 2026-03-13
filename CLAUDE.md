# KiwoomDayTrader

키움증권 OpenAPI+를 활용한 Python 주식 데이트레이딩 자동매매 시스템.

## Quick Reference

- **Language**: Python 3.10+
- **GUI**: PyQt5
- **Chart**: pyqtgraph
- **Logging**: loguru
- **Test**: pytest
- **Platform**: Windows (키움 OpenAPI+ COM 기반). macOS에서 개발 가능하나 GUI/API 실행 불가.

## Project Structure

```
kiwoom_trader/
  api/              # Phase 1: 키움 API 연동 (OCX, 이벤트, TR 큐, 세션)
  config/           # 설정 (constants, settings - config.json 관리)
  core/             # Phase 2-3: 매매 엔진 (주문, 리스크, 인디케이터, 전략, 포지션)
  gui/              # Phase 4: PyQt5 GUI (대시보드, 차트, 전략탭, 알림)
    widgets/        # 재사용 위젯 (캔들스틱, 인디케이터 차트, 토스트)
    notification/   # 알림 시스템 (Notifier, Discord 웹훅)
  backtest/         # Phase 5: 백테스트 (DataSource, 비용모델, 엔진, 성과분석, QThread)
  utils/            # 로깅 설정
  main.py           # 진입점 - 모든 컴포넌트 와이어링
tests/              # pytest 테스트 (369+ tests)
.planning/          # GSD 워크플로우 (로드맵, 요구사항, 페이즈별 계획/검증)
```

## Commands

```bash
# 테스트 실행
python -m pytest tests/ -x -q

# 전체 테스트 (verbose)
python -m pytest tests/ -v

# 앱 실행 (Windows + 키움 OpenAPI 필요)
python -m kiwoom_trader.main
```

## Architecture Patterns

- **PyQt5 try/except fallback**: 모든 Qt import는 `try/except ImportError`로 감싸서 macOS에서도 import 가능. `_HAS_PYQT5` 플래그로 분기.
- **Config-driven**: 모든 파라미터는 `config.json`으로 관리. `Settings` 클래스가 읽기/쓰기 담당.
- **Observer pattern**: callback 등록 방식 (RealDataManager, CandleAggregator, MarketHoursManager).
- **TDD**: RED-GREEN-REFACTOR 패턴. 테스트 먼저 작성.
- **Phase-based wiring**: `main.py`에서 Phase 1~5 순서로 컴포넌트 생성 및 시그널 연결.

## Key Conventions

- 키움 API 가격 데이터는 `abs(int(raw.strip() or "0"))` 패턴으로 파싱 (부호 규약 처리)
- TR 요청은 반드시 `TRRequestQueue`를 통해 (3.6초 제한 준수)
- `Candle` dataclass가 모든 봉 데이터의 표준 형식
- `Signal` dataclass가 매매 신호의 표준 형식
- 리스크 파라미터는 `RiskConfig` dataclass로 통합 관리
- 백테스트 비용: 매수 수수료 + 매도 수수료 + 거래세 0.18%(매도) + 슬리페이지

## Phase Status (v1.0)

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | API Foundation (OCX, 이벤트, TR 큐, 실시간) | Complete |
| 2 | Order Execution & Risk Management | 2/4 plans |
| 3 | Data Pipeline & Strategy Engine | Complete |
| 4 | Monitoring & Operations (GUI) | Complete |
| 5 | Backtest & Validation | Complete |

## Testing Notes

- PyQt5 의존 테스트는 `pytest.importorskip("PyQt5")` 또는 `@pytest.mark.skipif`로 CI 호환
- 백테스트 Dialog 테스트 7건은 PyQt5 없는 환경에서 skip
- 성과 지표(performance.py)는 순수 함수 — stdlib만 사용, 외부 의존성 없음
