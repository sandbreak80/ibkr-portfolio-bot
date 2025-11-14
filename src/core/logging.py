"""Structured logging and audit trail."""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class JSONLFormatter(logging.Formatter):
    """Formatter that outputs JSONL for audit logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """
    Set up structured logging with console and JSONL file outputs.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: artifacts/logs)
        enable_console: Enable console output
        enable_file: Enable JSONL file output
    """
    if log_dir is None:
        log_dir = Path("artifacts/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (human-readable)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler (JSONL for audit)
    if enable_file:
        log_file = log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # File gets all levels
        file_handler.setFormatter(JSONLFormatter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_rebalance_event(
    logger: logging.Logger,
    date: str,
    inputs: dict[str, Any],
    selected: list[str],
    corr_summary: Optional[dict[str, Any]] = None,
    weights: Optional[dict[str, float]] = None,
    orders: Optional[list[dict[str, Any]]] = None,
) -> None:
    """
    Log a rebalance event with structured data.

    Args:
        logger: Logger instance
        date: Rebalance date
        inputs: Input data snapshot
        selected: Selected assets
        corr_summary: Correlation summary
        weights: Target weights
        orders: Generated orders (if any)
    """
    event_data: dict[str, Any] = {
        "event_type": "rebalance",
        "date": date,
        "inputs": inputs,
        "selected": selected,
    }

    if corr_summary:
        event_data["corr_summary"] = corr_summary
    if weights:
        event_data["weights"] = weights
    if orders:
        event_data["orders"] = orders

    logger.info("Rebalance event", extra={"extra_fields": event_data})
