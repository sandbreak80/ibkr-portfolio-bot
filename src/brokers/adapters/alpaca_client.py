"""Alpaca adapter stub (disabled by default)."""
from src.core.logging import get_logger

logger = get_logger(__name__)


class AlpacaClient:
    """Alpaca client stub (not implemented)."""

    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        """Initialize Alpaca client stub."""
        logger.warning("Alpaca adapter is not implemented")


def fetch_historical_data_alpaca(symbol: str, start_date: str, end_date: str) -> None:
    """Stub function for Alpaca historical data fetch."""
    raise NotImplementedError("Alpaca adapter is not implemented")
