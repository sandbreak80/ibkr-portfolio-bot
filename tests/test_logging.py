"""Test core logging setup."""

from src.core.logging import get_logger, setup_logging


def test_logging_setup() -> None:
    """Test that logging can be set up."""
    setup_logging(log_level="INFO", enable_file=False)
    logger = get_logger(__name__)
    logger.info("Test log message")
    assert logger is not None


def test_logger_creation() -> None:
    """Test that logger can be created."""
    logger = get_logger("test_module")
    assert logger is not None
    assert logger.name == "test_module"
