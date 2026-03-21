"""Day trading strategies for Korean stock market.

These strategies operate on intraday tick/candle data and are designed
for 1-3 trades per day with high conviction entries.

Usage with ReplayEngine:
    engine = ReplayEngine(...)
    engine.day_strategies = [ORBStrategy(), VWAPBounceStrategy(), ...]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from collections import deque


@dataclass
class DaySignal:
    """Signal from a day trading strategy."""
    code: str
    side: str  # "BUY" or "SELL"
    price: int
    strategy: str
    reason: str
    timestamp: datetime


class ORBStrategy:
    """Opening Range Breakout — 장 시작 N분간 고/저를 정하고 돌파 시 진입.

    - 09:00~09:30: Range 형성 (고가/저가 기록)
    - 09:30 이후: 고가 돌파 → BUY, 저가 돌파 → SELL(숏은 못하므로 보유 중이면 청산)
    - 하루 최대 1건, 14:00 이후 신규 진입 금지

    Args:
        range_minutes: Range 형성 시간 (기본 30분 = 09:00~09:30)
        breakout_buffer_pct: 돌파 확인 버퍼 (0.1% = 가짜 돌파 필터)
    """

    def __init__(self, range_minutes: int = 30, breakout_buffer_pct: float = 0.1):
        self.name = "ORB"
        self.range_minutes = range_minutes
        self.breakout_buffer_pct = breakout_buffer_pct
        self._reset()

    def _reset(self):
        self._range_high: dict[str, float] = {}
        self._range_low: dict[str, float] = {}
        self._range_set: dict[str, bool] = {}
        self._traded_today: dict[str, bool] = {}
        self._in_position: dict[str, bool] = {}

    def on_candle(self, code: str, candle) -> list[DaySignal]:
        """Process a candle and return signals."""
        ts = candle.timestamp
        signals = []

        # Market open = 09:00
        market_open = ts.replace(hour=9, minute=0, second=0)
        range_end = ts.replace(hour=9, minute=self.range_minutes, second=0)

        # Phase 1: Range formation (09:00 ~ 09:30)
        if market_open <= ts < range_end:
            if code not in self._range_high:
                self._range_high[code] = candle.high
                self._range_low[code] = candle.low
            else:
                self._range_high[code] = max(self._range_high[code], candle.high)
                self._range_low[code] = min(self._range_low[code], candle.low)
            return signals

        # Range not formed yet
        if code not in self._range_high:
            return signals

        self._range_set[code] = True
        rh = self._range_high[code]
        rl = self._range_low[code]
        buffer = rh * self.breakout_buffer_pct / 100

        # Phase 2: Breakout detection (09:30 ~ 14:00)
        if self._traded_today.get(code):
            # Already traded — check exit only
            if self._in_position.get(code) and ts.hour >= 14:
                signals.append(DaySignal(
                    code=code, side="SELL", price=candle.close,
                    strategy=self.name, reason="ORB 시간 청산 (14:00)",
                    timestamp=ts,
                ))
                self._in_position[code] = False
            return signals

        if ts.hour >= 14:
            return signals  # No new entries after 14:00

        # Breakout up → BUY
        if candle.close > rh + buffer:
            signals.append(DaySignal(
                code=code, side="BUY", price=candle.close,
                strategy=self.name,
                reason=f"ORB 상단돌파 (range {rl:,.0f}~{rh:,.0f}, close {candle.close:,.0f})",
                timestamp=ts,
            ))
            self._traded_today[code] = True
            self._in_position[code] = True

        return signals


class VWAPBounceStrategy:
    """VWAP Mean Reversion — VWAP 아래로 이탈 후 복귀할 때 매수.

    - VWAP을 누적 계산 (틱 데이터 기반)
    - 가격이 VWAP 아래 → VWAP 위로 복귀 시 BUY
    - VWAP 위 1% 도달 시 익절, VWAP 아래 0.5% 손절

    Args:
        reversion_threshold_pct: VWAP 대비 이탈 임계값 (%)
    """

    def __init__(self, reversion_threshold_pct: float = 0.3):
        self.name = "VWAP_BOUNCE"
        self.threshold = reversion_threshold_pct
        self._cum_pv: dict[str, float] = {}  # cumulative price*volume
        self._cum_vol: dict[str, int] = {}   # cumulative volume
        self._below_vwap: dict[str, bool] = {}
        self._traded_count: dict[str, int] = {}
        self._in_position: dict[str, bool] = {}
        self._entry_price: dict[str, float] = {}

    def _get_vwap(self, code: str) -> float:
        vol = self._cum_vol.get(code, 0)
        if vol == 0:
            return 0
        return self._cum_pv.get(code, 0) / vol

    def on_candle(self, code: str, candle) -> list[DaySignal]:
        ts = candle.timestamp
        signals = []

        if ts.hour < 9:
            return signals

        # Update VWAP
        typical_price = (candle.high + candle.low + candle.close) / 3
        self._cum_pv[code] = self._cum_pv.get(code, 0) + typical_price * candle.volume
        self._cum_vol[code] = self._cum_vol.get(code, 0) + candle.volume

        vwap = self._get_vwap(code)
        if vwap == 0:
            return signals

        price = candle.close
        pct_from_vwap = (price - vwap) / vwap * 100

        # Exit check
        if self._in_position.get(code):
            entry = self._entry_price.get(code, price)
            pnl_pct = (price - entry) / entry * 100
            if pnl_pct >= 0.5:  # 익절
                signals.append(DaySignal(code, "SELL", price, self.name,
                    f"VWAP 익절 +{pnl_pct:.2f}%", ts))
                self._in_position[code] = False
            elif pnl_pct <= -0.3:  # 손절
                signals.append(DaySignal(code, "SELL", price, self.name,
                    f"VWAP 손절 {pnl_pct:.2f}%", ts))
                self._in_position[code] = False
            elif ts.hour >= 14:  # 시간 청산
                signals.append(DaySignal(code, "SELL", price, self.name,
                    "VWAP 시간 청산", ts))
                self._in_position[code] = False
            return signals

        # Max 3 trades/day
        if self._traded_count.get(code, 0) >= 3:
            return signals
        if ts.hour >= 14:
            return signals

        # Track VWAP crossover
        was_below = self._below_vwap.get(code, False)
        is_below = pct_from_vwap < -self.threshold

        if is_below:
            self._below_vwap[code] = True
        elif was_below and pct_from_vwap > 0:
            # Cross above VWAP from below → BUY
            signals.append(DaySignal(code, "BUY", price, self.name,
                f"VWAP 반등 (VWAP={vwap:,.0f}, price={price:,.0f})", ts))
            self._below_vwap[code] = False
            self._traded_count[code] = self._traded_count.get(code, 0) + 1
            self._in_position[code] = True
            self._entry_price[code] = price

        return signals


class PrevDayBreakoutStrategy:
    """전일 고/저 돌파 — 전일 고가 돌파 시 매수, 전일 저가 돌파 시 매수 금지.

    - 전일 고가를 market_context에서 가져옴
    - 장 시작 후 전일 고가 돌파 + 거래량 확인 → BUY
    - 하루 1건, 14시 이후 청산

    Args:
        volume_multiplier: 평균 거래량 대비 배수 (기본 1.5x)
    """

    def __init__(self, volume_multiplier: float = 1.5):
        self.name = "PREV_DAY_BREAKOUT"
        self.volume_mult = volume_multiplier
        self._traded: dict[str, bool] = {}
        self._in_position: dict[str, bool] = {}
        self._vol_history: dict[str, deque] = {}
        self._prev_high: dict[str, float] = {}
        self._prev_low: dict[str, float] = {}

    def set_prev_day(self, code: str, prev_high: float, prev_low: float):
        """Set previous day high/low from market context."""
        self._prev_high[code] = prev_high
        self._prev_low[code] = prev_low

    def on_candle(self, code: str, candle) -> list[DaySignal]:
        ts = candle.timestamp
        signals = []

        if code not in self._prev_high:
            return signals
        if ts.hour < 9 or (ts.hour == 9 and ts.minute < 10):
            return signals  # Skip first 10 min

        # Volume tracking
        if code not in self._vol_history:
            self._vol_history[code] = deque(maxlen=20)
        self._vol_history[code].append(candle.volume)

        # Exit
        if self._in_position.get(code) and ts.hour >= 14:
            signals.append(DaySignal(code, "SELL", candle.close, self.name,
                "전일돌파 시간 청산", ts))
            self._in_position[code] = False
            return signals

        if self._traded.get(code) or ts.hour >= 14:
            return signals

        prev_h = self._prev_high[code]
        prev_l = self._prev_low[code]
        avg_vol = sum(self._vol_history[code]) / max(len(self._vol_history[code]), 1)

        # 전일 고가 돌파 + 거래량 확인
        if candle.close > prev_h and candle.volume > avg_vol * self.volume_mult:
            signals.append(DaySignal(code, "BUY", candle.close, self.name,
                f"전일고가 돌파 ({prev_h:,.0f}→{candle.close:,.0f}, vol x{candle.volume/max(avg_vol,1):.1f})",
                ts))
            self._traded[code] = True
            self._in_position[code] = True

        # 전일 저가 붕괴 시 매수 차단 (이미 보유 중이면 청산)
        if self._in_position.get(code) and candle.close < prev_l:
            signals.append(DaySignal(code, "SELL", candle.close, self.name,
                f"전일저가 붕괴 손절 ({prev_l:,.0f})", ts))
            self._in_position[code] = False

        return signals


class GapStrategy:
    """갭 트레이딩 — 갭 방향에 따라 되메움 or 추세 진입.

    - 갭업 > 1%: 되메움 매도 (숏 불가이므로 스킵) or 추세 매수
    - 갭다운 < -1%: 되메움 매수 (전일 종가 복귀 시 익절)
    - 09:10~11:00 사이만 진입

    Args:
        gap_threshold_pct: 갭 임계값 (기본 1%)
    """

    def __init__(self, gap_threshold_pct: float = 1.0):
        self.name = "GAP_TRADE"
        self.threshold = gap_threshold_pct
        self._prev_close: dict[str, float] = {}
        self._gap_pct: dict[str, float] = {}
        self._gap_type: dict[str, str] = {}  # "up" or "down" or ""
        self._traded: dict[str, bool] = {}
        self._in_position: dict[str, bool] = {}
        self._first_price_set: dict[str, bool] = {}

    def set_prev_close(self, code: str, prev_close: float):
        self._prev_close[code] = prev_close

    def on_candle(self, code: str, candle) -> list[DaySignal]:
        ts = candle.timestamp
        signals = []

        if code not in self._prev_close:
            return signals

        prev_c = self._prev_close[code]

        # Detect gap on first candle after 09:00
        if not self._first_price_set.get(code) and ts.hour >= 9:
            gap = (candle.open - prev_c) / prev_c * 100
            self._gap_pct[code] = gap
            self._first_price_set[code] = True
            if gap < -self.threshold:
                self._gap_type[code] = "down"
            elif gap > self.threshold:
                self._gap_type[code] = "up"
            else:
                self._gap_type[code] = ""

        # Exit
        if self._in_position.get(code):
            if candle.close >= prev_c:  # 전일 종가 복귀 → 익절
                signals.append(DaySignal(code, "SELL", candle.close, self.name,
                    f"갭 되메움 익절 (전일종가 {prev_c:,.0f} 복귀)", ts))
                self._in_position[code] = False
            elif ts.hour >= 14:
                signals.append(DaySignal(code, "SELL", candle.close, self.name,
                    "갭 시간 청산", ts))
                self._in_position[code] = False
            return signals

        if self._traded.get(code):
            return signals

        # Only 09:10 ~ 11:00
        if ts.hour < 9 or (ts.hour == 9 and ts.minute < 10):
            return signals
        if ts.hour >= 11:
            return signals

        # 갭다운 → 되메움 매수
        if self._gap_type.get(code) == "down" and candle.close < prev_c * 0.995:
            signals.append(DaySignal(code, "BUY", candle.close, self.name,
                f"갭다운 되메움 매수 (갭 {self._gap_pct[code]:+.1f}%, 목표 {prev_c:,.0f})",
                ts))
            self._traded[code] = True
            self._in_position[code] = True

        return signals


class OrderFlowStrategy:
    """호가창 분석 (Volume Imbalance) — 매수/매도 체결강도로 방향 예측.

    틱 데이터의 체결량(fid_15) 부호로 매수/매도 체결을 구분하고,
    매수 체결이 압도적일 때 매수.

    실제 호가잔량은 DB에 없으므로, 체결 기반 유사 구현.

    Args:
        lookback: 체결강도 계산 기간 (봉 수)
        imbalance_threshold: 매수/매도 비율 임계값 (기본 1.5 = 매수가 1.5배)
    """

    def __init__(self, lookback: int = 10, imbalance_threshold: float = 1.5):
        self.name = "ORDER_FLOW"
        self.lookback = lookback
        self.threshold = imbalance_threshold
        self._buy_vol: dict[str, deque] = {}
        self._sell_vol: dict[str, deque] = {}
        self._traded_count: dict[str, int] = {}
        self._in_position: dict[str, bool] = {}
        self._entry_price: dict[str, float] = {}

    def on_candle(self, code: str, candle) -> list[DaySignal]:
        ts = candle.timestamp
        signals = []

        if ts.hour < 9:
            return signals

        # Estimate buy/sell volume from candle
        # If close > open → buy dominant, else sell dominant
        if code not in self._buy_vol:
            self._buy_vol[code] = deque(maxlen=self.lookback)
            self._sell_vol[code] = deque(maxlen=self.lookback)

        if candle.close >= candle.open:
            self._buy_vol[code].append(candle.volume)
            self._sell_vol[code].append(0)
        else:
            self._buy_vol[code].append(0)
            self._sell_vol[code].append(candle.volume)

        # Exit
        if self._in_position.get(code):
            entry = self._entry_price.get(code, candle.close)
            pnl_pct = (candle.close - entry) / entry * 100
            if pnl_pct >= 0.4:
                signals.append(DaySignal(code, "SELL", candle.close, self.name,
                    f"체결강도 익절 +{pnl_pct:.2f}%", ts))
                self._in_position[code] = False
            elif pnl_pct <= -0.3:
                signals.append(DaySignal(code, "SELL", candle.close, self.name,
                    f"체결강도 손절 {pnl_pct:.2f}%", ts))
                self._in_position[code] = False
            elif ts.hour >= 14:
                signals.append(DaySignal(code, "SELL", candle.close, self.name,
                    "체결강도 시간 청산", ts))
                self._in_position[code] = False
            return signals

        if self._traded_count.get(code, 0) >= 2 or ts.hour >= 14:
            return signals

        # Calculate imbalance
        total_buy = sum(self._buy_vol[code])
        total_sell = sum(self._sell_vol[code])

        if total_sell > 0 and total_buy / total_sell >= self.threshold:
            signals.append(DaySignal(code, "BUY", candle.close, self.name,
                f"매수체결 우위 (buy/sell={total_buy/total_sell:.1f}x)", ts))
            self._traded_count[code] = self._traded_count.get(code, 0) + 1
            self._in_position[code] = True
            self._entry_price[code] = candle.close

        return signals
