"""Tests for Discord alerting system."""
import os
from unittest.mock import Mock, patch

import pytest
import requests

from src.core.alerting import (
    DiscordAlerter,
    send_data_quality_warning,
    send_rebalance_error_alert,
    send_rebalance_success_alert,
    send_startup_notification,
    send_test_alert,
)


def test_discord_alerter_init_with_webhook() -> None:
    """Test DiscordAlerter initialization with webhook."""
    alerter = DiscordAlerter(webhook_url="https://discord.com/api/webhooks/test")
    assert alerter.enabled is True
    assert alerter.webhook_url == "https://discord.com/api/webhooks/test"


def test_discord_alerter_init_without_webhook() -> None:
    """Test DiscordAlerter initialization without webhook."""
    with patch.dict(os.environ, {}, clear=True):
        alerter = DiscordAlerter()
        assert alerter.enabled is False
        assert alerter.webhook_url == ""


def test_discord_alerter_init_from_env() -> None:
    """Test DiscordAlerter initialization from environment."""
    with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://test.com"}):
        alerter = DiscordAlerter()
        assert alerter.enabled is True
        assert alerter.webhook_url == "https://test.com"


def test_send_message_not_enabled() -> None:
    """Test send_message when webhook not enabled."""
    alerter = DiscordAlerter(webhook_url="")
    result = alerter.send_message("Test", "Body")
    assert result is False


@patch("requests.post")
def test_send_message_success(mock_post: Mock) -> None:
    """Test successful message send."""
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    alerter = DiscordAlerter(webhook_url="https://discord.com/api/webhooks/test")
    result = alerter.send_message("Test", "Body", color=0x123456)
    
    assert result is True
    mock_post.assert_called_once()
    
    # Verify payload structure
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert "embeds" in payload
    assert payload["embeds"][0]["title"] == "Test"
    assert payload["embeds"][0]["description"] == "Body"
    assert payload["embeds"][0]["color"] == 0x123456


@patch("requests.post")
def test_send_message_with_fields(mock_post: Mock) -> None:
    """Test message send with fields."""
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    alerter = DiscordAlerter(webhook_url="https://test.com")
    fields = [
        {"name": "Field1", "value": "Value1", "inline": True},
        {"name": "Field2", "value": "Value2", "inline": False},
    ]
    
    result = alerter.send_message("Test", "Body", fields=fields)
    
    assert result is True
    payload = mock_post.call_args[1]["json"]
    assert payload["embeds"][0]["fields"] == fields


@patch("requests.post")
def test_send_message_http_error(mock_post: Mock) -> None:
    """Test message send with HTTP error."""
    mock_post.side_effect = requests.exceptions.HTTPError("Server error")
    
    alerter = DiscordAlerter(webhook_url="https://test.com")
    result = alerter.send_message("Test", "Body")
    
    assert result is False


@patch("src.core.alerting.DiscordAlerter.send_message")
def test_send_rebalance_success_alert(mock_send: Mock) -> None:
    """Test rebalance success alert."""
    mock_send.return_value = True
    
    send_rebalance_success_alert(
        orders_placed=2,
        portfolio_value=10000.0,
        positions={"SPY": 0.5, "QQQ": 0.45},
        execution_time_seconds=5.3
    )
    
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert "✅" in call_args[1]["title"]
    assert call_args[1]["color"] == 0x2ECC71  # Green


@patch("src.core.alerting.DiscordAlerter.send_message")
def test_send_rebalance_error_alert(mock_send: Mock) -> None:
    """Test rebalance error alert."""
    mock_send.return_value = True
    
    error = ConnectionError("Test error")
    send_rebalance_error_alert(error, context={"account": "DUK200445"})
    
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert "🚨" in call_args[1]["title"]
    assert call_args[1]["color"] == 0xE74C3C  # Red


@patch("src.core.alerting.DiscordAlerter.send_message")
def test_send_data_quality_warning(mock_send: Mock) -> None:
    """Test data quality warning alert."""
    mock_send.return_value = True
    
    send_data_quality_warning("SPY", "Price jump detected")
    
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert "⚠️" in call_args[1]["title"]
    assert call_args[1]["color"] == 0xF39C12  # Orange


@patch("src.core.alerting.DiscordAlerter.send_message")
def test_send_startup_notification(mock_send: Mock) -> None:
    """Test startup notification."""
    mock_send.return_value = True
    
    send_startup_notification()
    
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert "🚀" in call_args[1]["title"]
    assert call_args[1]["color"] == 0x3498DB  # Blue


@patch("src.core.alerting.DiscordAlerter.send_message")
def test_send_test_alert(mock_send: Mock) -> None:
    """Test test alert."""
    mock_send.return_value = True
    
    result = send_test_alert()
    
    assert result is True
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert "🧪" in call_args[1]["title"]

