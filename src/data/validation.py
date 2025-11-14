"""Data quality validation for OHLCV bars."""

import pandas as pd

from src.core.logging import get_logger

logger = get_logger(__name__)


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


def validate_bars(df: pd.DataFrame, symbol: str, max_staleness_days: int = 2) -> bool:
    """
    Validate OHLCV bar data quality.

    Args:
        df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        symbol: Symbol being validated (for logging)
        max_staleness_days: Maximum age of most recent bar in days

    Returns:
        True if validation passes

    Raises:
        DataValidationError: If validation fails
    """
    if df.empty:
        raise DataValidationError(f"{symbol}: DataFrame is empty")

    # Check required columns
    required_cols = {"open", "high", "low", "close", "volume"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise DataValidationError(
            f"{symbol}: Missing required columns: {missing_cols}"
        )

    # Check for NaN values
    nan_cols = df[list(required_cols)].columns[df[list(required_cols)].isna().any()].tolist()
    if nan_cols:
        nan_count = df[nan_cols].isna().sum().to_dict()
        raise DataValidationError(
            f"{symbol}: NaN values found in {nan_cols}: {nan_count}"
        )

    # Check OHLC relationships (high >= close >= low, high >= open >= low)
    invalid_high = df[df["high"] < df["close"]].index.tolist()
    if invalid_high:
        raise DataValidationError(
            f"{symbol}: high < close at {len(invalid_high)} rows: {invalid_high[:5]}"
        )

    invalid_low_close = df[df["low"] > df["close"]].index.tolist()
    if invalid_low_close:
        raise DataValidationError(
            f"{symbol}: low > close at {len(invalid_low_close)} rows: {invalid_low_close[:5]}"
        )

    invalid_high_open = df[df["high"] < df["open"]].index.tolist()
    if invalid_high_open:
        raise DataValidationError(
            f"{symbol}: high < open at {len(invalid_high_open)} rows: {invalid_high_open[:5]}"
        )

    invalid_low_open = df[df["low"] > df["open"]].index.tolist()
    if invalid_low_open:
        raise DataValidationError(
            f"{symbol}: low > open at {len(invalid_low_open)} rows: {invalid_low_open[:5]}"
        )

    # Check for price outliers (>50% daily change is suspicious)
    df_sorted = df.sort_index()
    price_change = df_sorted["close"].pct_change().abs()
    outliers = price_change[price_change > 0.50].index.tolist()
    if outliers:
        logger.warning(
            f"{symbol}: Large price jumps (>50%) detected at {len(outliers)} bars: {outliers[:3]}"
        )
        # Don't fail, just warn - legitimate for some volatile stocks

    # Check volume > 0 (except for first bar which might be 0)
    zero_volume = df[df["volume"] <= 0].index.tolist()
    if len(zero_volume) > 1 or (len(zero_volume) == 1 and zero_volume[0] != df.index[0]):
        raise DataValidationError(
            f"{symbol}: Zero/negative volume at {len(zero_volume)} bars: {zero_volume[:5]}"
        )

    # Check for stale data (most recent bar should be within max_staleness_days)
    if isinstance(df.index, pd.DatetimeIndex):
        most_recent = df.index.max()
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=max_staleness_days)
        if most_recent < cutoff:
            raise DataValidationError(
                f"{symbol}: Stale data - most recent bar is {most_recent}, "
                f"but cutoff is {cutoff} ({max_staleness_days} days)"
            )

    logger.info(f"{symbol}: Validation passed ({len(df)} bars)")
    return True


def validate_bars_safe(df: pd.DataFrame, symbol: str, max_staleness_days: int = 2) -> tuple[bool, str]:
    """
    Safe wrapper for validate_bars that catches exceptions.

    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol being validated
        max_staleness_days: Maximum age of most recent bar in days

    Returns:
        (is_valid, error_message) tuple
    """
    try:
        validate_bars(df, symbol, max_staleness_days)
        return (True, "")
    except DataValidationError as e:
        return (False, str(e))
    except Exception as e:
        return (False, f"Unexpected validation error: {e}")


def check_data_quality_batch(
    data: dict[str, pd.DataFrame],
    max_staleness_days: int = 2
) -> dict[str, str]:
    """
    Validate multiple symbols and return any failures.

    Args:
        data: Dict mapping symbol -> DataFrame
        max_staleness_days: Maximum age of most recent bar in days

    Returns:
        Dict mapping symbol -> error message (only failed symbols)
    """
    failures = {}

    for symbol, df in data.items():
        is_valid, error = validate_bars_safe(df, symbol, max_staleness_days)
        if not is_valid:
            failures[symbol] = error
            logger.error(f"Data validation failed for {symbol}: {error}")

    if not failures:
        logger.info(f"Data quality check passed for all {len(data)} symbols")
    else:
        logger.warning(f"Data quality check failed for {len(failures)}/{len(data)} symbols")

    return failures

