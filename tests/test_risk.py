"""Test risk management."""
from src.strategy.risk import check_position_limits, check_weight_sum, validate_weights


def test_check_position_limits() -> None:
    """Test position limit checks."""
    weights = {"A": 0.3, "B": 0.3, "C": 0.3, "D": 0.1}

    # Should pass with max_positions=10
    is_valid, violations = check_position_limits(weights, max_weight_per_asset=0.5, max_positions=10)
    assert is_valid is True
    assert len(violations) == 0

    # Should fail with max_positions=3
    is_valid, violations = check_position_limits(weights, max_weight_per_asset=0.5, max_positions=3)
    assert is_valid is False
    assert len(violations) > 0


def test_check_weight_sum() -> None:
    """Test weight sum check."""
    weights = {"A": 0.5, "B": 0.45}
    is_valid, error = check_weight_sum(weights, expected_sum=0.95, tolerance=0.01)
    assert is_valid is True

    weights_bad = {"A": 0.5, "B": 0.3}
    is_valid, error = check_weight_sum(weights_bad, expected_sum=0.95, tolerance=0.01)
    assert is_valid is False
    assert len(error) > 0


def test_validate_weights() -> None:
    """Test full weight validation."""
    weights = {"A": 0.4, "B": 0.55}  # B exceeds 0.5 cap
    is_valid, errors = validate_weights(weights, max_weight_per_asset=0.5, expected_sum=0.95)
    assert is_valid is False
    assert len(errors) > 0

    weights_good = {"A": 0.45, "B": 0.5}
    is_valid, errors = validate_weights(weights_good, max_weight_per_asset=0.5, expected_sum=0.95)
    assert is_valid is True
