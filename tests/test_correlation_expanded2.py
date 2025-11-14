"""Additional tests for correlation module."""
import pandas as pd
import pytest

from src.features.correlation import get_correlation_matrix


def test_get_correlation_matrix_empty_returns() -> None:
    """Test get_correlation_matrix with empty returns."""
    returns = pd.DataFrame()
    corr_matrix = get_correlation_matrix(returns)
    assert corr_matrix.empty


def test_get_correlation_matrix_single_column() -> None:
    """Test get_correlation_matrix with single column."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.DataFrame({"SPY": pd.Series(0.001, index=dates)})
    
    corr_matrix = get_correlation_matrix(returns, window=30)
    # Single column should return 1x1 matrix
    assert not corr_matrix.empty


def test_get_correlation_matrix_insufficient_data() -> None:
    """Test get_correlation_matrix with insufficient data."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")  # Less than window
    returns = pd.DataFrame(
        {
            "SPY": pd.Series(0.001, index=dates),
            "QQQ": pd.Series(0.001, index=dates),
        }
    )
    
    corr_matrix = get_correlation_matrix(returns, window=30)
    # Should handle insufficient data gracefully
    assert isinstance(corr_matrix, pd.DataFrame)


def test_get_correlation_matrix_date_before_data() -> None:
    """Test get_correlation_matrix with date before any data."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": pd.Series(0.001, index=dates),
            "QQQ": pd.Series(0.001, index=dates),
        }
    )
    
    target_date = pd.Timestamp("2019-01-01")  # Before data
    corr_matrix = get_correlation_matrix(returns, window=30, date=target_date)
    # Should handle gracefully
    assert isinstance(corr_matrix, pd.DataFrame)
