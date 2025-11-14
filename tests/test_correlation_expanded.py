"""Expanded tests for correlation module."""
import pandas as pd

from src.features.correlation import get_correlation_matrix, select_with_correlation_cap


def test_correlation_matrix_single_asset() -> None:
    """Test correlation matrix with single asset."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.DataFrame({"SPY": pd.Series(0.001, index=dates)})

    corr_matrix = get_correlation_matrix(returns, window=30)
    assert not corr_matrix.empty
    assert "SPY" in corr_matrix.columns


def test_correlation_matrix_small_window() -> None:
    """Test correlation matrix with small window."""
    dates = pd.date_range("2020-01-01", periods=50, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": pd.Series(0.001, index=dates),
            "QQQ": pd.Series(0.001, index=dates),
        }
    )

    corr_matrix = get_correlation_matrix(returns, window=10)
    assert not corr_matrix.empty


def test_correlation_matrix_specific_date() -> None:
    """Test correlation matrix at specific date."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": pd.Series(0.001, index=dates),
            "QQQ": pd.Series(0.001, index=dates),
        }
    )

    target_date = pd.Timestamp("2020-02-01")
    corr_matrix = get_correlation_matrix(returns, window=30, date=target_date)
    assert not corr_matrix.empty


def test_select_with_correlation_cap_high_correlation() -> None:
    """Test selection with high correlation assets."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": pd.Series(0.001, index=dates),
            "QQQ": pd.Series(0.001, index=dates),  # Highly correlated
            "TLT": pd.Series(-0.001, index=dates),  # Negatively correlated
        }
    )

    scores = {"SPY": 1.0, "QQQ": 0.9, "TLT": 0.8}

    selected = select_with_correlation_cap(scores, returns, top_n=2, corr_cap=0.7, corr_window=30)
    # Should select assets with lower correlation
    assert len(selected) <= 2


def test_select_with_correlation_cap_all_high_corr() -> None:
    """Test selection when all assets are highly correlated."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": pd.Series(0.001, index=dates),
            "QQQ": pd.Series(0.001, index=dates),
            "VTI": pd.Series(0.001, index=dates),
        }
    )

    scores = {"SPY": 1.0, "QQQ": 0.9, "VTI": 0.8}

    selected = select_with_correlation_cap(scores, returns, top_n=3, corr_cap=0.5, corr_window=30)
    # Should still select some assets even if all are correlated
    assert len(selected) > 0


def test_select_with_correlation_cap_specific_date() -> None:
    """Test selection at specific date."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.DataFrame(
        {
            "SPY": pd.Series(0.001, index=dates),
            "QQQ": pd.Series(0.001, index=dates),
        }
    )

    scores = {"SPY": 1.0, "QQQ": 0.9}
    target_date = pd.Timestamp("2020-02-01")

    selected = select_with_correlation_cap(scores, returns, top_n=2, corr_cap=0.7, corr_window=30, date=target_date)
    assert len(selected) <= 2
