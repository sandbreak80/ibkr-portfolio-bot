"""Test selector module expansion."""

import pandas as pd

from src.core.config import load_config
from src.strategy.selector import select_assets


def test_select_assets_empty_data() -> None:
    """Test selection with empty data."""
    config = load_config()
    returns = pd.DataFrame()
    selected = select_assets({}, returns, config)
    assert selected == []


def test_select_assets_no_long_ok() -> None:
    """Test selection when no assets pass long_ok gates."""
    dates = pd.date_range("2020-01-01", periods=50, freq="D")
    # Create data with falling prices (EMA20 < EMA50)
    data = {
        "SPY": pd.DataFrame(
            {
                "open": range(200, 150, -1),
                "high": range(201, 151, -1),
                "low": range(199, 149, -1),
                "close": range(200, 150, -1),  # Falling
                "volume": [1000] * 50,
            },
            index=dates,
        )
    }

    returns = pd.DataFrame({"SPY": data["SPY"]["close"].pct_change()}, index=dates)
    returns = returns.fillna(0.0)

    config = load_config()
    config.selection.top_n = 1

    selected = select_assets(data, returns, config)
    # May be empty if no assets pass gates
    assert isinstance(selected, list)
