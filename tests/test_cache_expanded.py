"""Additional tests for cache module."""
from pathlib import Path

import pandas as pd
import pytest

from src.data.cache import ParquetCache


def test_cache_read_missing_file() -> None:
    """Test reading from non-existent cache file."""
    cache_dir = Path("/tmp/test_cache_read_missing")
    cache = ParquetCache(cache_dir)

    df = cache.read("NONEXISTENT")
    assert df.empty


def test_cache_read_with_timestamp_column() -> None:
    """Test reading cache with timestamp column instead of index."""
    cache_dir = Path("/tmp/test_cache_timestamp_col")
    cache_dir.mkdir(exist_ok=True, parents=True)
    cache = ParquetCache(cache_dir)

    # Write with timestamp column
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": dates,
            "open": range(100, 110),
            "high": range(101, 111),
            "low": range(99, 109),
            "close": range(100, 110),
            "volume": [1000] * 10,
        }
    )
    df = df.set_index("timestamp")
    cache.write("SPY", df)

    # Read should handle timestamp column
    result = cache.read("SPY")
    assert not result.empty


def test_cache_write_empty_dataframe() -> None:
    """Test writing empty DataFrame."""
    cache_dir = Path("/tmp/test_cache_write_empty")
    cache = ParquetCache(cache_dir)

    # Should not crash, just warn
    cache.write("SPY", pd.DataFrame())


def test_cache_write_missing_columns() -> None:
    """Test writing DataFrame with missing required columns."""
    cache_dir = Path("/tmp/test_cache_missing_cols")
    cache = ParquetCache(cache_dir)

    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": range(100, 110),
            "close": range(100, 110),
            # Missing high, low, volume
        },
        index=dates,
    )

    with pytest.raises(ValueError):
        cache.write("SPY", df)


def test_cache_write_duplicate_dates() -> None:
    """Test writing DataFrame with duplicate dates."""
    cache_dir = Path("/tmp/test_cache_duplicates")
    cache_dir.mkdir(exist_ok=True, parents=True)
    cache = ParquetCache(cache_dir)

    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    # Add duplicate
    dates_dup = list(dates) + [dates[0]]
    df = pd.DataFrame(
        {
            "open": range(100, 111),
            "high": range(101, 112),
            "low": range(99, 110),
            "close": range(100, 111),
            "volume": [1000] * 11,
        },
        index=pd.DatetimeIndex(dates_dup),
    )

    # Should handle duplicates by keeping first
    cache.write("SPY", df)
    result = cache.read("SPY")
    assert len(result) == 10  # Duplicate removed


def test_cache_append_empty_new_data() -> None:
    """Test appending empty DataFrame."""
    cache_dir = Path("/tmp/test_cache_append_empty")
    cache_dir.mkdir(exist_ok=True, parents=True)
    cache = ParquetCache(cache_dir)

    # Write initial data
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": range(100, 110),
            "high": range(101, 111),
            "low": range(99, 109),
            "close": range(100, 110),
            "volume": [1000] * 10,
        },
        index=dates,
    )
    cache.write("SPY", df)

    # Append empty - should not crash
    cache.append("SPY", pd.DataFrame())


def test_cache_append_all_dates_exist() -> None:
    """Test appending when all dates already exist."""
    cache_dir = Path("/tmp/test_cache_append_all_exist")
    cache_dir.mkdir(exist_ok=True, parents=True)
    cache = ParquetCache(cache_dir)

    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": range(100, 110),
            "high": range(101, 111),
            "low": range(99, 109),
            "close": range(100, 110),
            "volume": [1000] * 10,
        },
        index=dates,
    )
    cache.write("SPY", df)

    # Append same data - should be idempotent
    cache.append("SPY", df)
    result = cache.read("SPY")
    assert len(result) == 10  # No duplicates


def test_cache_append_with_timestamp_column() -> None:
    """Test appending with timestamp column."""
    cache_dir = Path("/tmp/test_cache_append_timestamp")
    cache_dir.mkdir(exist_ok=True, parents=True)
    cache = ParquetCache(cache_dir)

    # Write initial
    dates1 = pd.date_range("2020-01-01", periods=5, freq="D")
    df1 = pd.DataFrame(
        {
            "open": range(100, 105),
            "high": range(101, 106),
            "low": range(99, 104),
            "close": range(100, 105),
            "volume": [1000] * 5,
        },
        index=dates1,
    )
    cache.write("SPY", df1)

    # Append new data with timestamp column
    dates2 = pd.date_range("2020-01-06", periods=5, freq="D")
    df2 = pd.DataFrame(
        {
            "timestamp": dates2,
            "open": range(105, 110),
            "high": range(106, 111),
            "low": range(104, 109),
            "close": range(105, 110),
            "volume": [1000] * 5,
        }
    )
    cache.append("SPY", df2)

    result = cache.read("SPY")
    assert len(result) == 10


def test_cache_get_date_range_empty() -> None:
    """Test get_date_range with empty cache."""
    cache_dir = Path("/tmp/test_cache_date_range_empty")
    cache = ParquetCache(cache_dir)

    min_date, max_date = cache.get_date_range("NONEXISTENT")
    assert min_date is None
    assert max_date is None


def test_cache_get_date_range() -> None:
    """Test get_date_range with cached data."""
    cache_dir = Path("/tmp/test_cache_date_range")
    cache_dir.mkdir(exist_ok=True, parents=True)
    cache = ParquetCache(cache_dir)

    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": range(100, 110),
            "high": range(101, 111),
            "low": range(99, 109),
            "close": range(100, 110),
            "volume": [1000] * 10,
        },
        index=dates,
    )
    cache.write("SPY", df)

    min_date, max_date = cache.get_date_range("SPY")
    assert min_date == dates[0]
    assert max_date == dates[-1]
