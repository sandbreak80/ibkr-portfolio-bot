"""Tiingo adapter stub (disabled by default)."""
from src.core.logging import get_logger

logger = get_logger(__name__)


class TiingoClient:
    """Tiingo client stub (not implemented)."""

    def __init__(self, api_key: str = "") -> None:
        """Initialize Tiingo client stub."""
        logger.warning("Tiingo adapter is not implemented")


def fetch_historical_data_tiingo(symbol: str, start_date: str, end_date: str) -> None:
    """Stub function for Tiingo historical data fetch."""
    raise NotImplementedError("Tiingo adapter is not implemented")
