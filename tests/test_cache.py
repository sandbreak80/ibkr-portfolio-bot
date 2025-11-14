"""Test Parquet cache functionality."""
from pathlib import Path

import pandas as pd
import pytest

from src.data.cache import ParquetCache


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture
def cache(cache_dir: Path) -> ParquetCache:
    """Create ParquetCache instance."""
    return ParquetCache(cache_dir)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Create sample OHLCV data."""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    return pd.DataFrame(
        {
            "open": range(100, 110),
            "high": range(101, 111),
            "low": range(99, 109),
            "close": range(100, 110),
            "volume": range(1000, 1010),
        },
        index=dates,
    )


def test_cache_write_read(cache: ParquetCache, sample_data: pd.DataFrame) -> None:
    """Test writing and reading cache."""
    cache.write("TEST", sample_data)
    df = cache.read("TEST")
    assert not df.empty
    assert len(df) == 10
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


def test_cache_append_idempotent(cache: ParquetCache, sample_data: pd.DataFrame) -> None:
    """Test idempotent append."""
    # Write initial data
    cache.write("TEST", sample_data)

    # Append same data (should not duplicate)
    cache.append("TEST", sample_data)
    df = cache.read("TEST")
    assert len(df) == 10  # Should still be 10, not 20

    # Append new data
    new_dates = pd.date_range("2024-01-11", periods=5, freq="D")
    new_data = pd.DataFrame(
        {
            "open": range(110, 115),
            "high": range(111, 116),
            "low": range(109, 114),
            "close": range(110, 115),
            "volume": range(1010, 1015),
        },
        index=new_dates,
    )
    cache.append("TEST", new_data)
    df = cache.read("TEST")
    assert len(df) == 15  # Should now be 15


def test_cache_date_range(cache: ParquetCache, sample_data: pd.DataFrame) -> None:
    """Test getting date range."""
    cache.write("TEST", sample_data)
    min_date, max_date = cache.get_date_range("TEST")
    assert min_date == sample_data.index.min()
    assert max_date == sample_data.index.max()


def test_cache_empty_read(cache: ParquetCache) -> None:
    """Test reading non-existent cache."""
    df = cache.read("NONEXISTENT")
    assert df.empty
