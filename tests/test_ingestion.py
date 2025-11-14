"""Test data ingestion module."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.core.config import load_config
from src.data.ingestion import DataIngestion


def test_data_ingestion_init() -> None:
    """Test DataIngestion initialization."""
    config = load_config()
    ingestion = DataIngestion(config)
    assert ingestion.config is not None
    assert ingestion.cache is not None
    assert ingestion.universe_manager is not None


@pytest.mark.asyncio
@patch("src.data.ingestion.IBKRClient")
async def test_fetch_and_cache_symbol(mock_client_class) -> None:
    """Test fetching and caching a single symbol."""
    # Setup mocks
    mock_client = MagicMock()
    mock_client.connected = False
    mock_client.fetch_historical_data = AsyncMock(
        return_value=pd.DataFrame(
            {
                "open": [100, 101],
                "high": [101, 102],
                "low": [99, 100],
                "close": [100, 101],
                "volume": [1000, 1100],
            },
            index=pd.date_range("2024-01-01", periods=2, freq="D"),
        )
    )
    mock_client_class.return_value = mock_client

    config = load_config()
    cache_dir = Path("/tmp/test_cache")
    ingestion = DataIngestion(config, cache_dir=cache_dir)

    # Test fetch
    df = await ingestion.fetch_and_cache_symbol("SPY", force_refresh=True)

    assert not df.empty
    assert len(df) == 2


@pytest.mark.asyncio
@patch("src.data.ingestion.IBKRClient")
async def test_fetch_all(mock_client_class) -> None:
    """Test fetching all symbols."""
    # Setup mocks
    mock_client = MagicMock()
    mock_client.connected = False
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.fetch_historical_data = AsyncMock(
        return_value=pd.DataFrame(
            {
                "open": [100],
                "high": [101],
                "low": [99],
                "close": [100],
                "volume": [1000],
            },
            index=pd.date_range("2024-01-01", periods=1, freq="D"),
        )
    )
    mock_client_class.return_value = mock_client

    config = load_config()
    config.universe = ["SPY", "QQQ"]  # Limit for test
    cache_dir = Path("/tmp/test_cache")
    ingestion = DataIngestion(config, cache_dir=cache_dir)

    # Test fetch all
    results = await ingestion.fetch_all(force_refresh=True)

    assert len(results) == 2
    assert "SPY" in results
    assert "QQQ" in results
