"""Walk-forward analysis with rolling train/OOS re-optimization."""
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from src.core.config import AppConfig
from src.core.logging import get_logger
from src.strategy.backtest import run_backtest
from src.strategy.metrics import calculate_all_metrics

logger = get_logger(__name__)


def generate_walkforward_windows(
    start_date: datetime,
    end_date: datetime,
    train_years: int = 3,
    oos_months: int = 3,
) -> list[tuple[datetime, datetime, datetime, datetime]]:
    """
    Generate walk-forward windows.

    Args:
        start_date: Start date
        end_date: End date
        train_years: Training period in years
        oos_months: Out-of-sample period in months

    Returns:
        List of (train_start, train_end, oos_start, oos_end) tuples
    """
    windows = []
    current_date = start_date

    while current_date < end_date:
        train_start = current_date
        train_end = train_start + timedelta(days=365 * train_years)

        if train_end > end_date:
            break

        oos_start = train_end
        oos_end = oos_start + timedelta(days=30 * oos_months)

        if oos_end > end_date:
            oos_end = end_date

        if oos_start >= oos_end:
            break

        windows.append((train_start, train_end, oos_start, oos_end))
        current_date = oos_start

    return windows


def grid_search(
    data: dict[str, pd.DataFrame],
    returns: pd.DataFrame,
    config: AppConfig,
    train_start: datetime,
    train_end: datetime,
    param_grid: Optional[dict] = None,
) -> dict:
    """
    Perform grid search over parameter space.

    Args:
        data: Dictionary mapping symbols to OHLCV DataFrames
        returns: DataFrame with returns
        config: Application configuration
        train_start: Training start date
        train_end: Training end date
        param_grid: Parameter grid (uses config defaults if not provided)

    Returns:
        Dictionary with best parameters and score
    """
    if param_grid is None:
        param_grid = {
            "ema_fast": config.walkforward.reoptimize.ema_fast,
            "ema_slow": config.walkforward.reoptimize.ema_slow,
            "top_n": config.walkforward.reoptimize.top_n,
            "corr_cap": config.walkforward.reoptimize.corr_cap,
        }

    best_score = float("-inf")
    best_params = None

    # Filter data to training period
    train_data = {}
    for symbol, df in data.items():
        train_df = df[(df.index >= train_start) & (df.index < train_end)]
        if not train_df.empty:
            train_data[symbol] = train_df

    train_returns = returns[(returns.index >= train_start) & (returns.index < train_end)]

    if not train_data or train_returns.empty:
        logger.warning(f"Insufficient data for grid search {train_start} to {train_end}")
        return {"params": None, "score": float("-inf")}

    # Grid search
    for ema_fast in param_grid["ema_fast"]:
        for ema_slow in param_grid["ema_slow"]:
            if ema_fast >= ema_slow:
                continue

            for top_n in param_grid["top_n"]:
                for corr_cap in param_grid["corr_cap"]:
                    # Create modified config
                    test_config = AppConfig(**config.model_dump())
                    test_config.features.ema_fast = ema_fast
                    test_config.features.ema_slow = ema_slow
                    test_config.selection.top_n = top_n
                    test_config.selection.corr_cap = corr_cap

                    try:
                        # Run backtest on training period
                        results = run_backtest(train_data, test_config, train_start, train_end)

                        if not results:
                            continue

                        equity = results.get("equity", pd.Series())
                        returns_series = results.get("returns", pd.Series())
                        turnover = results.get("turnover", pd.Series())

                        if equity.empty or returns_series.empty:
                            continue

                        # Calculate metrics
                        metrics = calculate_all_metrics(returns_series, equity, turnover)

                        # Use Calmar as objective (or config objective)
                        objective = metrics.get(config.permutation.objective, metrics.get("Calmar", 0.0))

                        if objective > best_score:
                            best_score = objective
                            best_params = {
                                "ema_fast": ema_fast,
                                "ema_slow": ema_slow,
                                "top_n": top_n,
                                "corr_cap": corr_cap,
                            }

                    except Exception as e:
                        logger.warning(f"Error in grid search for params {ema_fast}/{ema_slow}/{top_n}/{corr_cap}: {e}")
                        continue

    return {"params": best_params, "score": best_score}


def run_walkforward(
    data: dict[str, pd.DataFrame],
    returns: pd.DataFrame,
    config: AppConfig,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """
    Run walk-forward analysis.

    Args:
        data: Dictionary mapping symbols to OHLCV DataFrames
        returns: DataFrame with returns
        config: Application configuration
        start_date: Start date (uses data range if not provided)
        end_date: End date (uses data range if not provided)

    Returns:
        Dictionary with walk-forward results
    """
    # Determine date range
    if start_date is None or end_date is None:
        all_dates = set()
        for df in data.values():
            if not df.empty:
                all_dates.update(df.index)
        if not all_dates:
            logger.warning("No dates found in data")
            return {}
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

    if not windows:
        logger.warning("No walk-forward windows generated")
        return {}

    logger.info(f"Generated {len(windows)} walk-forward windows")

    oos_results = []
    oos_equity_segments = []
    chosen_params_history = []

    for i, (train_start, train_end, oos_start, oos_end) in enumerate(windows):
        logger.info(f"Window {i+1}/{len(windows)}: Train {train_start.date()} to {train_end.date()}, OOS {oos_start.date()} to {oos_end.date()}")

        # Grid search on training period
        grid_result = grid_search(data, returns, config, train_start, train_end)

        if grid_result["params"] is None:
            logger.warning(f"No valid parameters found for window {i+1}")
            continue

        best_params = grid_result["params"]
        chosen_params_history.append({oos_start: best_params})

        # Apply best params to OOS period
        test_config = AppConfig(**config.model_dump())
        test_config.features.ema_fast = best_params["ema_fast"]
        test_config.features.ema_slow = best_params["ema_slow"]
        test_config.selection.top_n = best_params["top_n"]
        test_config.selection.corr_cap = best_params["corr_cap"]

        # Run backtest on OOS period
        oos_data = {}
        for symbol, df in data.items():
            oos_df = df[(df.index >= oos_start) & (df.index <= oos_end)]
            if not oos_df.empty:
                oos_data[symbol] = oos_df

        if not oos_data:
            continue

        oos_results_window = run_backtest(oos_data, test_config, oos_start, oos_end)

        if oos_results_window:
            oos_equity = oos_results_window.get("equity", pd.Series())
            oos_returns = oos_results_window.get("returns", pd.Series())
            oos_turnover = oos_results_window.get("turnover", pd.Series())

            if not oos_equity.empty:
                # Normalize equity to start at 1.0 for concatenation
                oos_equity_normalized = oos_equity / oos_equity.iloc[0]
                oos_equity_segments.append(oos_equity_normalized)

                # Calculate OOS metrics
                oos_metrics = calculate_all_metrics(oos_returns, oos_equity, oos_turnover)
                oos_results.append(
                    {
                        "window": i + 1,
                        "oos_start": oos_start,
                        "oos_end": oos_end,
                        "params": best_params,
                        "metrics": oos_metrics,
                    }
                )

    # Concatenate OOS equity segments
    if oos_equity_segments:
        oos_equity_combined = pd.concat(oos_equity_segments)
        # Remove duplicates (overlapping dates)
        oos_equity_combined = oos_equity_combined[~oos_equity_combined.index.duplicated(keep="first")]
        oos_equity_combined = oos_equity_combined.sort_index()
    else:
        oos_equity_combined = pd.Series()

    return {
        "windows": windows,
        "oos_results": oos_results,
        "oos_equity": oos_equity_combined,
        "chosen_params": chosen_params_history,
    }
