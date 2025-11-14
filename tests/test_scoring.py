"""Test scoring function."""
import pandas as pd
import pytest

from src.features.scoring import calculate_score, calculate_scores_for_dataframe


def test_score_basic() -> None:
    """Test score calculation with simple data."""
    close = pd.Series([100, 105, 110])
    ema_fast = pd.Series([100, 102, 104])
    atr_values = pd.Series([2, 2, 2])

    scores = calculate_score(close, ema_fast, atr_values)
    assert len(scores) == 3
    # First score should be 0 (close == ema)
    assert abs(scores.iloc[0]) < 1e-6
    # Later scores should be positive (close > ema)
    assert scores.iloc[-1] > 0


def test_score_with_dataframe() -> None:
    """Test score calculation from DataFrame."""
    dates = pd.date_range("2024-01-01", periods=25, freq="D")
    df = pd.DataFrame(
        {
            "open": range(100, 125),
            "high": range(101, 126),
            "low": range(99, 124),
            "close": range(100, 125),
            "volume": range(1000, 1025),
        },
        index=dates,
    )

    scores = calculate_scores_for_dataframe(df, ema_fast_window=20, atr_window=20)
    assert len(scores) == 25
    assert not scores.isna().all()


def test_score_empty_dataframe() -> None:
    """Test score calculation with empty DataFrame."""
    df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    scores = calculate_scores_for_dataframe(df)
    assert len(scores) == 0


def test_score_missing_columns() -> None:
    """Test score calculation with missing columns."""
    df = pd.DataFrame({"close": [100, 101, 102]})
    with pytest.raises(ValueError):
        calculate_scores_for_dataframe(df)
