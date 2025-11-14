"""Test universe management."""
from src.core.config import load_config
from src.data.universe import UniverseManager


def test_universe_manager_default() -> None:
    """Test universe manager with default config."""
    config = load_config()
    manager = UniverseManager(config)
    universe = manager.get_universe()
    assert len(universe) > 0
    assert "SPY" in universe


def test_universe_validation() -> None:
    """Test symbol validation."""
    config = load_config()
    manager = UniverseManager(config)

    # Valid symbols
    assert manager.validate_symbol("SPY") is True
    assert manager.validate_symbol("QQQ") is True

    # Invalid symbols
    assert manager.validate_symbol("") is False
    assert manager.validate_symbol("INVALID-SYMBOL") is False
    assert manager.validate_symbol("A" * 20) is False  # Too long


def test_universe_add_remove() -> None:
    """Test adding and removing symbols."""
    config = load_config()
    manager = UniverseManager(config)

    initial_count = len(manager.get_universe())

    # Add valid symbol
    assert manager.add_symbol("TEST") is True
    assert len(manager.get_universe()) == initial_count + 1
    assert "TEST" in manager.get_universe()

    # Add duplicate (should fail)
    assert manager.add_symbol("TEST") is False

    # Remove symbol
    assert manager.remove_symbol("TEST") is True
    assert len(manager.get_universe()) == initial_count
    assert "TEST" not in manager.get_universe()


def test_universe_validate_all() -> None:
    """Test validating entire universe."""
    config = load_config()
    manager = UniverseManager(config)

    is_valid, invalid = manager.validate_universe()
    assert is_valid is True
    assert len(invalid) == 0
