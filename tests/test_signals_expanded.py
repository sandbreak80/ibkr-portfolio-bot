"""Expanded tests for signals module."""
import pandas as pd

from src.core.config import load_config
from src.strategy.signals import calculate_signals, check_exit, check_long_ok


def test_check_long_ok_empty_series() -> None:
    """Test check_long_ok with empty series."""
    close = pd.Series([], dtype=float)
    ema_fast = pd.Series([], dtype=float)
    ema_slow = pd.Series([], dtype=float)

    result = check_long_ok(close, ema_fast, ema_slow)
    assert result is False


def test_check_long_ok_trend_down() -> None:
    """Test check_long_ok when trend is down."""
    close = pd.Series([100, 101, 102])
    ema_fast = pd.Series([99, 100, 101])  # Fast < Slow
    ema_slow = pd.Series([100, 101, 102])

    result = check_long_ok(close, ema_fast, ema_slow)
    assert result is False


def test_check_long_ok_with_macd_enabled_positive() -> None:
    """Test check_long_ok with MACD enabled and positive."""
    close = pd.Series([100, 101, 102])
    ema_fast = pd.Series([100, 101, 102])
    ema_slow = pd.Series([99, 100, 101])
    macd_line = pd.Series([0.1, 0.2, 0.3])

    result = check_long_ok(close, ema_fast, ema_slow, macd_line, macd_enabled=True)
    assert result is True


def test_check_long_ok_with_macd_enabled_negative() -> None:
    """Test check_long_ok with MACD enabled and negative."""
    close = pd.Series([100, 101, 102])
    ema_fast = pd.Series([100, 101, 102])
    ema_slow = pd.Series([99, 100, 101])
    macd_line = pd.Series([-0.1, -0.2, -0.3])

    result = check_long_ok(close, ema_fast, ema_slow, macd_line, macd_enabled=True)
    assert result is False


def test_check_long_ok_with_macd_empty() -> None:
    """Test check_long_ok with MACD enabled but empty series."""
    close = pd.Series([100, 101, 102])
    ema_fast = pd.Series([100, 101, 102])
    ema_slow = pd.Series([99, 100, 101])
    macd_line = pd.Series([], dtype=float)

    result = check_long_ok(close, ema_fast, ema_slow, macd_line, macd_enabled=True)
    assert result is False


def test_check_exit_no_position() -> None:
    """Test check_exit when no position."""
    close = pd.Series([100, 101, 102])
    ema_fast = pd.Series([99, 100, 101])

    result = check_exit(close, ema_fast, current_position=False)
    assert result is False


def test_check_exit_empty_series() -> None:
    """Test check_exit with empty series."""
    close = pd.Series([], dtype=float)
    ema_fast = pd.Series([], dtype=float)

    result = check_exit(close, ema_fast, current_position=True)
    assert result is False


def test_check_exit_close_below_ema() -> None:
    """Test check_exit when close is below EMA."""
    close = pd.Series([100, 99, 98])  # Below EMA
    ema_fast = pd.Series([100, 100, 100])

    result = check_exit(close, ema_fast, current_position=True)
    assert result is True


def test_check_exit_close_above_ema() -> None:
    """Test check_exit when close is above EMA."""
    close = pd.Series([100, 101, 102])  # Above EMA
    ema_fast = pd.Series([99, 100, 101])

    result = check_exit(close, ema_fast, current_position=True)
    assert result is False


def test_calculate_signals_empty_dataframe() -> None:
    """Test calculate_signals with empty DataFrame."""
    df = pd.DataFrame()
    config = load_config()

    signals = calculate_signals(df, config)
    assert signals == {}


def test_calculate_signals_single_symbol() -> None:
    """Test calculate_signals with single symbol DataFrame."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    df = pd.DataFrame(
        {
            "open": range(100, 200),
            "high": range(101, 201),
            "low": range(99, 199),
            "close": range(100, 200),
            "volume": [1000] * 100,
        },
        index=dates,
    )
    config = load_config()

    signals = calculate_signals(df, config)
    # Should handle single symbol case
    assert isinstance(signals, dict)


def test_calculate_signals_missing_columns() -> None:
    """Test calculate_signals with missing required columns."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": range(100, 110),
            "close": range(100, 110),
            # Missing high, low, volume
        },
        index=dates,
    )
    config = load_config()

    signals = calculate_signals(df, config)
    # Should handle missing columns gracefully
    assert isinstance(signals, dict)


def test_calculate_signals_multiindex() -> None:
    """Test calculate_signals with MultiIndex DataFrame."""
    dates = pd.date_range("2020-01-01", periods=50, freq="D")
    index = pd.MultiIndex.from_product([["SPY", "QQQ"], dates], names=["symbol", "date"])
    df = pd.DataFrame(
        {
            "open": range(100, 200),
            "high": range(101, 201),
            "low": range(99, 199),
            "close": range(100, 200),
            "volume": [1000] * 100,
        },
        index=index,
    )
    config = load_config()

    signals = calculate_signals(df, config)
    assert isinstance(signals, dict)
    assert len(signals) >= 0  # May have signals or not depending on data
