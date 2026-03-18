---
created: 2026-03-18T20:45:59.298Z
title: Add Monte Carlo simulation for strategy validation
area: backtest
files:
  - kiwoom_trader/backtest/performance.py
  - kiwoom_trader/backtest/replay_engine.py
  - scripts/replay.py
---

## Problem

현재 전략 평가는 2일치 데이터 리플레이 결과(수익률, 승률, MDD)만으로 판단한다. 샘플이 적어 전략이 진짜 유효한지, 운이 좋거나 나빴던 건지 구분할 수 없다. 특히 거래 건수가 0~18건으로 통계적 유의성이 없음.

## Solution

`performance.py`에 `monte_carlo_analysis()` 함수 추가:

1. 실제 거래 결과(P&L 리스트)를 입력받아 순서를 랜덤 셔플하여 N회(10,000회) 반복
2. 각 시뮬레이션에서 에쿼티 커브, 최종 수익, MDD 계산
3. 산출 지표:
   - 95% 신뢰구간 (수익률 상한/하한)
   - Worst-case MDD (99th percentile)
   - 파산 확률 (자본 X% 이하로 하락할 확률)
   - 기대 수익 분포 히스토그램
4. `replay.py`에 `--monte-carlo` 옵션 추가하여 리플레이 후 자동 실행
5. 전제: 거래 건수 20건+ 쌓인 후 적용 (그 전에는 경고 출력)
