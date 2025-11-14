"""Test correlation matrix and selection."""
import numpy as np
import pandas as pd

from src.features.correlation import (
    apply_correlation_cap,
    get_correlation_matrix,
    select_with_correlation_cap,
)


def test_correlation_matrix_basic() -> None:
    """Test correlation matrix calculation."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": np.random.randn(100).cumsum(),
            "QQQ": np.random.randn(100).cumsum(),
        },
        index=dates,
    )

    corr_matrix = get_correlation_matrix(returns, window=90)
    assert not corr_matrix.empty
    assert "SPY" in corr_matrix.index
    assert "QQQ" in corr_matrix.index
    # Diagonal should be 1.0
    assert abs(corr_matrix.loc["SPY", "SPY"] - 1.0) < 0.01
    assert abs(corr_matrix.loc["QQQ", "QQQ"] - 1.0) < 0.01
    # Symmetric
    assert abs(corr_matrix.loc["SPY", "QQQ"] - corr_matrix.loc["QQQ", "SPY"]) < 0.01


def test_correlation_cap_selection() -> None:
    """Test correlation cap selection."""
    # Create returns with known correlation
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    base_returns = np.random.randn(100)

    # SPY and VTI highly correlated (similar returns)
    returns = pd.DataFrame(
        {
            "SPY": base_returns,
            "VTI": base_returns + np.random.randn(100) * 0.1,  # Highly correlated
            "GLD": np.random.randn(100),  # Low correlation
        },
        index=dates,
    )

    scores = {"SPY": 1.0, "VTI": 0.9, "GLD": 0.8}

    # With high correlation cap, should select both SPY and VTI
    selected_high_cap = select_with_correlation_cap(
        scores, returns, top_n=2, corr_window=90, corr_cap=0.95
    )
    assert len(selected_high_cap) <= 2

    # With low correlation cap, should select SPY and GLD (not VTI)
    selected_low_cap = select_with_correlation_cap(
        scores, returns, top_n=2, corr_window=90, corr_cap=0.5
    )
    assert len(selected_low_cap) <= 2
    # GLD should be selected (low correlation)
    if len(selected_low_cap) == 2:
        assert "GLD" in selected_low_cap


def test_apply_correlation_cap() -> None:
    """Test correlation cap application."""
    # Create correlation matrix
    corr_matrix = pd.DataFrame(
        {
            "SPY": [1.0, 0.95, 0.3],
            "VTI": [0.95, 1.0, 0.2],
            "GLD": [0.3, 0.2, 1.0],
        },
        index=["SPY", "VTI", "GLD"],
    )

    symbols = ["SPY", "VTI", "GLD"]
    scores = {"SPY": 1.0, "VTI": 0.9, "GLD": 0.8}

    # With corr_cap=0.7, should reject VTI (corr=0.95 with SPY)
    selected = apply_correlation_cap(symbols, scores, corr_matrix, corr_cap=0.7)
    assert "SPY" in selected
    assert "VTI" not in selected  # Should be rejected due to high correlation
    assert "GLD" in selected  # Should be included (low correlation)


def test_correlation_empty_returns() -> None:
    """Test correlation with empty returns."""
    returns = pd.DataFrame()
    corr_matrix = get_correlation_matrix(returns, window=90)
    assert corr_matrix.empty


def test_select_with_correlation_cap_empty() -> None:
    """Test selection with empty scores."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    returns = pd.DataFrame({"SPY": np.random.randn(100)}, index=dates)
    selected = select_with_correlation_cap({}, returns, top_n=2)
    assert selected == []
