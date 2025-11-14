"""Tests for retry logic."""
from typing import Any
from unittest.mock import Mock

import pytest

from src.core.retry import async_retry_with_backoff, retry_with_backoff


def test_retry_success_first_attempt() -> None:
    """Test successful execution on first attempt."""
    mock_func = Mock(return_value="success")
    decorated = retry_with_backoff()(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 1


def test_retry_success_after_failures() -> None:
    """Test successful execution after transient failures."""
    mock_func = Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])
    decorated = retry_with_backoff(max_attempts=3, initial_delay=0.01)(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 3


def test_retry_exhausted() -> None:
    """Test failure after all retries exhausted."""
    mock_func = Mock(side_effect=ConnectionError("Connection failed"))
    decorated = retry_with_backoff(max_attempts=3, initial_delay=0.01)(mock_func)

    with pytest.raises(ConnectionError, match="Connection failed"):
        decorated()

    assert mock_func.call_count == 3


def test_retry_unexpected_exception() -> None:
    """Test that unexpected exceptions are not retried."""
    mock_func = Mock(side_effect=ValueError("Unexpected error"))
    decorated = retry_with_backoff(
        max_attempts=3,
        initial_delay=0.01,
        exceptions=(ConnectionError,)
    )(mock_func)

    with pytest.raises(ValueError, match="Unexpected error"):
        decorated()

    # Should fail immediately, no retries
    assert mock_func.call_count == 1


def test_retry_with_custom_exceptions() -> None:
    """Test retry with custom exception types."""
    mock_func = Mock(side_effect=[TimeoutError(), ValueError("success")])
    decorated = retry_with_backoff(
        max_attempts=2,
        initial_delay=0.01,
        exceptions=(TimeoutError,)
    )(mock_func)

    # Should retry on TimeoutError, then raise ValueError
    with pytest.raises(ValueError, match="success"):
        decorated()

    assert mock_func.call_count == 2


def test_retry_exponential_backoff() -> None:
    """Test that backoff increases exponentially."""
    import time

    call_times = []

    def slow_func() -> str:
        call_times.append(time.time())
        if len(call_times) < 3:
            raise ConnectionError()
        return "success"

    decorated = retry_with_backoff(
        max_attempts=3,
        initial_delay=0.1,
        exponential_base=2.0
    )(slow_func)

    result = decorated()

    assert result == "success"
    assert len(call_times) == 3

    # Check delays are increasing (with some tolerance)
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]

    assert delay1 >= 0.08  # ~0.1s (initial_delay)
    assert delay2 >= 0.18  # ~0.2s (initial_delay * exponential_base)
    assert delay2 > delay1  # Should be increasing


@pytest.mark.asyncio
async def test_async_retry_success_first_attempt() -> None:
    """Test async successful execution on first attempt."""
    async def async_func() -> str:
        return "success"

    decorated = async_retry_with_backoff()(async_func)
    result = await decorated()

    assert result == "success"


@pytest.mark.asyncio
async def test_async_retry_success_after_failures() -> None:
    """Test async successful execution after transient failures."""
    counter = {"calls": 0}

    async def async_func() -> str:
        counter["calls"] += 1
        if counter["calls"] < 3:
            raise ConnectionError()
        return "success"

    decorated = async_retry_with_backoff(max_attempts=3, initial_delay=0.01)(async_func)
    result = await decorated()

    assert result == "success"
    assert counter["calls"] == 3


@pytest.mark.asyncio
async def test_async_retry_exhausted() -> None:
    """Test async failure after all retries exhausted."""
    async def async_func() -> str:
        raise ConnectionError("Connection failed")

    decorated = async_retry_with_backoff(max_attempts=3, initial_delay=0.01)(async_func)

    with pytest.raises(ConnectionError, match="Connection failed"):
        await decorated()


@pytest.mark.asyncio
async def test_async_retry_unexpected_exception() -> None:
    """Test async that unexpected exceptions are not retried."""
    counter = {"calls": 0}

    async def async_func() -> str:
        counter["calls"] += 1
        raise ValueError("Unexpected error")

    decorated = async_retry_with_backoff(
        max_attempts=3,
        initial_delay=0.01,
        exceptions=(ConnectionError,)
    )(async_func)

    with pytest.raises(ValueError, match="Unexpected error"):
        await decorated()

    # Should fail immediately, no retries
    assert counter["calls"] == 1


def test_retry_with_args_and_kwargs() -> None:
    """Test retry decorator preserves function arguments."""
    mock_func = Mock(return_value="result")
    decorated = retry_with_backoff()(mock_func)

    result = decorated("arg1", "arg2", kwarg1="val1", kwarg2="val2")

    assert result == "result"
    mock_func.assert_called_once_with("arg1", "arg2", kwarg1="val1", kwarg2="val2")


@pytest.mark.asyncio
async def test_async_retry_with_args_and_kwargs() -> None:
    """Test async retry decorator preserves function arguments."""
    async def async_func(*args: Any, **kwargs: Any) -> tuple:
        return (args, kwargs)

    decorated = async_retry_with_backoff()(async_func)
    result = await decorated("arg1", "arg2", kwarg1="val1", kwarg2="val2")

    assert result == (("arg1", "arg2"), {"kwarg1": "val1", "kwarg2": "val2"})


def test_retry_max_delay_cap() -> None:
    """Test that delay is capped at max_delay."""
    import time

    call_times = []

    def slow_func() -> str:
        call_times.append(time.time())
        if len(call_times) < 4:
            raise ConnectionError()
        return "success"

    decorated = retry_with_backoff(
        max_attempts=4,
        initial_delay=0.1,
        max_delay=0.2,  # Cap at 0.2s
        exponential_base=2.0
    )(slow_func)

    result = decorated()

    assert result == "success"
    assert len(call_times) == 4

    # Last delay should be capped at max_delay (0.2s)
    delay3 = call_times[3] - call_times[2]
    assert delay3 < 0.25  # Should be ~0.2s, not 0.4s

