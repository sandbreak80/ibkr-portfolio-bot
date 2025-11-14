"""Retry logic with exponential backoff for transient failures."""
import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (ConnectionError, TimeoutError),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator with exponential backoff for sync functions.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        def fetch_data():
            # ... code that may fail transiently
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    func_name = getattr(func, "__name__", "function")
                    if attempt == max_attempts:
                        logger.error(
                            f"{func_name} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func_name} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    func_name = getattr(func, "__name__", "function")
                    logger.error(f"{func_name} failed with unexpected error: {e}")
                    raise

            # Should never reach here, but mypy needs it
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic error")

        return wrapper
    return decorator


def async_retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (ConnectionError, TimeoutError),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Retry decorator with exponential backoff for async functions.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated async function

    Example:
        @async_retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        async def fetch_data():
            # ... async code that may fail transiently
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    func_name = getattr(func, "__name__", "function")
                    if attempt == max_attempts:
                        logger.error(
                            f"{func_name} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func_name} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    func_name = getattr(func, "__name__", "function")
                    logger.error(f"{func_name} failed with unexpected error: {e}")
                    raise

            # Should never reach here, but mypy needs it
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic error")

        return wrapper
    return decorator

