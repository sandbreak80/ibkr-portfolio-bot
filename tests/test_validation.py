"""Tests for data validation."""
import pandas as pd
import pytest

from src.data.validation import (
    DataValidationError,
    check_data_quality_batch,
    validate_bars,
    validate_bars_safe,
)


def create_valid_bars(num_bars: int = 10) -> pd.DataFrame:
    """Create valid OHLCV data for testing."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=num_bars, freq="1D")
    df = pd.DataFrame({
        "open": [100.0 + i for i in range(num_bars)],
        "high": [102.0 + i for i in range(num_bars)],
        "low": [99.0 + i for i in range(num_bars)],
        "close": [101.0 + i for i in range(num_bars)],
        "volume": [1000000 + i * 1000 for i in range(num_bars)],
    }, index=dates)
    return df


def test_validate_bars_valid_data() -> None:
    """Test validation passes for valid data."""
    df = create_valid_bars()
    assert validate_bars(df, "TEST") is True


def test_validate_bars_empty_dataframe() -> None:
    """Test validation fails for empty DataFrame."""
    df = pd.DataFrame()
    with pytest.raises(DataValidationError, match="DataFrame is empty"):
        validate_bars(df, "TEST")


def test_validate_bars_missing_columns() -> None:
    """Test validation fails for missing columns."""
    df = pd.DataFrame({
        "open": [100],
        "high": [102],
        # Missing low, close, volume
    })
    with pytest.raises(DataValidationError, match="Missing required columns"):
        validate_bars(df, "TEST")


def test_validate_bars_nan_values() -> None:
    """Test validation fails for NaN values."""
    df = create_valid_bars()
    df.loc[df.index[0], "close"] = float("nan")
    with pytest.raises(DataValidationError, match="NaN values found"):
        validate_bars(df, "TEST")


def test_validate_bars_invalid_high_low() -> None:
    """Test validation fails when high < close."""
    df = create_valid_bars()
    df.loc[df.index[0], "high"] = 50.0  # Less than close
    with pytest.raises(DataValidationError, match="high < close"):
        validate_bars(df, "TEST")


def test_validate_bars_invalid_low_close() -> None:
    """Test validation fails when low > close."""
    df = create_valid_bars()
    df.loc[df.index[0], "low"] = 200.0  # Greater than close
    with pytest.raises(DataValidationError, match="low > close"):
        validate_bars(df, "TEST")


def test_validate_bars_invalid_high_open() -> None:
    """Test validation fails when high < open."""
    df = create_valid_bars()
    # Make high < open, but keep relationships valid otherwise
    df.loc[df.index[0], "open"] = 105.0
    df.loc[df.index[0], "high"] = 102.0  # Less than open
    df.loc[df.index[0], "close"] = 101.0
    df.loc[df.index[0], "low"] = 99.0
    with pytest.raises(DataValidationError, match="high < open"):
        validate_bars(df, "TEST")


def test_validate_bars_invalid_low_open() -> None:
    """Test validation fails when low > open."""
    df = create_valid_bars()
    # Make low > open, but keep relationships valid otherwise
    df.loc[df.index[0], "open"] = 99.5
    df.loc[df.index[0], "high"] = 102.0
    df.loc[df.index[0], "close"] = 101.0
    df.loc[df.index[0], "low"] = 100.0  # Greater than open
    with pytest.raises(DataValidationError, match="low > open"):
        validate_bars(df, "TEST")


def test_validate_bars_zero_volume() -> None:
    """Test validation fails for zero volume (except first bar)."""
    df = create_valid_bars()
    df.loc[df.index[1], "volume"] = 0  # Zero volume on second bar
    with pytest.raises(DataValidationError, match="Zero/negative volume"):
        validate_bars(df, "TEST")


def test_validate_bars_zero_volume_first_bar_ok() -> None:
    """Test validation allows zero volume on first bar."""
    df = create_valid_bars()
    df.loc[df.index[0], "volume"] = 0
    assert validate_bars(df, "TEST") is True


def test_validate_bars_negative_volume() -> None:
    """Test validation fails for negative volume."""
    df = create_valid_bars()
    df.loc[df.index[1], "volume"] = -1000  # Second bar (first bar can be zero)
    with pytest.raises(DataValidationError, match="Zero/negative volume"):
        validate_bars(df, "TEST")


def test_validate_bars_stale_data() -> None:
    """Test validation fails for stale data."""
    # Create bars from 10 days ago
    dates = pd.date_range(
        end=pd.Timestamp.now() - pd.Timedelta(days=10),
        periods=5,
        freq="1D"
    )
    df = pd.DataFrame({
        "open": [100.0] * 5,
        "high": [102.0] * 5,
        "low": [99.0] * 5,
        "close": [101.0] * 5,
        "volume": [1000000] * 5,
    }, index=dates)

    with pytest.raises(DataValidationError, match="Stale data"):
        validate_bars(df, "TEST", max_staleness_days=2)


def test_validate_bars_large_price_jump_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Test validation warns but doesn't fail for large price jumps."""
    df = create_valid_bars()
    # Create 60% price jump (suspicious but could be legitimate)
    df.loc[df.index[1], "close"] = df.loc[df.index[0], "close"] * 1.6
    df.loc[df.index[1], "high"] = df.loc[df.index[1], "close"] + 1

    # Should pass but log warning
    assert validate_bars(df, "TEST") is True
    assert "Large price jumps" in caplog.text


