"""Test compliance checks."""
from datetime import datetime

from src.core.config import load_config
from src.strategy.compliance import ComplianceChecker


def test_settlement_guard() -> None:
    """Test settlement guard check."""
    config = load_config()
    checker = ComplianceChecker(config)

    # Should pass: target < settled
    is_valid, error = checker.check_settlement_guard(target_notional=1000.0, settled_cash=2000.0)
    assert is_valid is True

    # Should fail: target > settled
    is_valid, error = checker.check_settlement_guard(target_notional=2000.0, settled_cash=1000.0)
    assert is_valid is False
    assert len(error) > 0


def test_one_rebalance_per_day() -> None:
    """Test one rebalance per day check."""
    config = load_config()
    checker = ComplianceChecker(config)

    date1 = datetime(2024, 1, 1, 15, 55)
    date2 = datetime(2024, 1, 1, 16, 0)  # Same day
    date3 = datetime(2024, 1, 2, 15, 55)  # Next day

    # First rebalance should pass
    is_valid, error = checker.check_one_rebalance_per_day(date1)
    assert is_valid is True
    checker.record_rebalance(date1)

    # Second rebalance same day should fail
    is_valid, error = checker.check_one_rebalance_per_day(date2)
    assert is_valid is False

    # Rebalance next day should pass
    is_valid, error = checker.check_one_rebalance_per_day(date3)
    assert is_valid is True


def test_max_orders_per_day() -> None:
    """Test max orders per day check."""
    config = load_config()
    checker = ComplianceChecker(config)

    # Should pass initially
    is_valid, error = checker.check_max_orders_per_day()
    assert is_valid is True

    # Record orders up to limit
    for _ in range(config.execution.max_orders_per_day):
        checker.record_order()

    # Should fail after limit
    is_valid, error = checker.check_max_orders_per_day()
    assert is_valid is False


def test_validate_trade() -> None:
    """Test full trade validation."""
    config = load_config()
    checker = ComplianceChecker(config)

    date = datetime(2024, 1, 1, 15, 55)

    # Valid trade
    is_valid, errors = checker.validate_trade(
        target_notional=1000.0,
        settled_cash=2000.0,
        current_date=date,
    )
    assert is_valid is True

    # Invalid: exceeds settled cash
    is_valid, errors = checker.validate_trade(
        target_notional=3000.0,
        settled_cash=2000.0,
        current_date=date,
    )
    assert is_valid is False
    assert len(errors) > 0
