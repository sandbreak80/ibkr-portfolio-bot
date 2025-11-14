"""Discord alerting system for portfolio events."""
import os
from datetime import datetime
from typing import Optional

import requests

from src.core.logging import get_logger

logger = get_logger(__name__)


class DiscordAlerter:
    """Send alerts to Discord via webhook."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        """
        Initialize Discord alerter.

        Args:
            webhook_url: Discord webhook URL (or use DISCORD_WEBHOOK_URL env var)
        """
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
        self.enabled = bool(self.webhook_url)

        if not self.enabled:
            logger.warning("Discord webhook not configured, alerts disabled")

    def send_message(
        self,
        title: str,
        description: str,
        color: int = 0x3498DB,  # Blue
        fields: Optional[list[dict]] = None
    ) -> bool:
        """
        Send rich embed message to Discord.

        Args:
            title: Embed title
            description: Embed description
            color: Embed color (hex)
            fields: List of {"name": "Field", "value": "Value", "inline": False}

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.warning("Discord webhook not enabled, skipping alert")
            return False

        try:
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "IBKR Portfolio Bot"}
            }

            if fields:
                embed["fields"] = fields

            payload = {
                "embeds": [embed],
                "username": "Portfolio Bot"
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )
            response.raise_for_status()

            logger.info(f"Discord alert sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False


def send_rebalance_success_alert(
    orders_placed: int,
    portfolio_value: float,
    positions: dict,
    execution_time_seconds: float = 0.0
) -> None:
    """Send alert for successful rebalance."""
    alerter = DiscordAlerter()

    fields = [
        {"name": "📈 Portfolio Value", "value": f"${portfolio_value:,.2f}", "inline": True},
        {"name": "📋 Orders Placed", "value": str(orders_placed), "inline": True},
        {"name": "⏱️ Execution Time", "value": f"{execution_time_seconds:.1f}s", "inline": True},
    ]

    # Add positions
    if positions:
        positions_text = "\n".join([
            f"**{symbol}**: {weight:.1%}"
            for symbol, weight in sorted(positions.items(), key=lambda x: -x[1])
        ])
        fields.append({"name": "💼 Current Positions", "value": positions_text, "inline": False})

    alerter.send_message(
        title="✅ Portfolio Rebalanced Successfully",
        description=f"Daily rebalance completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}",
        color=0x2ECC71,  # Green
        fields=fields
    )


def send_rebalance_error_alert(
    error: Exception,
    context: Optional[dict] = None
) -> None:
    """Send alert for rebalance failure."""
    alerter = DiscordAlerter()

    fields = [
        {"name": "❌ Error Type", "value": f"`{type(error).__name__}`", "inline": False},
        {"name": "📄 Error Message", "value": f"```{str(error)[:500]}```", "inline": False},
    ]

    if context:
        context_text = "\n".join([f"**{k}**: {v}" for k, v in list(context.items())[:5]])
        fields.append({"name": "🔍 Context", "value": context_text, "inline": False})

    alerter.send_message(
        title="🚨 Portfolio Rebalance FAILED",
        description=f"**ACTION REQUIRED**: Rebalance failed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}",
        color=0xE74C3C,  # Red
        fields=fields
    )


def send_data_quality_warning(symbol: str, issue: str) -> None:
    """Send alert for data quality issues."""
    alerter = DiscordAlerter()

    alerter.send_message(
        title="⚠️ Data Quality Warning",
        description=f"Data issue detected for **{symbol}**",
        color=0xF39C12,  # Orange
        fields=[
            {"name": "Symbol", "value": symbol, "inline": True},
            {"name": "Issue", "value": issue, "inline": False},
        ]
    )


def send_startup_notification() -> None:
    """Send notification that bot is starting."""
    alerter = DiscordAlerter()

    alerter.send_message(
        title="🚀 Portfolio Bot Starting",
        description="Automated rebalance system is initializing",
        color=0x3498DB,  # Blue
        fields=[
            {"name": "Status", "value": "✅ All systems operational", "inline": False},
            {"name": "Next Action", "value": "Waiting for 15:55 ET rebalance time", "inline": False},
        ]
    )


def send_test_alert() -> bool:
    """
    Send a test alert to verify Discord webhook is working.

    Returns:
        True if alert sent successfully
    """
    alerter = DiscordAlerter()

    return alerter.send_message(
        title="🧪 Test Alert",
        description="This is a test message from your IBKR Portfolio Bot!",
        color=0x9B59B6,  # Purple
        fields=[
            {"name": "Status", "value": "✅ Discord webhook is working!", "inline": False},
            {"name": "Next Step", "value": "Configure scheduler for automated trading", "inline": False},
        ]
    )

