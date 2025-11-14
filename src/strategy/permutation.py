"""Permutation testing (IMCPT-lite) with joint permutations."""
import random
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.core.config import AppConfig
from src.core.logging import get_logger
from src.strategy.walkforward import generate_walkforward_windows, grid_search

logger = get_logger(__name__)


def permute_returns_joint(returns: pd.DataFrame, seed: Optional[int] = None) -> pd.DataFrame:
    """
    Permute returns with joint permutation (preserves cross-asset structure).

    Args:
        returns: DataFrame with returns (columns = symbols, index = dates)
        seed: Random seed for reproducibility

    Returns:
        Permuted returns DataFrame
    """
    if returns.empty:
        return returns

    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    # Create copy
    permuted = returns.copy()

    # Permute the index (dates) while keeping columns together
    # This preserves cross-asset correlations within each time period
    permuted_index = returns.index.copy()
    indices = np.arange(len(permuted_index))
    np.random.shuffle(indices)
    permuted = permuted.iloc[indices].copy()
    permuted.index = returns.index  # Restore original index order

    return permuted


def run_permutation_test(
    data: dict[str, pd.DataFrame],
    returns: pd.DataFrame,
    config: AppConfig,
    train_start: datetime,
    train_end: datetime,
    runs: int = 200,
    seed: int = 42,
) -> dict:
    """
    Run permutation test (IMCPT-lite) on training window.

    Args:
        data: Dictionary mapping symbols to OHLCV DataFrames
        returns: DataFrame with returns
        config: Application configuration
        train_start: Training start date
        train_end: Training end date
        runs: Number of permutation runs
        seed: Random seed

    Returns:
        Dictionary with permutation test results
    """
    # Filter data to training period
    train_data = {}
    for symbol, df in data.items():
        train_df = df[(df.index >= train_start) & (df.index < train_end)]
        if not train_df.empty:
            train_data[symbol] = train_df

    train_returns = returns[(returns.index >= train_start) & (returns.index < train_end)]

    if not train_data or train_returns.empty:
        logger.warning(f"Insufficient data for permutation test {train_start} to {train_end}")
        return {"p_value": None, "real_score": None, "permuted_scores": []}

    # Run grid search on real data
    logger.info("Running grid search on real data...")
    real_grid_result = grid_search(train_data, train_returns, config, train_start, train_end)

    if real_grid_result["params"] is None:
        logger.warning("No valid parameters found for real data")
        return {"p_value": None, "real_score": None, "permuted_scores": []}

    real_score = real_grid_result["score"]
    logger.info(f"Real best score: {real_score:.4f}")

    # Run permutations
    permuted_scores = []
    np.random.seed(seed)
    random.seed(seed)

    for run in range(runs):
        if (run + 1) % 50 == 0:
            logger.info(f"Permutation run {run+1}/{runs}")

        # Permute returns
        permuted_returns = permute_returns_joint(train_returns, seed=seed + run)

        # Run grid search on permuted data
        permuted_grid_result = grid_search(train_data, permuted_returns, config, train_start, train_end)

        if permuted_grid_result["params"] is not None:
            permuted_score = permuted_grid_result["score"]
            permuted_scores.append(permuted_score)

    if not permuted_scores:
        logger.warning("No valid permuted scores generated")
        return {"p_value": None, "real_score": real_score, "permuted_scores": []}

    # Calculate p-value: fraction of permuted scores >= real score
    p_value = sum(1 for score in permuted_scores if score >= real_score) / len(permuted_scores)

    logger.info(f"Permutation test complete: p-value = {p_value:.4f} (real score: {real_score:.4f})")

    return {
        "p_value": p_value,
        "real_score": real_score,
        "permuted_scores": permuted_scores,
        "runs": runs,
        "valid_runs": len(permuted_scores),
    }


def run_permutation_tests_on_windows(
    data: dict[str, pd.DataFrame],
    returns: pd.DataFrame,
    config: AppConfig,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[dict]:
    """
    Run permutation tests on walk-forward windows.

    Args:
        data: Dictionary mapping symbols to OHLCV DataFrames
        returns: DataFrame with returns
        config: Application configuration
        start_date: Start date
        end_date: End date

    Returns:
        List of permutation test results per window
    """
    # Determine date range
    if start_date is None or end_date is None:
        all_dates = set()
        for df in data.values():
            if not df.empty:
                all_dates.update(df.index)
        if not all_dates:
            return []
        all_dates = sorted(all_dates)
        if start_date is None:
            start_date = all_dates[0]
        if end_date is None:
            end_date = all_dates[-1]

    # Generate windows
    windows = generate_walkforward_windows(
        start_date,
        end_date,
        train_years=config.walkforward.train_years,
        oos_months=config.walkforward.oos_months,
    )

    results = []
    for i, (train_start, train_end, oos_start, oos_end) in enumerate(windows):
        logger.info(f"Permutation test window {i+1}/{len(windows)}: {train_start.date()} to {train_end.date()}")

        window_result = run_permutation_test(
            data,
            returns,
            config,
            train_start,
            train_end,
            runs=config.permutation.runs,
            seed=config.backtest.seed + i,
        )

        window_result["window"] = i + 1
        window_result["train_start"] = train_start
        window_result["train_end"] = train_end
        results.append(window_result)

    return results
