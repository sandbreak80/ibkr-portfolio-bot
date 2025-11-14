"""Test strategy signals."""
import pandas as pd

from src.strategy.signals import check_exit, check_long_ok


def test_check_long_ok_basic() -> None:
    """Test long_ok check with basic trend."""
    close = pd.Series([100, 105, 110])
    ema_fast = pd.Series([100, 102, 104])  # Rising
    ema_slow = pd.Series([100, 101, 102])  # Rising but slower

    # EMA fast > EMA slow, should be OK
    assert check_long_ok(close, ema_fast, ema_slow) is True

    # EMA fast < EMA slow, should not be OK
    ema_fast_reverse = pd.Series([100, 99, 98])
    assert check_long_ok(close, ema_fast_reverse, ema_slow) is False


def test_check_exit() -> None:
    """Test exit condition."""
    close = pd.Series([100, 95, 90])  # Falling
    ema_fast = pd.Series([100, 100, 100])  # Constant

    # Close < EMA, should exit (90 < 100)
    result = check_exit(close, ema_fast, current_position=True)
    assert result is True, f"Expected True but got {result}"

    # Close > EMA, should not exit (110 > 100)
    close_rising = pd.Series([100, 105, 110])
    result = check_exit(close_rising, ema_fast, current_position=True)
    assert result is False, f"Expected False but got {result}"

    # No position, should not exit
    result = check_exit(close, ema_fast, current_position=False)
    assert result is False, f"Expected False but got {result}"
