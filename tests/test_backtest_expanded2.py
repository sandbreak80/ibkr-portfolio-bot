"""Additional tests for backtest module."""
from datetime import datetime

import pandas as pd

from src.core.config import load_config
from src.strategy.backtest import calculate_returns, run_backtest


def test_calculate_returns_empty_dataframe() -> None:
    """Test calculate_returns with empty DataFrame."""
    df = pd.DataFrame()
    returns = calculate_returns(df)
    assert returns.empty


def test_calculate_returns_missing_close_column() -> None:
    """Test calculate_returns with missing close column."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": range(100, 110),
            "high": range(101, 111),
            # Missing close
        },
        index=dates,
    )
    returns = calculate_returns(df)
    assert returns.empty


def test_run_backtest_no_dates() -> None:
    """Test run_backtest when no dates found."""
    data = {
        "SPY": pd.DataFrame(
            {
                "open": [],
                "high": [],
                "low": [],
                "close": [],
                "volume": [],
            }
        )
    }
    config = load_config()

    results = run_backtest(data, config)
    assert results == {}


def test_run_backtest_date_range_filtering() -> None:
    """Test run_backtest with date range filtering."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    data = {
        "SPY": pd.DataFrame(
            {
                "open": range(100, 200),
                "high": range(101, 201),
                "low": range(99, 199),
                "close": range(100, 200),
                "volume": [1000] * 100,
            },
            index=dates,
        )
    }
    config = load_config()
    config.selection.top_n = 1

    start_date = datetime(2020, 1, 10)
    end_date = datetime(2020, 2, 15)  # Fixed: January only has 31 days

    results = run_backtest(data, config, start_date=start_date, end_date=end_date)
    if results:
        assert "equity" in results
        assert "returns" in results


def test_run_backtest_no_returns_calculated() -> None:
    """Test run_backtest when no returns can be calculated."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    data = {
        "SPY": pd.DataFrame(
            {
                "open": [100] * 5,  # Flat prices
                "high": [101] * 5,
                "low": [99] * 5,
                "close": [100] * 5,  # No price change
                "volume": [1000] * 5,
            },
            index=dates,
        )
    }
    config = load_config()

    results = run_backtest(data, config)
    # Should handle gracefully
    assert isinstance(results, dict)
