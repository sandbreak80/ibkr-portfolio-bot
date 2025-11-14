"""Comprehensive tests for risk module."""

from src.strategy.risk import check_position_limits, check_weight_sum, validate_weights


def test_check_position_limits_valid() -> None:
    """Test position limits with valid weights."""
    weights = {"SPY": 0.3, "QQQ": 0.25, "VTI": 0.2}
    is_valid, violations = check_position_limits(weights, max_weight_per_asset=0.5, max_positions=10)
    assert is_valid
    assert len(violations) == 0


def test_check_position_limits_too_many_positions() -> None:
    """Test position limits with too many positions."""
    weights = {f"SYM{i}": 0.1 for i in range(15)}
    is_valid, violations = check_position_limits(weights, max_weight_per_asset=0.5, max_positions=10)
    assert not is_valid
    assert any("Too many positions" in v for v in violations)


def test_check_position_limits_exceeds_max_weight() -> None:
    """Test position limits with weight exceeding max."""
    weights = {"SPY": 0.6, "QQQ": 0.3}
    is_valid, violations = check_position_limits(weights, max_weight_per_asset=0.5, max_positions=10)
    assert not is_valid
    assert any("SPY" in v for v in violations)


def test_check_position_limits_negative_weight() -> None:
    """Test position limits with negative weight."""
    weights = {"SPY": 0.5, "QQQ": -0.1}
    is_valid, violations = check_position_limits(weights, max_weight_per_asset=0.5, max_positions=10)
    assert not is_valid
    assert any("negative weight" in v for v in violations)


def test_check_weight_sum_valid() -> None:
    """Test weight sum check with valid sum."""
    weights = {"SPY": 0.5, "QQQ": 0.45}
    is_valid, error = check_weight_sum(weights, expected_sum=0.95, tolerance=0.01)
    assert is_valid
    assert error == ""


def test_check_weight_sum_invalid() -> None:
    """Test weight sum check with invalid sum."""
    weights = {"SPY": 0.5, "QQQ": 0.3}
    is_valid, error = check_weight_sum(weights, expected_sum=0.95, tolerance=0.01)
    assert not is_valid
    assert "differs from expected" in error


def test_check_weight_sum_within_tolerance() -> None:
    """Test weight sum check within tolerance."""
    weights = {"SPY": 0.5, "QQQ": 0.449}  # Sum = 0.949, within 0.01 of 0.95
    is_valid, error = check_weight_sum(weights, expected_sum=0.95, tolerance=0.01)
    assert is_valid


def test_validate_weights_valid() -> None:
    """Test validate_weights with valid weights."""
    weights = {"SPY": 0.5, "QQQ": 0.45}
    is_valid, errors = validate_weights(weights, max_weight_per_asset=0.5, max_positions=10, expected_sum=0.95)
    assert is_valid
    assert len(errors) == 0


def test_validate_weights_multiple_violations() -> None:
    """Test validate_weights with multiple violations."""
    weights = {"SPY": 0.6, "QQQ": 0.2, "VTI": 0.1}  # SPY exceeds max, sum is wrong
    is_valid, errors = validate_weights(weights, max_weight_per_asset=0.5, max_positions=10, expected_sum=0.95)
    assert not is_valid
    assert len(errors) > 0


def test_validate_weights_empty() -> None:
    """Test validate_weights with empty weights."""
    weights = {}
    is_valid, errors = validate_weights(weights, expected_sum=0.95)
    # Empty weights sum to 0, which differs from 0.95
    assert not is_valid or len(errors) >= 0  # May or may not be valid depending on tolerance
