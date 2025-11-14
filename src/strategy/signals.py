"""Strategy signals: trend gates and exit conditions."""
from typing import Optional

import pandas as pd

from src.core.config import AppConfig
from src.core.logging import get_logger
from src.features.indicators import ema, macd

logger = get_logger(__name__)


def check_long_ok(
    close: pd.Series,
    ema_fast: pd.Series,
    ema_slow: pd.Series,
    macd_line: Optional[pd.Series] = None,
    macd_enabled: bool = False,
) -> bool:
    """
    Check if long position is allowed based on trend gates.

    Args:
        close: Close prices
        ema_fast: Fast EMA (typically EMA20)
        ema_slow: Slow EMA (typically EMA50)
        macd_line: MACD line (optional)
        macd_enabled: Whether to require MACD > 0

    Returns:
        True if long position is allowed
    """
    if len(close) == 0 or len(ema_fast) == 0 or len(ema_slow) == 0:
        return False

    # Basic trend gate: EMA20 > EMA50
    latest_fast = ema_fast.iloc[-1]
    latest_slow = ema_slow.iloc[-1]
    trend_ok = bool(latest_fast > latest_slow)

    if not trend_ok:
        return False

    # Optional MACD gate
    if macd_enabled and macd_line is not None:
        if len(macd_line) == 0:
            return False
        macd_ok = bool(macd_line.iloc[-1] > 0)
        return macd_ok

    return True


def check_exit(
    close: pd.Series,
    ema_fast: pd.Series,
    current_position: bool = True,
) -> bool:
    """
    Check if position should be exited.

    Exit condition: Close < EMA20

    Args:
        close: Close prices
        ema_fast: Fast EMA (typically EMA20)
        current_position: Whether currently holding position

    Returns:
        True if position should be exited
    """
    if not current_position:
        return False

    if len(close) == 0 or len(ema_fast) == 0:
        return False

    latest_close = close.iloc[-1]
    latest_ema = ema_fast.iloc[-1]

    return bool(latest_close < latest_ema)


def calculate_signals(
    df: pd.DataFrame,
    config: AppConfig,
) -> dict[str, bool]:
    """
    Calculate long_ok signals for all symbols in DataFrame.

    Args:
        df: DataFrame with OHLCV data (MultiIndex: symbol, date)
        config: Application configuration

    Returns:
        Dictionary mapping symbols to long_ok boolean
    """
    signals = {}

    if df.empty:
        return signals

    # Check if MultiIndex (symbol, date) or single symbol
    if isinstance(df.index, pd.MultiIndex):
        symbols = df.index.get_level_values(0).unique()
    else:
        # Single symbol case - assume symbol name from columns or index name
        symbols = ["UNKNOWN"]

    for symbol in symbols:
        try:
            if isinstance(df.index, pd.MultiIndex):
                symbol_df = df.loc[symbol]
            else:
                symbol_df = df

            if symbol_df.empty:
                signals[symbol] = False
                continue

            required_cols = ["open", "high", "low", "close", "volume"]
            if not all(col in symbol_df.columns for col in required_cols):
                signals[symbol] = False
                continue

            close = symbol_df["close"]
            # high = symbol_df["high"]  # Reserved for future use (stop losses, etc.)
            # low = symbol_df["low"]    # Reserved for future use (stop losses, etc.)

            # Calculate EMAs
            ema_fast = ema(close, config.features.ema_fast)
            ema_slow = ema(close, config.features.ema_slow)

            # Calculate MACD if enabled
            macd_line = None
            if config.features.macd.enabled:
                macd_line, _, _ = macd(
                    close,
                    fast=config.features.macd.fast,
                    slow=config.features.macd.slow,
                    signal=config.features.macd.signal,
                )

            # Check long_ok
            long_ok = check_long_ok(
                close,
                ema_fast,
                ema_slow,
                macd_line,
                config.features.macd.enabled,
            )

            signals[symbol] = long_ok

        except Exception as e:
            logger.error(f"Error calculating signal for {symbol}: {e}")
            signals[symbol] = False

    return signals