def test_validate_bars_safe_valid() -> None:
    """Test safe wrapper returns True for valid data."""
    df = create_valid_bars()
    is_valid, error = validate_bars_safe(df, "TEST")
    assert is_valid is True
    assert error == ""


def test_validate_bars_safe_invalid() -> None:
    """Test safe wrapper returns False and error message for invalid data."""
    df = pd.DataFrame()
    is_valid, error = validate_bars_safe(df, "TEST")
    assert is_valid is False
    assert "DataFrame is empty" in error


def test_validate_bars_safe_unexpected_error() -> None:
    """Test safe wrapper catches unexpected errors."""
    # Pass invalid type to trigger unexpected error
    is_valid, error = validate_bars_safe(None, "TEST")  # type: ignore
    assert is_valid is False
    assert "Unexpected validation error" in error


def test_check_data_quality_batch_all_valid() -> None:
    """Test batch validation with all valid symbols."""
    data = {
        "SPY": create_valid_bars(),
        "QQQ": create_valid_bars(),
        "IWM": create_valid_bars(),
    }
    failures = check_data_quality_batch(data)
    assert len(failures) == 0


def test_check_data_quality_batch_some_invalid() -> None:
    """Test batch validation with some invalid symbols."""
    data = {
        "SPY": create_valid_bars(),
        "QQQ": pd.DataFrame(),  # Empty (invalid)
        "IWM": create_valid_bars(),
    }
    failures = check_data_quality_batch(data)
    assert len(failures) == 1
    assert "QQQ" in failures
    assert "DataFrame is empty" in failures["QQQ"]


def test_check_data_quality_batch_all_invalid() -> None:
    """Test batch validation with all invalid symbols."""
    data = {
        "SPY": pd.DataFrame(),
        "QQQ": pd.DataFrame(),
        "IWM": pd.DataFrame(),
    }
    failures = check_data_quality_batch(data)
    assert len(failures) == 3
    assert all(sym in failures for sym in ["SPY", "QQQ", "IWM"])


def test_validate_bars_non_datetime_index() -> None:
    """Test validation works with non-datetime index (skips staleness check)."""
    df = pd.DataFrame({
        "open": [100.0, 101.0],
        "high": [102.0, 103.0],
        "low": [99.0, 100.0],
        "close": [101.0, 102.0],
        "volume": [1000000, 1001000],
    })
    # Should pass (no staleness check without DatetimeIndex)
    assert validate_bars(df, "TEST") is True


def test_validate_bars_custom_staleness() -> None:
    """Test validation with custom staleness threshold."""
    # Create bars from 5 days ago
    dates = pd.date_range(
        end=pd.Timestamp.now() - pd.Timedelta(days=5),
        periods=5,
        freq="1D"
    )
    df = pd.DataFrame({
        "open": [100.0] * 5,
        "high": [102.0] * 5,
        "low": [99.0] * 5,
        "close": [101.0] * 5,
        "volume": [1000000] * 5,
    }, index=dates)

    # Should fail with 2-day threshold
    with pytest.raises(DataValidationError, match="Stale data"):
        validate_bars(df, "TEST", max_staleness_days=2)

    # Should pass with 10-day threshold
    assert validate_bars(df, "TEST", max_staleness_days=10) is True

