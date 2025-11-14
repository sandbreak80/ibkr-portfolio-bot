"""Type definitions and dataclasses."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict


@dataclass
class Bar:
    """OHLCV bar data."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class PositionDict(TypedDict):
    """Position dictionary."""

    symbol: str
    quantity: float
    weight: float
    notional: float


class OrderDict(TypedDict):
    """Order dictionary."""

    symbol: str
    action: str  # BUY | SELL
    quantity: float
    order_type: str  # MKT | LMT
    limit_price: Optional[float]
    account: str


class MetricsDict(TypedDict):
    """Backtest metrics dictionary."""

    CAGR: float
    Sharpe: float
    Calmar: float
    MaxDD: float
    PF: float  # Profit Factor
    Turnover: float


class RebalanceSnapshot(TypedDict):
    """Rebalance event snapshot."""

    date: str
    scores: dict[str, float]
    selected: list[str]
    weights: dict[str, float]
    orders: Optional[list[OrderDict]]


@dataclass
class AssetData:
    """Asset data container."""

    symbol: str
    bars: list[Bar]
    returns: list[float]
    ema_fast: Optional[list[float]] = None
    ema_slow: Optional[list[float]] = None
    atr: Optional[list[float]] = None
    macd: Optional[list[float]] = None
    macd_signal: Optional[list[float]] = None
    score: Optional[float] = None
    long_ok: Optional[bool] = None
