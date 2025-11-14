"""Risk management: position limits and sanity checks."""

from src.core.logging import get_logger

logger = get_logger(__name__)


def check_position_limits(
    weights: dict[str, float],
    max_weight_per_asset: float = 0.5,
    max_positions: int = 10,
) -> tuple[bool, list[str]]:
    """
    Check position limits.

    Args:
        weights: Dictionary mapping symbols to weights
        max_weight_per_asset: Maximum weight per asset
        max_positions: Maximum number of positions

    Returns:
        Tuple of (is_valid, list of violations)
    """
    violations = []

    if len(weights) > max_positions:
        violations.append(f"Too many positions: {len(weights)} > {max_positions}")

    for symbol, weight in weights.items():
        if weight > max_weight_per_asset:
            violations.append(f"{symbol}: weight {weight:.4f} > {max_weight_per_asset}")

        if weight < 0:
            violations.append(f"{symbol}: negative weight {weight:.4f}")

    return (len(violations) == 0, violations)


def check_weight_sum(
    weights: dict[str, float],
    expected_sum: float = 1.0,
    tolerance: float = 0.01,
) -> tuple[bool, str]:
    """
    Check that weights sum to expected value.

    Args:
        weights: Dictionary mapping symbols to weights
        expected_sum: Expected sum of weights
        tolerance: Tolerance for comparison

    Returns:
        Tuple of (is_valid, error_message)
    """
    actual_sum = sum(weights.values())
    diff = abs(actual_sum - expected_sum)

    if diff > tolerance:
        return (
            False,
            f"Weight sum {actual_sum:.4f} differs from expected {expected_sum:.4f} by {diff:.4f}",
        )

    return (True, "")


def validate_weights(
    weights: dict[str, float],
    max_weight_per_asset: float = 0.5,
    max_positions: int = 10,
    expected_sum: float = 0.95,  # With 5% cash buffer
    tolerance: float = 0.01,
) -> tuple[bool, list[str]]:
    """
    Validate portfolio weights.

    Args:
        weights: Dictionary mapping symbols to weights
        max_weight_per_asset: Maximum weight per asset
        max_positions: Maximum number of positions
        expected_sum: Expected sum of weights
        tolerance: Tolerance for sum comparison

    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []

    # Check position limits
    limits_ok, limit_violations = check_position_limits(weights, max_weight_per_asset, max_positions)
    errors.extend(limit_violations)

    # Check weight sum
    sum_ok, sum_error = check_weight_sum(weights, expected_sum, tolerance)
    if not sum_ok:
        errors.append(sum_error)

    return (len(errors) == 0, errors)
