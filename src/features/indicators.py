"""Technical indicators implemented from scratch."""
import numpy as np
import pandas as pd

from src.core.logging import get_logger

logger = get_logger(__name__)


def ema(series: pd.Series, window: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).

    Uses standard recursive formula: EMA_t = α * price_t + (1 - α) * EMA_{t-1}
    where α = 2 / (window + 1)

    Args:
        series: Price series (typically close prices)
        window: EMA window period

    Returns:
        Series with EMA values
    """
    if window <= 0:
        raise ValueError(f"EMA window must be positive, got {window}")

    if len(series) == 0:
        return pd.Series(dtype=float, index=series.index)

    # Calculate smoothing factor
    alpha = 2.0 / (window + 1.0)

    # Initialize result
    ema_values = np.zeros(len(series))
    ema_values[0] = series.iloc[0]

    # Recursive calculation
    for i in range(1, len(series)):
        ema_values[i] = alpha * series.iloc[i] + (1 - alpha) * ema_values[i - 1]

    return pd.Series(ema_values, index=series.index, name=f"EMA{window}")


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    """
    Calculate Average True Range (ATR) using Wilder's smoothing method.

    True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
    ATR = EMA of True Range (using Wilder's smoothing: α = 1/window)

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        window: ATR window period

    Returns:
        Series with ATR values
    """
    if window <= 0:
        raise ValueError(f"ATR window must be positive, got {window}")

    if len(high) == 0 or len(low) == 0 or len(close) == 0:
        return pd.Series(dtype=float, index=close.index)

    # Calculate True Range
    tr_values = []
    prev_close = close.iloc[0]

    for i in range(len(high)):
        h = high.iloc[i]
        lo = low.iloc[i]
        c = close.iloc[i]

        tr = max(h - lo, abs(h - prev_close), abs(lo - prev_close))
        tr_values.append(tr)
        prev_close = c

    tr_series = pd.Series(tr_values, index=close.index)

    # Wilder's smoothing (special case of EMA with α = 1/window)
    # ATR_t = (ATR_{t-1} * (window - 1) + TR_t) / window
    atr_values = np.zeros(len(tr_series))
    atr_values[0] = tr_series.iloc[0]

    for i in range(1, len(tr_series)):
        atr_values[i] = (atr_values[i - 1] * (window - 1) + tr_series.iloc[i]) / window

    return pd.Series(atr_values, index=close.index, name=f"ATR{window}")


def stdev(series: pd.Series, window: int) -> pd.Series:
    """
    Calculate rolling standard deviation.

    Uses sample standard deviation (ddof=1).

    Args:
        series: Price series (typically returns)
        window: Rolling window period

    Returns:
        Series with standard deviation values
    """
    if window <= 0:
        raise ValueError(f"STDEV window must be positive, got {window}")

    if len(series) == 0:
        return pd.Series(dtype=float, index=series.index)

    return series.rolling(window=window, min_periods=1).std(ddof=1)


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(MACD Line, signal)
    Histogram = MACD Line - Signal Line

    Args:
        close: Close prices
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal EMA period (default: 9)

    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError(f"MACD periods must be positive: fast={fast}, slow={slow}, signal={signal}")

    if fast >= slow:
        raise ValueError(f"Fast period ({fast}) must be less than slow period ({slow})")

    if len(close) == 0:
        empty = pd.Series(dtype=float, index=close.index)
        return (empty, empty, empty)

    # Calculate EMAs
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)

    # MACD line
    macd_line = ema_fast - ema_slow

    # Signal line (EMA of MACD line)
    signal_line = ema(macd_line, signal)

    # Histogram
    histogram = macd_line - signal_line

    return (macd_line, signal_line, histogram)
