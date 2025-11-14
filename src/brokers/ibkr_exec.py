"""IBKR execution: weights to fractional orders."""
from datetime import datetime
from typing import Optional

from ib_insync import LimitOrder, MarketOrder, Stock

from src.core.config import AppConfig
from src.core.logging import get_logger
from src.core.types import OrderDict
from src.strategy.compliance import ComplianceChecker

logger = get_logger(__name__)


class IBKRExecutor:
    """IBKR order execution with fractional shares support."""

    def __init__(self, ibkr_client, config: AppConfig) -> None:
        """
        Initialize IBKR executor.

        Args:
            ibkr_client: IBKRClient instance (must be connected)
            config: Application configuration
        """
        self.client = ibkr_client
        self.config = config
        self.compliance = ComplianceChecker(config)

    def calculate_target_notional(
        self,
        weights: dict[str, float],
        equity: float,
    ) -> float:
        """
        Calculate target notional value from weights.

        Args:
            weights: Dictionary mapping symbols to weights
            equity: Account equity

        Returns:
            Target notional value
        """
        total_weight = sum(weights.values())
        target_notional = equity * total_weight
        return target_notional

    def weights_to_orders(
        self,
        weights: dict[str, float],
        current_positions: Optional[dict[str, float]] = None,
        equity: float = 25000.0,
        account: str = "DUK200445",
        dry_run: bool = False,
    ) -> list[OrderDict]:
        """
        Convert weights to fractional orders.

        Args:
            weights: Dictionary mapping symbols to target weights
            current_positions: Dictionary mapping symbols to current positions (qty)
            equity: Account equity
            account: Account ID
            dry_run: If True, don't place orders

        Returns:
            List of order dictionaries
        """
        if current_positions is None:
            current_positions = {}

        orders = []

        for symbol, target_weight in weights.items():
            try:
                # Calculate target notional
                target_notional = equity * target_weight

                # Get current position quantity
                current_qty = current_positions.get(symbol, 0.0)

                # Calculate target quantity (fractional)
                # In real implementation, would fetch current price from IBKR
                # For now, use placeholder price
                current_price = 100.0  # Placeholder
                target_qty = target_notional / current_price

                # Calculate order quantity (difference)
                order_qty = target_qty - current_qty

                if abs(order_qty) < 0.01:  # Minimum order size
                    continue

                # Determine action
                action = "BUY" if order_qty > 0 else "SELL"
                order_qty_abs = abs(order_qty)

                # Create order dict
                order_dict: OrderDict = {
                    "symbol": symbol,
                    "action": action,
                    "quantity": order_qty_abs,
                    "order_type": self.config.execution.order_type,
                    "limit_price": None,
                    "account": account,
                }

                # Calculate limit price if LMT order
                if self.config.execution.order_type == "LMT":
                    # Limit price = mid ± offset_bps
                    offset_pct = self.config.execution.limit_offset_bps / 10000.0
                    if action == "BUY":
                        limit_price = current_price * (1 - offset_pct)
                    else:
                        limit_price = current_price * (1 + offset_pct)
                    order_dict["limit_price"] = limit_price

                orders.append(order_dict)

            except Exception as e:
                logger.error(f"Error creating order for {symbol}: {e}")
                continue

        return orders

    async def place_orders(
        self,
        orders: list[OrderDict],
        dry_run: bool = False,
    ) -> list[dict]:
        """
        Place orders with IBKR.

        Args:
            orders: List of order dictionaries
            dry_run: If True, print orders but don't place

        Returns:
            List of order results
        """
        if not self.client.connected:
            raise ConnectionError("IBKR client not connected")

        if not orders:
            logger.info("No orders to place")
            return []

        results = []

        for order_dict in orders:
            try:
                # Check compliance
                if not dry_run:
                    # In real implementation, would check settlement, PDT, etc.
                    pass

                if dry_run:
                    logger.info(
                        f"DRY-RUN: {order_dict['action']} {order_dict['quantity']:.4f} "
                        f"{order_dict['symbol']} @ {order_dict.get('limit_price', 'MKT')}"
                    )
                    results.append({"order": order_dict, "status": "dry_run", "order_id": None})
                    continue

                # Create contract
                contract = Stock(order_dict["symbol"], "SMART", "USD")

                # Create order
                if order_dict["order_type"] == "MKT":
                    order = MarketOrder(order_dict["action"], order_dict["quantity"])
                else:  # LMT
                    if order_dict.get("limit_price") is None:
                        logger.warning(f"No limit price for LMT order {order_dict['symbol']}")
                        continue
                    order = LimitOrder(
                        order_dict["action"],
                        order_dict["quantity"],
                        order_dict["limit_price"],
                    )

                # Set order properties
                order.totalQuantity = order_dict["quantity"]
                order.account = order_dict["account"]
                order.outsideRth = False  # Regular hours only

                # Place order
                trade = self.client.ib.placeOrder(contract, order)
                logger.info(f"Placed order {trade.order.orderId} for {order_dict['symbol']}")

                results.append(
                    {
                        "order": order_dict,
                        "status": "placed",
                        "order_id": trade.order.orderId,
                        "trade": trade,
                    }
                )

                # Record order for compliance
                self.compliance.record_order()

            except Exception as e:
                logger.error(f"Error placing order for {order_dict['symbol']}: {e}")
                results.append({"order": order_dict, "status": "error", "error": str(e)})

        return results

    async def execute_rebalance(
        self,
        weights: dict[str, float],
        current_positions: Optional[dict[str, float]] = None,
        equity: Optional[float] = None,
        dry_run: bool = False,
        paper: bool = False,
        live: bool = False,
    ) -> list[dict]:
        """
        Execute rebalance: convert weights to orders and place them.

        Args:
            weights: Dictionary mapping symbols to target weights
            current_positions: Current positions (symbol -> qty)
            equity: Account equity (fetches from IBKR if not provided)
            dry_run: If True, don't place orders
            paper: If True, use paper account
            live: If True, use live account

        Returns:
            List of order results
        """
        # Determine account
        if live:
            account = self.config.ibkr.account_live
            if not account:
                raise ValueError("Live account not configured")
        elif paper:
            account = self.config.ibkr.account_paper
        else:
            account = self.config.ibkr.account_paper  # Default to paper

        # Get equity if not provided
        if equity is None:
            if not dry_run:
                account_summary = self.client.get_account_summary()
                equity = float(account_summary.get("NetLiquidation", 25000.0))
            else:
                equity = 25000.0  # Default for dry-run

        # Check compliance
        target_notional = self.calculate_target_notional(weights, equity)
        if not dry_run:
            account_summary = self.client.get_account_summary()
            settled_cash = float(account_summary.get("AvailableFunds", equity))

            is_valid, errors = self.compliance.validate_trade(
                target_notional,
                settled_cash,
                datetime.now(),
            )

            if not is_valid:
                logger.error(f"Compliance check failed: {errors}")
                raise ValueError(f"Compliance violation: {errors}")

        # Convert weights to orders
        orders = self.weights_to_orders(weights, current_positions, equity, account, dry_run)

        # Limit orders per day
        if len(orders) > self.config.execution.max_orders_per_day:
            logger.warning(
                f"Too many orders ({len(orders)}), limiting to {self.config.execution.max_orders_per_day}"
            )
            orders = orders[: self.config.execution.max_orders_per_day]

        # Place orders
        results = await self.place_orders(orders, dry_run=dry_run)

        if not dry_run:
            # Record rebalance
            self.compliance.record_rebalance(datetime.now())

        return results
