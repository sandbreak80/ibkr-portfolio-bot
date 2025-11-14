"""Test core configuration loading."""

from src.core.config import load_config


def test_config_loads() -> None:
    """Test that configuration loads successfully."""
    config = load_config()
    assert config is not None
    assert config.ibkr.host == "127.0.0.1"
    assert config.ibkr.port == 7497
    assert len(config.universe) > 0


def test_config_universe_default() -> None:
    """Test that default universe is set."""
    config = load_config()
    assert "SPY" in config.universe
    assert "QQQ" in config.universe
