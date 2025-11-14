"""Test IBKR client with mocks."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brokers.ibkr_client import IBKRClient
from src.core.config import load_config


def test_ibkr_client_init() -> None:
    """Test IBKRClient initialization."""
    config = load_config()
    client = IBKRClient(config.ibkr)
    assert client.config is not None
    assert client.connected is False


@pytest.mark.asyncio
@patch("src.brokers.ibkr_client.IB")
async def test_ibkr_client_connect(mock_ib_class) -> None:
    """Test IBKR client connection."""
    # Setup mock
    mock_ib = MagicMock()
    mock_ib.connectAsync = AsyncMock()
    mock_ib.reqMarketDataType = MagicMock()
    mock_ib_class.return_value = mock_ib

    config = load_config()
    client = IBKRClient(config.ibkr)

    await client.connect()

    assert client.connected is True
    mock_ib.connectAsync.assert_called_once()


@pytest.mark.asyncio
@patch("src.brokers.ibkr_client.IB")
@patch("src.brokers.ibkr_client.util")
async def test_ibkr_client_fetch_historical_data(mock_util, mock_ib_class) -> None:
    """Test historical data fetching."""
    import pandas as pd

    # Setup mock DataFrame from util.df
    mock_df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-01")],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],
            "volume": [1000],
        }
    )
    mock_util.df = MagicMock(return_value=mock_df)

    # Setup mock Bar object
    mock_bar = MagicMock()
    mock_bar.time = datetime(2024, 1, 1)
    mock_bar.open = 100.0
    mock_bar.high = 101.0
    mock_bar.low = 99.0
    mock_bar.close = 100.0
    mock_bar.volume = 1000

    # Setup mock IB
    mock_ib = MagicMock()
    mock_ib.connectAsync = AsyncMock()
    mock_ib.reqMarketDataType = MagicMock()
    mock_ib.reqHistoricalDataAsync = AsyncMock(return_value=[mock_bar])
    mock_ib_class.return_value = mock_ib

    config = load_config()
    client = IBKRClient(config.ibkr)
    await client.connect()

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 2)

    df = await client.fetch_historical_data("SPY", start_date, end_date)

    assert not df.empty
    assert "close" in df.columns


@pytest.mark.asyncio
@patch("src.brokers.ibkr_client.IB")
async def test_ibkr_client_get_account_summary(mock_ib_class) -> None:
    """Test account summary retrieval."""
    # Setup mock AccountValue object
    mock_account_value = MagicMock()
    mock_account_value.tag = "NetLiquidation"
    mock_account_value.value = "25000"

    # Setup mock IB
    mock_ib = MagicMock()
    mock_ib.connectAsync = AsyncMock()
    mock_ib.reqMarketDataType = MagicMock()
    mock_ib.accountValues = MagicMock(return_value=[mock_account_value])
    mock_ib_class.return_value = mock_ib

    config = load_config()
    client = IBKRClient(config.ibkr)
    await client.connect()

    summary = client.get_account_summary()

    assert "NetLiquidation" in summary
    assert summary["NetLiquidation"] == "25000"
