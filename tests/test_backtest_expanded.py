"""Test backtest module expansion."""
from datetime import datetime

import pandas as pd

from src.core.config import load_config
from src.strategy.backtest import calculate_costs, calculate_returns, run_backtest


def test_calculate_returns_multiindex() -> None:
    """Test returns calculation with MultiIndex."""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    index = pd.MultiIndex.from_product([["SPY", "QQQ"], dates], names=["symbol", "date"])
    df = pd.DataFrame(
        {
            "open": range(100, 120),
            "high": range(101, 121),
            "low": range(99, 119),
            "close": range(100, 120),
            "volume": [1000] * 20,
        },
        index=index,
    )

    returns = calculate_returns(df)
    assert not returns.empty


def test_calculate_costs_with_prices() -> None:
    """Test cost calculation with price series."""
    turnover = pd.Series([0.1, 0.2, 0.0])
    prices = pd.Series([100, 101, 102])
    costs = calculate_costs(turnover, commission_per_share=0.0035, slippage_bps=1.0, prices=prices)
    assert len(costs) == 3
    assert all(costs >= 0)


def test_run_backtest_with_date_range() -> None:
    """Test backtest with specific date range."""
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
    end_date = datetime(2020, 1, 30)

    results = run_backtest(data, config, start_date, end_date)

    if results:
        equity = results.get("equity", pd.Series())
        assert not equity.empty


def test_run_backtest_empty_data() -> None:
    """Test backtest with empty data."""
    config = load_config()
    results = run_backtest({}, config)
    assert results == {}


def test_run_backtest_single_symbol() -> None:
    """Test backtest with single symbol."""
    dates = pd.date_range("2020-01-01", periods=50, freq="D")
    data = {
        "SPY": pd.DataFrame(
            {
                "open": range(100, 150),
                "high": range(101, 151),
                "low": range(99, 149),
                "close": range(100, 150),
                "volume": [1000] * 50,
            },
            index=dates,
        )
    }

    config = load_config()
    config.selection.top_n = 1

    results = run_backtest(data, config)

    if results:
        assert "equity" in results
        assert "returns" in results
