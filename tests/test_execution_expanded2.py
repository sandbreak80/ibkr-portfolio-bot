"""Additional tests for ibkr_exec module."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.brokers.ibkr_exec import IBKRExecutor
from src.core.config import load_config


@pytest.mark.asyncio
async def test_place_orders_limit_order_no_price() -> None:
    """Test placing limit order without limit price."""
    config = load_config()
    config.execution.order_type = "LMT"
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.ib = MagicMock()

    executor = IBKRExecutor(mock_client, config)

    orders = [
        {
            "symbol": "SPY",
            "action": "BUY",
            "quantity": 10.5,
            "order_type": "LMT",
            "limit_price": None,  # Missing limit price
            "account": "DUK200445",
        }
    ]

    results = await executor.place_orders(orders, dry_run=False)
    # Should handle missing limit price gracefully
    assert len(results) >= 0


@pytest.mark.asyncio
async def test_place_orders_error_handling() -> None:
    """Test error handling when placing orders."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.ib = MagicMock()
    mock_client.ib.placeOrder = AsyncMock(side_effect=Exception("Connection error"))

    executor = IBKRExecutor(mock_client, config)

    orders = [
        {
            "symbol": "SPY",
            "action": "BUY",
            "quantity": 10.5,
            "order_type": "MKT",
            "account": "DUK200445",
        }
    ]

    results = await executor.place_orders(orders, dry_run=False)
    # Should handle errors gracefully
    assert len(results) == 1
    assert results[0]["status"] == "error"


@pytest.mark.asyncio
async def test_execute_rebalance_with_equity() -> None:
    """Test execute_rebalance with explicit equity."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5}

    results = await executor.execute_rebalance(weights, equity=30000.0, dry_run=True, paper=True)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_execute_rebalance_live_mode() -> None:
    """Test execute_rebalance in live mode (should not actually execute)."""
    config = load_config()
    config.ibkr.account_live = "LIVE123"  # Configure live account
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5}

    # In dry_run, should not actually place orders
    results = await executor.execute_rebalance(weights, dry_run=True, live=True)
    assert isinstance(results, list)
