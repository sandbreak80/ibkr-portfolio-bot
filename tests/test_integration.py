"""Integration tests for end-to-end workflows."""
import pandas as pd

from src.core.config import load_config
from src.strategy.backtest import run_backtest
from src.strategy.selector import select_assets
from src.strategy.weighting import calculate_weights


def test_end_to_end_backtest() -> None:
    """Test end-to-end backtest workflow."""
    # Create sample data
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
        ),
        "QQQ": pd.DataFrame(
            {
                "open": range(200, 300),
                "high": range(201, 301),
                "low": range(199, 299),
                "close": range(200, 300),
                "volume": [1000] * 100,
            },
            index=dates,
        ),
    }

    config = load_config()
    config.selection.top_n = 2

    # Calculate returns
    returns_dict = {}
    for symbol, df in data.items():
        returns = df["close"].pct_change()
        returns_dict[symbol] = returns

    returns = pd.DataFrame(returns_dict)
    returns = returns.fillna(0.0)

    # Run backtest
    results = run_backtest(data, config)

    assert results is not None
    assert "equity" in results
    assert "returns" in results
    assert not results["equity"].empty


def test_end_to_end_selection_and_weights() -> None:
    """Test end-to-end selection and weighting."""
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
        ),
        "QQQ": pd.DataFrame(
            {
                "open": range(200, 300),
                "high": range(201, 301),
                "low": range(199, 299),
                "close": range(200, 300),
                "volume": [1000] * 100,
            },
            index=dates,
        ),
    }

    config = load_config()
    config.selection.top_n = 2

    # Calculate returns
    returns_dict = {}
    for symbol, df in data.items():
        returns = df["close"].pct_change()
        returns_dict[symbol] = returns

    returns = pd.DataFrame(returns_dict)
    returns = returns.fillna(0.0)

    # Select assets
    selected = select_assets(data, returns, config)

    # Calculate weights
    if selected:
        weights = calculate_weights(selected, returns, config)
        assert len(weights) > 0
        total_weight = sum(weights.values())
        expected_total = 1.0 - config.weights.cash_buffer
        assert abs(total_weight - expected_total) < 0.01
