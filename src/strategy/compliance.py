"""Compliance checks: settlement guard, PDT counter, rebalance limits."""
from datetime import datetime
from typing import Optional

from src.core.config import AppConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


class ComplianceChecker:
    """Compliance checker for trading rules."""

    def __init__(self, config: AppConfig) -> None:
        """
        Initialize compliance checker.

        Args:
            config: Application configuration
        """
        self.config = config
        self.last_rebalance_date: Optional[datetime] = None
        self.pdt_counter = 0
        self.orders_today = 0

    def check_settlement_guard(
        self,
        target_notional: float,
        settled_cash: float,
    ) -> tuple[bool, str]:
        """
        Check settlement guard: target_notional <= settled_cash.

        Args:
            target_notional: Target notional value for orders
            settled_cash: Available settled cash

        Returns:
            Tuple of (is_valid, error_message)
        """
        if target_notional > settled_cash:
            return (
                False,
                f"Target notional {target_notional:.2f} exceeds settled cash {settled_cash:.2f}",
            )

        return (True, "")

    def check_one_rebalance_per_day(self, current_date: datetime) -> tuple[bool, str]:
        """
        Check that only one rebalance occurs per day.

        Args:
            current_date: Current date

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.last_rebalance_date is not None:
            if self.last_rebalance_date.date() == current_date.date():
                return (
                    False,
                    f"Rebalance already occurred today ({current_date.date()})",
                )

        return (True, "")

    def check_max_orders_per_day(self) -> tuple[bool, str]:
        """
        Check maximum orders per day limit.

        Returns:
            Tuple of (is_valid, error_message)
        """
        max_orders = self.config.execution.max_orders_per_day
        if self.orders_today >= max_orders:
            return (
                False,
                f"Maximum orders per day ({max_orders}) reached",
            )

        return (True, "")

    def record_rebalance(self, date: datetime) -> None:
        """
        Record a rebalance event.

        Args:
            date: Rebalance date
        """
        self.last_rebalance_date = date
        logger.info(f"Recorded rebalance at {date}")

    def record_order(self) -> None:
        """Record an order placement."""
        self.orders_today += 1
        logger.debug(f"Recorded order ({self.orders_today} today)")

    def reset_daily_counters(self, date: datetime) -> None:
        """
        Reset daily counters (call at start of each day).

        Args:
            date: Current date
        """
        if self.last_rebalance_date is None:
            self.orders_today = 0
            return

        # Reset if new day
        if date.date() > self.last_rebalance_date.date():
            self.orders_today = 0
            logger.debug(f"Reset daily counters for {date.date()}")

    def validate_trade(
        self,
        target_notional: float,
        settled_cash: float,
        current_date: datetime,
    ) -> tuple[bool, list[str]]:
        """
        Validate trade compliance.

        Args:
            target_notional: Target notional value
            settled_cash: Available settled cash
            current_date: Current date

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        # Check settlement guard
        settlement_ok, settlement_error = self.check_settlement_guard(target_notional, settled_cash)
        if not settlement_ok:
            errors.append(settlement_error)

        # Check one rebalance per day
        rebalance_ok, rebalance_error = self.check_one_rebalance_per_day(current_date)
        if not rebalance_ok:
            errors.append(rebalance_error)

        # Check max orders per day
        orders_ok, orders_error = self.check_max_orders_per_day()
        if not orders_ok:
            errors.append(orders_error)

        return (len(errors) == 0, errors)
