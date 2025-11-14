"""Rolling correlation matrix with greedy selection cap."""
from typing import Optional

import pandas as pd

from src.core.logging import get_logger

logger = get_logger(__name__)


def calculate_rolling_correlation_matrix(
    returns: pd.DataFrame,
    window: int = 90,
    min_periods: Optional[int] = None,
) -> pd.DataFrame:
    """
    Calculate rolling correlation matrix for returns.

    Args:
        returns: DataFrame with returns (columns = symbols, index = dates)
        window: Rolling window period (default: 90 days)
        min_periods: Minimum periods required (default: window)

    Returns:
        DataFrame with correlation matrix (last window)
    """
    if returns.empty:
        return pd.DataFrame()

    if min_periods is None:
        min_periods = window

    # Calculate rolling correlation
    corr_matrix = returns.rolling(window=window, min_periods=min_periods).corr()

    # Get the most recent correlation matrix
    if isinstance(corr_matrix.index, pd.MultiIndex):
        # MultiIndex case: get last date's correlations
        last_date = corr_matrix.index.get_level_values(0).max()
        last_corr = corr_matrix.loc[last_date]
    else:
        # Simple index case: use last row
        last_corr = corr_matrix.iloc[-1]

    return last_corr


def get_correlation_matrix(
    returns: pd.DataFrame,
    window: int = 90,
    date: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    Get correlation matrix for a specific date or most recent.

    Args:
        returns: DataFrame with returns (columns = symbols, index = dates)
        window: Rolling window period
        date: Specific date to use (default: most recent)

    Returns:
        Correlation matrix DataFrame
    """
    if returns.empty:
        return pd.DataFrame()

    if date is not None:
        # Filter returns up to and including date
        returns_subset = returns[returns.index <= date]
        if len(returns_subset) < window:
            logger.warning(f"Insufficient data for correlation at {date}")
            return pd.DataFrame()
        returns = returns_subset

    # Calculate correlation for the window ending at the specified date
    if date is not None:
        window_returns = returns[returns.index <= date].tail(window)
    else:
        window_returns = returns.tail(window)

    if len(window_returns) < window:
        logger.warning(f"Insufficient data for {window}-day correlation")
        return pd.DataFrame()

    corr_matrix = window_returns.corr()
    return corr_matrix


def apply_correlation_cap(
    symbols: list[str],
    scores: dict[str, float],
    corr_matrix: pd.DataFrame,
    corr_cap: float = 0.7,
) -> list[str]:
    """
    Select symbols with correlation cap using greedy algorithm.

    Args:
        symbols: List of symbols to consider (sorted by score desc)
        scores: Dictionary mapping symbols to scores
        corr_matrix: Correlation matrix DataFrame
        corr_cap: Maximum allowed correlation (default: 0.7)

    Returns:
        List of selected symbols
    """
    if not symbols:
        return []

    if corr_matrix.empty:
        logger.warning("Empty correlation matrix, returning top symbol")
        return [symbols[0]] if symbols else []

    selected = []

    for symbol in symbols:
        # Check correlation with already selected symbols
        can_add = True

        for selected_symbol in selected:
            # Get correlation (handle both directions)
            if symbol in corr_matrix.index and selected_symbol in corr_matrix.columns:
                corr = corr_matrix.loc[symbol, selected_symbol]
            elif symbol in corr_matrix.columns and selected_symbol in corr_matrix.index:
                corr = corr_matrix.loc[selected_symbol, symbol]
            else:
                # Symbol not in matrix, assume low correlation
                corr = 0.0

            # Check if correlation exceeds cap
            if abs(corr) > corr_cap:
                can_add = False
                logger.debug(
                    f"Rejecting {symbol} due to correlation {corr:.3f} "
                    f"with {selected_symbol} (cap: {corr_cap})"
                )
                break

        if can_add:
            selected.append(symbol)
            logger.debug(f"Selected {symbol} (score: {scores.get(symbol, 0):.3f})")

    return selected


def select_with_correlation_cap(
    scores: dict[str, float],
    returns: pd.DataFrame,
    top_n: int = 2,
    corr_window: int = 90,
    corr_cap: float = 0.7,
    date: Optional[pd.Timestamp] = None,
) -> list[str]:
    """
    Select top N symbols with correlation cap.

    Args:
        scores: Dictionary mapping symbols to scores
        returns: DataFrame with returns (columns = symbols, index = dates)
        top_n: Maximum number of symbols to select
        corr_window: Rolling window for correlation (default: 90)
        corr_cap: Maximum allowed correlation (default: 0.7)
        date: Date for correlation calculation (default: most recent)

    Returns:
        List of selected symbols
    """
    if not scores:
        return []

    # Sort symbols by score (descending)
    sorted_symbols = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    symbol_list = [s[0] for s in sorted_symbols]

    # Limit to top candidates (we'll filter by correlation)
    # Take more than top_n to have options after correlation filtering
    candidates = symbol_list[: min(len(symbol_list), top_n * 3)]

    # Get correlation matrix
    corr_matrix = get_correlation_matrix(returns, window=corr_window, date=date)

    if corr_matrix.empty:
        logger.warning("Empty correlation matrix, returning top symbols by score")
        return symbol_list[:top_n]

    # Apply correlation cap
    selected = apply_correlation_cap(candidates, scores, corr_matrix, corr_cap)

    # Limit to top_n
    return selected[:top_n]
