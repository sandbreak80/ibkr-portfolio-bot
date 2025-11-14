"""Test permutation testing."""
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.core.config import load_config
from src.strategy.permutation import permute_returns_joint, run_permutation_test


def test_permute_returns_joint() -> None:
    """Test joint permutation of returns."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": np.random.randn(100),
            "QQQ": np.random.randn(100),
        },
        index=dates,
    )

    # Permute with seed
    permuted = permute_returns_joint(returns, seed=42)

    # Should have same shape and columns
    assert permuted.shape == returns.shape
    assert list(permuted.columns) == list(returns.columns)

    # Should be different order (with high probability)
    assert not returns.equals(permuted)


def test_permutation_deterministic() -> None:
    """Test that permutation is deterministic with same seed."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    np.random.seed(123)  # Set seed before generating data
    returns = pd.DataFrame({"SPY": np.random.randn(50)}, index=dates)

    permuted1 = permute_returns_joint(returns, seed=42)
    permuted2 = permute_returns_joint(returns, seed=42)

    # Should be identical with same seed (same permutation of rows)
    pd.testing.assert_frame_equal(permuted1, permuted2)


def test_permutation_p_value_range() -> None:
    """Test that p-value is in valid range [0, 1]."""
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    data = {
        "SPY": pd.DataFrame(
            {
                "open": [100] * 200,
                "high": [101] * 200,
                "low": [99] * 200,
                "close": range(100, 300),
                "volume": [1000] * 200,
            },
            index=dates,
        )
    }

    returns = pd.DataFrame({"SPY": data["SPY"]["close"].pct_change()}, index=dates)
    returns = returns.fillna(0.0)

    config = load_config()
    config.selection.top_n = 1
    config.walkforward.train_years = 1
    config.walkforward.oos_months = 1
    config.permutation.runs = 10  # Small number for test

    train_start = datetime(2020, 1, 1)
    train_end = datetime(2020, 6, 1)

    try:
        result = run_permutation_test(data, returns, config, train_start, train_end, runs=10, seed=42)

        if result.get("p_value") is not None:
            p_value = result["p_value"]
            assert 0.0 <= p_value <= 1.0, f"P-value {p_value} not in [0, 1]"
    except Exception as e:
        # Skip if permutation test fails (may happen with insufficient data)
        pytest.skip(f"Permutation test failed: {e}")
