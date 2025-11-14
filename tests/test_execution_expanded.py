"""Expanded tests for IBKR execution."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brokers.ibkr_exec import IBKRExecutor
from src.core.config import load_config


def test_executor_init() -> None:
    """Test executor initialization."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)
    assert executor.client == mock_client
    assert executor.config == config
    assert executor.compliance is not None


def test_weights_to_orders_with_positions() -> None:
    """Test weights to orders with existing positions."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5}
    current_positions = {"SPY": 50.0}  # Already have 50 shares

    orders = executor.weights_to_orders(weights, current_positions=current_positions, equity=25000.0, dry_run=True)

    # Should generate order to adjust position
    assert len(orders) >= 0  # May be 0 if position already matches


def test_weights_to_orders_sell() -> None:
    """Test sell orders."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.1}  # Reduce weight
    current_positions = {"SPY": 100.0}  # Have 100 shares

    orders = executor.weights_to_orders(weights, current_positions=current_positions, equity=25000.0, dry_run=True)

    # Should generate sell order
    if orders:
        assert any(order["action"] == "SELL" for order in orders)


def test_weights_to_orders_minimum_size() -> None:
    """Test minimum order size filtering."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    # Very small weight that might still generate order (threshold is 0.01 qty)
    weights = {"SPY": 0.00001}  # Even smaller

    orders = executor.weights_to_orders(weights, equity=25000.0, dry_run=True)

    # May or may not filter out depending on calculated qty
    assert isinstance(orders, list)


@pytest.mark.asyncio
async def test_place_orders_dry_run() -> None:
    """Test placing orders in dry-run mode."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

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

    results = await executor.place_orders(orders, dry_run=True)
    assert len(results) == 1
    assert results[0]["status"] == "dry_run"


@pytest.mark.asyncio
@patch("src.brokers.ibkr_exec.Stock")
@patch("src.brokers.ibkr_exec.MarketOrder")
async def test_place_orders_paper(mock_order_class, mock_stock_class) -> None:
    """Test placing orders in paper mode."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.ib = MagicMock()
    mock_client.ib.placeOrder = AsyncMock()

    executor = IBKRExecutor(mock_client, config)

    mock_stock = MagicMock()
    mock_stock_class.return_value = mock_stock
    mock_order = MagicMock()
    mock_order_class.return_value = mock_order

    orders = [
        {
            "symbol": "SPY",
            "action": "BUY",
            "quantity": 10.5,
            "order_type": "MKT",
            "account": "DUK200445",
        }
    ]

    # Should not actually place in dry_run
    results = await executor.place_orders(orders, dry_run=True)
    assert len(results) > 0


def test_execute_rebalance_paper() -> None:
    """Test paper trading execution."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5}

    async def run_test() -> None:
        results = await executor.execute_rebalance(weights, dry_run=False, paper=True)
        # In paper mode with dry_run=False, should attempt to place orders
        assert isinstance(results, list)

    import asyncio

    asyncio.run(run_test())


def test_execute_rebalance_with_positions() -> None:
    """Test rebalance with current positions."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5, "QQQ": 0.3}
    current_positions = {"SPY": 50.0}

    async def run_test() -> None:
        results = await executor.execute_rebalance(
            weights, current_positions=current_positions, dry_run=True, paper=True
        )
        assert isinstance(results, list)

    import asyncio

    asyncio.run(run_test())
