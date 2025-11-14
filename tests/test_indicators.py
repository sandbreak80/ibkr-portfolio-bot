"""Test indicators against known values."""
import pandas as pd
import pytest

from src.features.indicators import atr, ema, macd, stdev


def test_ema_basic() -> None:
    """Test EMA with simple constant series."""
    series = pd.Series([10.0] * 10)
    ema_result = ema(series, window=5)
    assert len(ema_result) == 10
    assert ema_result.iloc[0] == 10.0
    # EMA should converge to the constant value
    assert abs(ema_result.iloc[-1] - 10.0) < 0.01


def test_ema_rising() -> None:
    """Test EMA with rising series."""
    series = pd.Series(range(1, 11), dtype=float)
    ema_result = ema(series, window=3)
    assert len(ema_result) == 10
    assert ema_result.iloc[0] == 1.0
    # EMA should lag but follow the trend
    assert ema_result.iloc[-1] > ema_result.iloc[0]


def test_ema_window_validation() -> None:
    """Test EMA window validation."""
    series = pd.Series([1, 2, 3])
    with pytest.raises(ValueError):
        ema(series, window=0)
    with pytest.raises(ValueError):
        ema(series, window=-1)


def test_atr_basic() -> None:
    """Test ATR with simple data."""
    high = pd.Series([110, 111, 112])
    low = pd.Series([100, 101, 102])
    close = pd.Series([105, 106, 107])
    atr_result = atr(high, low, close, window=3)
    assert len(atr_result) == 3
    assert atr_result.iloc[0] == 10.0  # First TR = high - low
    assert all(atr_result > 0)


def test_atr_window_validation() -> None:
    """Test ATR window validation."""
    high = pd.Series([110, 111])
    low = pd.Series([100, 101])
    close = pd.Series([105, 106])
    with pytest.raises(ValueError):
        atr(high, low, close, window=0)


def test_stdev_basic() -> None:
    """Test standard deviation calculation."""
    # Constant series should have zero std
    series = pd.Series([10.0] * 10)
    stdev_result = stdev(series, window=5)
    assert len(stdev_result) == 10
    assert stdev_result.iloc[-1] == 0.0

    # Variable series should have positive std
    series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    stdev_result = stdev(series, window=10)
    assert stdev_result.iloc[-1] > 0


def test_macd_basic() -> None:
    """Test MACD calculation."""
    close = pd.Series(range(100, 150), dtype=float)
    macd_line, signal_line, histogram = macd(close, fast=12, slow=26, signal=9)
    assert len(macd_line) == len(close)
    assert len(signal_line) == len(close)
    assert len(histogram) == len(close)
    # MACD line should exist
    assert not macd_line.isna().all()


def test_macd_validation() -> None:
    """Test MACD parameter validation."""
    close = pd.Series([100, 101, 102])
    with pytest.raises(ValueError):
        macd(close, fast=0, slow=26, signal=9)
    with pytest.raises(ValueError):
        macd(close, fast=12, slow=10, signal=9)  # fast >= slow


def test_ema_empty_series() -> None:
    """Test EMA with empty series."""
    series = pd.Series(dtype=float)
    ema_result = ema(series, window=5)
    assert len(ema_result) == 0


def test_atr_empty_series() -> None:
    """Test ATR with empty series."""
    high = pd.Series(dtype=float)
    low = pd.Series(dtype=float)
    close = pd.Series(dtype=float)
    atr_result = atr(high, low, close, window=5)
    assert len(atr_result) == 0
