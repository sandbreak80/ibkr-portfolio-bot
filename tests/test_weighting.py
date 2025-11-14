"""Test portfolio weighting."""
import numpy as np
import pandas as pd
import pytest

from src.core.config import load_config
from src.strategy.weighting import (
    apply_cash_buffer,
    apply_weight_caps,
    calculate_inverse_vol_weights,
    calculate_weights,
)


def test_inverse_vol_weights() -> None:
    """Test inverse-volatility weight calculation."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    returns = pd.DataFrame(
        {
            "LOW_VOL": np.random.randn(50) * 0.01,  # Low volatility
            "HIGH_VOL": np.random.randn(50) * 0.05,  # High volatility
        },
        index=dates,
    )

    weights = calculate_inverse_vol_weights(["LOW_VOL", "HIGH_VOL"], returns, vol_window=20)
    assert len(weights) == 2
    # LOW_VOL should have higher weight (lower volatility)
    assert weights["LOW_VOL"] > weights["HIGH_VOL"]


def test_apply_weight_caps() -> None:
    """Test weight cap application."""
    weights = {"A": 0.6, "B": 0.4}  # A exceeds 0.5 cap
    capped = apply_weight_caps(weights, max_weight_per_asset=0.5)
    assert capped["A"] <= 0.5
    assert sum(capped.values()) == pytest.approx(1.0, abs=0.01)


def test_apply_cash_buffer() -> None:
    """Test cash buffer application."""
    weights = {"A": 0.5, "B": 0.5}
    buffered = apply_cash_buffer(weights, cash_buffer=0.05)
    total = sum(buffered.values())
    assert total == pytest.approx(0.95, abs=0.01)


def test_calculate_weights_integration() -> None:
    """Test full weight calculation."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": np.random.randn(50) * 0.02,
            "QQQ": np.random.randn(50) * 0.02,
        },
        index=dates,
    )

    config = load_config()
    weights = calculate_weights(["SPY", "QQQ"], returns, config)
    assert len(weights) == 2
    total = sum(weights.values())
    expected_total = 1.0 - config.weights.cash_buffer
    assert total == pytest.approx(expected_total, abs=0.01)
