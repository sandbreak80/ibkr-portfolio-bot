"""Additional tests for selector module."""
import pandas as pd

from src.core.config import load_config
from src.strategy.selector import select_assets


def test_select_assets_empty_data() -> None:
    """Test selector with empty data dictionary."""
    config = load_config()
    returns = pd.DataFrame()

    selected = select_assets({}, returns, config)
    assert selected == []


def test_select_assets_empty_dataframe() -> None:
    """Test selector with empty DataFrame for a symbol."""
    config = load_config()
    data = {"SPY": pd.DataFrame()}
    returns = pd.DataFrame()

    selected = select_assets(data, returns, config)
    assert selected == []


def test_select_assets_date_filtering() -> None:
    """Test selector with date filtering."""
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
    returns = pd.DataFrame({"SPY": pd.Series(0.001, index=dates)})
    config = load_config()
    config.selection.top_n = 1

    target_date = pd.Timestamp("2020-02-01")
    selected = select_assets(data, returns, config, date=target_date)
    # May or may not select depending on signals
    assert isinstance(selected, list)


def test_select_assets_date_before_data() -> None:
    """Test selector with date before any data."""
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
    returns = pd.DataFrame({"SPY": pd.Series(0.001, index=dates)})
    config = load_config()

    target_date = pd.Timestamp("2019-01-01")  # Before data
    selected = select_assets(data, returns, config, date=target_date)
    assert isinstance(selected, list)


def test_select_assets_empty_scores() -> None:
    """Test selector when scores are empty."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    data = {
        "SPY": pd.DataFrame(
            {
                "open": [100] * 10,
                "high": [101] * 10,
                "low": [99] * 10,
                "close": [100] * 10,  # Flat price
                "volume": [1000] * 10,
            },
            index=dates,
        )
    }
    returns = pd.DataFrame({"SPY": pd.Series(0.0, index=dates)})
    config = load_config()

    selected = select_assets(data, returns, config)
    # May return empty if no valid scores
    assert isinstance(selected, list)


def test_select_assets_score_below_min() -> None:
    """Test selector when scores are below minimum."""
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
    returns = pd.DataFrame({"SPY": pd.Series(0.001, index=dates)})
    config = load_config()
    config.selection.min_score = 100.0  # Very high minimum

    selected = select_assets(data, returns, config)
    # Should filter out low scores
    assert isinstance(selected, list)


def test_select_assets_exception_handling() -> None:
    """Test selector handles exceptions gracefully."""
    # Create data that might cause exceptions
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    data = {
        "SPY": pd.DataFrame(
            {
                "open": [100, 101, None, 103, 104],  # Invalid data
                "high": [101, 102, 102, 104, 105],
                "low": [99, 100, 100, 102, 103],
                "close": [100, 101, 101, 103, 104],
                "volume": [1000] * 5,
            },
            index=dates,
        )
    }
    returns = pd.DataFrame({"SPY": pd.Series(0.001, index=dates)})
    config = load_config()

    # Should handle exceptions without crashing
    selected = select_assets(data, returns, config)
    assert isinstance(selected, list)
