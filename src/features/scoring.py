"""Scoring function for asset selection."""
import numpy as np
import pandas as pd

from src.core.logging import get_logger
from src.features.indicators import atr, ema

logger = get_logger(__name__)


def calculate_score(
    close: pd.Series,
    ema_fast: pd.Series,
    atr: pd.Series,
    eps: float = 1e-6,
) -> pd.Series:
    """
    Calculate asset score for selection.

    Score = ((Close / EMA20) - 1) / max(ATR%, eps)
    where ATR% = ATR / Close

    Args:
        close: Close prices
        ema_fast: Fast EMA (typically EMA20)
        atr: ATR values
        eps: Small epsilon to avoid division by zero

    Returns:
        Series with scores
    """
    if len(close) == 0 or len(ema_fast) == 0 or len(atr) == 0:
        return pd.Series(dtype=float, index=close.index)

    # Calculate ATR percentage
    atr_pct = atr / close

    # Calculate price momentum relative to EMA
    price_momentum = (close / ema_fast) - 1.0

    # Score = momentum / volatility (ATR%)
    # Use max to avoid division by zero
    score = price_momentum / np.maximum(atr_pct, eps)

    return score


def calculate_scores_for_dataframe(
    df: pd.DataFrame,
    ema_fast_window: int = 20,
    atr_window: int = 20,
    eps: float = 1e-6,
) -> pd.Series:
    """
    Calculate scores for a DataFrame with OHLCV data.

    Args:
        df: DataFrame with columns [open, high, low, close, volume]
        ema_fast_window: Fast EMA window (default: 20)
        atr_window: ATR window (default: 20)
        eps: Small epsilon to avoid division by zero

    Returns:
        Series with scores indexed by timestamp
    """
    if df.empty:
        return pd.Series(dtype=float)

    required_cols = ["open", "high", "low", "close", "volume"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Calculate indicators
    ema_fast = ema(close, ema_fast_window)
    atr_values = atr(high, low, close, atr_window)

    # Calculate scores
    scores = calculate_score(close, ema_fast, atr_values, eps)

    return scores
