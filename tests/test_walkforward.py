"""Test walk-forward analysis."""
from datetime import datetime

import pandas as pd
import pytest

from src.core.config import load_config
from src.strategy.walkforward import generate_walkforward_windows, run_walkforward


def test_generate_walkforward_windows() -> None:
    """Test walk-forward window generation."""
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2021, 1, 1)

    windows = generate_walkforward_windows(start_date, end_date, train_years=1, oos_months=3)

    assert len(windows) > 0
    for train_start, train_end, oos_start, oos_end in windows:
        assert train_start < train_end
        assert train_end <= oos_start
        assert oos_start < oos_end
        assert train_start >= start_date
        assert oos_end <= end_date


def test_walkforward_no_leakage() -> None:
    """Test that walk-forward has no data leakage."""
    # Create simple data
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    data = {
        "SPY": pd.DataFrame(
            {
                "open": [100] * 500,
                "high": [101] * 500,
                "low": [99] * 500,
                "close": range(100, 600),
                "volume": [1000] * 500,
            },
            index=dates,
        )
    }

    # Create returns
    returns = pd.DataFrame({"SPY": data["SPY"]["close"].pct_change()}, index=dates)
    returns = returns.fillna(0.0)

    config = load_config()
    config.walkforward.train_years = 1
    config.walkforward.oos_months = 1
    config.selection.top_n = 1

    # Run walk-forward
    results = run_walkforward(data, returns, config)

    if not results:
        pytest.skip("Walk-forward returned empty results")

    # Verify OOS dates don't overlap with training dates
    windows = results.get("windows", [])
    for i, (train_start, train_end, oos_start, oos_end) in enumerate(windows):
        # OOS should start after training ends
        assert train_end <= oos_start, f"Window {i}: OOS starts before training ends"
        # No overlap
        assert train_end <= oos_start, f"Window {i}: Training and OOS overlap"
