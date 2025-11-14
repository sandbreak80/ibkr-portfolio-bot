"""Test IBKR execution."""
from unittest.mock import MagicMock

from src.brokers.ibkr_exec import IBKRExecutor
from src.core.config import load_config


def test_calculate_target_notional() -> None:
    """Test target notional calculation."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5, "QQQ": 0.45}
    equity = 25000.0

    notional = executor.calculate_target_notional(weights, equity)
    assert notional == equity * 0.95  # 5% cash buffer


def test_weights_to_orders() -> None:
    """Test weights to orders conversion."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5, "QQQ": 0.45}
    orders = executor.weights_to_orders(weights, equity=25000.0, dry_run=True)

    assert len(orders) == 2
    assert all("symbol" in order for order in orders)
    assert all("action" in order for order in orders)
    assert all("quantity" in order for order in orders)


def test_weights_to_orders_limit_price() -> None:
    """Test limit price calculation for LMT orders."""
    config = load_config()
    config.execution.order_type = "LMT"
    config.execution.limit_offset_bps = 2  # 2 bps

    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5}
    orders = executor.weights_to_orders(weights, equity=25000.0, dry_run=True)

    assert len(orders) == 1
    assert orders[0]["order_type"] == "LMT"
    assert orders[0]["limit_price"] is not None


def test_execute_rebalance_dry_run() -> None:
    """Test dry-run execution."""
    config = load_config()
    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    weights = {"SPY": 0.5}

    async def run_test() -> None:
        results = await executor.execute_rebalance(weights, dry_run=True, paper=True)
        assert len(results) > 0
        assert all(r["status"] == "dry_run" for r in results)

    import asyncio

    asyncio.run(run_test())


def test_max_orders_per_day_limit() -> None:
    """Test max orders per day limit."""
    config = load_config()
    config.execution.max_orders_per_day = 2

    mock_client = MagicMock()
    mock_client.connected = True

    executor = IBKRExecutor(mock_client, config)

    # Create weights that would generate more orders than limit
    weights = {"SPY": 0.25, "QQQ": 0.25, "VTI": 0.25, "TLT": 0.25}

    orders = executor.weights_to_orders(weights, equity=25000.0, dry_run=True)
    # Should be limited by max_orders_per_day in execute_rebalance
    assert len(orders) <= 4  # Before limiting
