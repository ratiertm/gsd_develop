"""Core data models for order execution and risk management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Union


class OrderState(Enum):
    """Order lifecycle states."""

    CREATED = auto()  # 주문 생성 (아직 SendOrder 호출 전)
    SUBMITTED = auto()  # SendOrder 호출됨, 접수 대기
    ACCEPTED = auto()  # 접수 확인 (gubun=0, 주문상태=접수)
    PARTIAL_FILL = auto()  # 부분 체결 (미체결수량 > 0)
    FILLED = auto()  # 전량 체결 (미체결수량 == 0)
    CANCELLED = auto()  # 취소 완료
    REJECTED = auto()  # 거부됨
    MODIFY_PENDING = auto()  # 정정 요청 중


# Legal state transitions. Terminal states (FILLED, CANCELLED, REJECTED) have no outgoing edges.
VALID_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.CREATED: {OrderState.SUBMITTED, OrderState.REJECTED},
    OrderState.SUBMITTED: {OrderState.ACCEPTED, OrderState.REJECTED},
    OrderState.ACCEPTED: {
        OrderState.PARTIAL_FILL,
        OrderState.FILLED,
        OrderState.CANCELLED,
        OrderState.MODIFY_PENDING,
    },
    OrderState.PARTIAL_FILL: {
        OrderState.FILLED,
        OrderState.CANCELLED,
        OrderState.MODIFY_PENDING,
        OrderState.PARTIAL_FILL,
    },
    OrderState.MODIFY_PENDING: {OrderState.ACCEPTED, OrderState.REJECTED},
    # Terminal states -- no outgoing transitions
}


class OrderSide(Enum):
    """Order direction."""

    BUY = auto()
    SELL = auto()


@dataclass
class Order:
    """Represents a single order in the system."""

    code: str
    side: OrderSide
    qty: int
    price: int
    order_type: int
    hoga_gb: str
    state: OrderState = OrderState.CREATED
    order_no: str = ""
    org_order_no: str = ""
    filled_qty: int = 0
    filled_price: int = 0
    screen_no: str = ""
    rq_name: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Position:
    """Represents a held position for a single stock."""

    code: str
    qty: int
    avg_price: int
    high_water_mark: int = 0
    stop_loss_price: int = 0
    take_profit_price: int = 0
    trailing_stop_price: int = 0
    unrealized_pnl: int = 0


@dataclass
class RiskConfig:
    """Risk management configuration with user-locked defaults."""

    stop_loss_pct: float = -2.0
    take_profit_pct: float = 3.0
    trailing_stop_pct: float = 1.5
    max_symbol_weight_pct: float = 20.0
    max_positions: int = 5
    daily_loss_limit_pct: float = 3.0
    split_count: int = 3
    split_interval_sec: int = 45
    trading_start: str = "09:05"
    trading_end_new_buy: str = "15:15"
    auction_start_am: str = "08:30"
    auction_end_am: str = "09:00"
    auction_start_pm: str = "15:20"
    auction_end_pm: str = "15:30"


@dataclass
class Candle:
    """Single OHLCV candle for technical indicator calculation."""

    code: str
    open: int
    high: int
    low: int
    close: int
    volume: int
    timestamp: datetime
    cum_price_volume: float = 0.0
    cum_volume: int = 0


@dataclass
class Condition:
    """Single condition comparing an indicator value against a threshold."""

    indicator: str  # e.g. "rsi", "ema_short"
    operator: str  # "gt", "lt", "gte", "lte", "cross_above", "cross_below"
    value: float  # threshold value


@dataclass
class CompositeRule:
    """Composite rule combining conditions with AND/OR logic.

    Conditions can be Condition instances or nested CompositeRule instances.
    """

    logic: str  # "AND" or "OR"
    conditions: list[Union[Condition, CompositeRule]]


@dataclass
class Signal:
    """Trading signal emitted by a strategy."""

    code: str
    side: str  # "BUY" or "SELL"
    strategy_name: str
    priority: int
    price: int
    timestamp: datetime
    reason: str


@dataclass
class StrategyConfig:
    """Configuration for a single trading strategy."""

    name: str
    enabled: bool
    priority: int
    entry_rule: CompositeRule
    exit_rule: CompositeRule
    indicators: dict  # indicator configs: {"rsi": {"type": "rsi", "period": 14}, ...}
    cooldown_sec: int = 300


@dataclass
class TradeRecord:
    """Record of a single trade (paper or live)."""

    timestamp: datetime
    code: str
    side: str
    strategy: str
    price: int
    qty: int
    amount: int
    pnl: int
    pnl_pct: float
    balance: int
    reason: str
