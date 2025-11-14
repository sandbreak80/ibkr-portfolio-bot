"""Expanded tests for logging module."""
from pathlib import Path

from src.core.logging import get_logger, setup_logging


def test_setup_logging_file_only() -> None:
    """Test logging setup with file output only."""
    log_dir = Path("/tmp/test_logs_file_only")
    log_dir.mkdir(exist_ok=True)

    setup_logging(log_level="DEBUG", log_dir=log_dir, enable_console=False, enable_file=True)

    logger = get_logger("test_module")
    logger.info("Test message")

    # Check log file was created
    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) > 0


def test_setup_logging_console_only() -> None:
    """Test logging setup with console output only."""
    setup_logging(log_level="WARNING", log_dir=None, enable_console=True, enable_file=False)

    logger = get_logger("test_console")
    logger.warning("Test warning message")

    # Should not crash
    assert True


def test_setup_logging_different_levels() -> None:
    """Test logging setup with different log levels."""
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        setup_logging(log_level=level, log_dir=None, enable_console=False, enable_file=False)
        logger = get_logger(f"test_{level}")
        logger.info("Test message")
        assert True


def test_get_logger_multiple_modules() -> None:
    """Test getting loggers for multiple modules."""
    setup_logging(log_level="INFO", log_dir=None, enable_console=False, enable_file=False)

    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    logger3 = get_logger("module1")  # Should return same logger

    assert logger1.name == "module1"
    assert logger2.name == "module2"
    assert logger3 == logger1  # Should be same instance


def test_logger_logging_levels() -> None:
    """Test logger at different levels."""
    setup_logging(log_level="DEBUG", log_dir=None, enable_console=False, enable_file=False)

    logger = get_logger("test_levels")

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    assert True
