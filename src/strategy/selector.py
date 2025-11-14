"""Asset selection with ranking and correlation cap."""
from typing import Optional

import pandas as pd

from src.core.config import AppConfig
from src.core.logging import get_logger
from src.features.correlation import select_with_correlation_cap
from src.features.scoring import calculate_scores_for_dataframe
from src.strategy.signals import calculate_signals

logger = get_logger(__name__)


def select_assets(
    data: dict[str, pd.DataFrame],
    returns: pd.DataFrame,
    config: AppConfig,
    date: Optional[pd.Timestamp] = None,
) -> list[str]:
    """
    Select top N assets with correlation cap.

    Args:
        data: Dictionary mapping symbols to OHLCV DataFrames
        returns: DataFrame with returns (columns = symbols, index = dates)
        config: Application configuration
        date: Date for selection (default: most recent)

    Returns:
        List of selected symbols
    """
    if not data:
        return []

    # Calculate scores for all symbols
    scores = {}
    long_ok_signals = {}

    for symbol, df in data.items():
        if df.empty:
            continue

        # Filter to date if specified
        if date is not None:
            df_filtered = df[df.index <= date]
            if df_filtered.empty:
                continue
            df = df_filtered

        try:
            # Calculate score
            symbol_scores = calculate_scores_for_dataframe(
                df,
                ema_fast_window=config.features.ema_fast,
                atr_window=config.features.atr_window,
            )

            if symbol_scores.empty:
                continue

            # Get latest score
            latest_score = symbol_scores.iloc[-1]

            # Check if score meets minimum
            if latest_score < config.selection.min_score:
                continue

            scores[symbol] = latest_score

            # Calculate signals to check long_ok
            signals = calculate_signals(df, config)
            long_ok_signals[symbol] = signals.get(symbol, False)

        except Exception as e:
            logger.error(f"Error calculating score for {symbol}: {e}")
            continue

    # Filter to only long_ok symbols
    long_ok_scores = {s: score for s, score in scores.items() if long_ok_signals.get(s, False)}

    if not long_ok_scores:
        logger.info("No assets pass long_ok gates")
        return []

    # Select with correlation cap
    selected = select_with_correlation_cap(
        long_ok_scores,
        returns,
        top_n=config.selection.top_n,
        corr_window=config.selection.corr_window,
        corr_cap=config.selection.corr_cap,
        date=date,
    )

    logger.info(f"Selected {len(selected)} assets: {selected}")
    return selected
