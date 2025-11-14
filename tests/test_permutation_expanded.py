"""Test permutation module expansion."""
from datetime import datetime

import numpy as np
import pandas as pd

from src.core.config import load_config
from src.strategy.permutation import permute_returns_joint, run_permutation_test


def test_permute_returns_joint_empty() -> None:
    """Test permutation with empty returns."""
    returns = pd.DataFrame()
    permuted = permute_returns_joint(returns, seed=42)
    assert permuted.empty


def test_permute_returns_joint_single_column() -> None:
    """Test permutation with single column."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    returns = pd.DataFrame({"SPY": np.random.randn(50)}, index=dates)
    permuted = permute_returns_joint(returns, seed=42)
    assert permuted.shape == returns.shape


def test_run_permutation_test_insufficient_data() -> None:
    """Test permutation test with insufficient data."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")  # Too few days
    data = {
        "SPY": pd.DataFrame(
            {
                "open": [100] * 10,
                "high": [101] * 10,
                "low": [99] * 10,
                "close": [100] * 10,
                "volume": [1000] * 10,
            },
            index=dates,
        )
    }

    returns = pd.DataFrame({"SPY": [0.001] * 10}, index=dates)

    config = load_config()
    config.selection.top_n = 1
    config.permutation.runs = 5

    train_start = datetime(2020, 1, 1)
    train_end = datetime(2020, 1, 5)

    result = run_permutation_test(data, returns, config, train_start, train_end, runs=5, seed=42)

    # Should handle insufficient data gracefully
    assert result is not None
