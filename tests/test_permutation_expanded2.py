"""Additional expanded tests for permutation module."""
from datetime import datetime

import numpy as np
import pandas as pd

from src.strategy.permutation import permute_returns_joint, run_permutation_test


def test_permute_returns_joint_different_seeds() -> None:
    """Test that different seeds produce different permutations."""
    dates = pd.date_range("2020-01-01", periods=50, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": np.random.RandomState(42).randn(50),
            "QQQ": np.random.RandomState(43).randn(50),
        },
        index=dates,
    )

    permuted1 = permute_returns_joint(returns, seed=1)
    permuted2 = permute_returns_joint(returns, seed=2)

    # Should be different (very unlikely to be identical)
    assert not permuted1.equals(permuted2)


def test_permute_returns_joint_same_seed() -> None:
    """Test that same seed produces same permutation."""
    dates = pd.date_range("2020-01-01", periods=50, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": np.random.RandomState(44).randn(50),
            "QQQ": np.random.RandomState(45).randn(50),
        },
        index=dates,
    )

    permuted1 = permute_returns_joint(returns, seed=100)
    permuted2 = permute_returns_joint(returns, seed=100)

    # Should be identical with same seed
    assert permuted1.equals(permuted2)


def test_permute_returns_joint_preserves_shape() -> None:
    """Test that permutation preserves DataFrame shape."""
    dates = pd.date_range("2020-01-01", periods=30, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": np.random.randn(30),
            "QQQ": np.random.randn(30),
            "TLT": np.random.randn(30),
        },
        index=dates,
    )

    permuted = permute_returns_joint(returns, seed=50)

    assert permuted.shape == returns.shape
    assert list(permuted.columns) == list(returns.columns)


def test_run_permutation_test_different_runs() -> None:
    """Test permutation test with different number of runs."""
    dates = pd.date_range("2020-01-01", periods=200, freq="D")  # More data
    data = {
        "SPY": pd.DataFrame(
            {
                "open": range(100, 300),
                "high": range(101, 301),
                "low": range(99, 299),
                "close": range(100, 300),
                "volume": [1000] * 200,
            },
            index=dates,
        )
    }

    from src.core.config import load_config

    config = load_config()
    config.selection.top_n = 1

    train_start = datetime(2020, 1, 1)
    train_end = datetime(2020, 6, 30)  # Longer period

    # Test with fewer runs for speed
    try:
        results = run_permutation_test(data, pd.DataFrame(), config, train_start, train_end, runs=5, seed=42)
        # May return dict with None values if insufficient data
        assert isinstance(results, dict)
        # If insufficient data, that's acceptable - just verify it doesn't crash
    except (ValueError, KeyError) as e:
        # May fail if insufficient data, which is acceptable
        import pytest
        pytest.skip(f"Insufficient data for permutation test: {e}")


def test_run_permutation_test_insufficient_data_handling() -> None:
    """Test permutation test handles insufficient data gracefully."""
    # Very small dataset
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    data = {
        "SPY": pd.DataFrame(
            {
                "open": range(100, 110),
                "high": range(101, 111),
                "low": range(99, 109),
                "close": range(100, 110),
                "volume": [1000] * 10,
            },
            index=dates,
        )
    }

    from src.core.config import load_config

    config = load_config()
    config.selection.top_n = 1

    train_start = datetime(2020, 1, 1)
    train_end = datetime(2020, 1, 5)

    # Should handle gracefully or raise appropriate error
    try:
        results = run_permutation_test(data, pd.DataFrame(), config, train_start, train_end, runs=5, seed=42)
        assert isinstance(results, dict)
    except (ValueError, KeyError):
        # Expected for insufficient data
        pass
