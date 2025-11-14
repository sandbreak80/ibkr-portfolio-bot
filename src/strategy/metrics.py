"""Backtest metrics calculation."""

import numpy as np
import pandas as pd

from src.core.logging import get_logger

logger = get_logger(__name__)


def calculate_cagr(equity: pd.Series, periods_per_year: float = 252.0) -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    Args:
        equity: Equity curve series
        periods_per_year: Trading periods per year (default: 252 for daily)

    Returns:
        CAGR as decimal (e.g., 0.15 for 15%)
    """
    if len(equity) < 2:
        return 0.0

    if equity.iloc[0] == 0:
        return 0.0

    total_return = equity.iloc[-1] / equity.iloc[0]
    num_periods = len(equity) - 1
    years = num_periods / periods_per_year

    if years <= 0:
        return 0.0

    cagr = (total_return ** (1.0 / years)) - 1.0
    return cagr


def calculate_sharpe(returns: pd.Series, rf_rate: float = 0.0, periods_per_year: float = 252.0) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        returns: Return series
        rf_rate: Risk-free rate (default: 0.0)
        periods_per_year: Trading periods per year

    Returns:
        Sharpe ratio
    """
    if len(returns) < 2:
        return 0.0

    excess_returns = returns - rf_rate / periods_per_year
    mean_excess = excess_returns.mean()
    std_excess = excess_returns.std()

    if std_excess == 0 or np.isnan(std_excess):
        return 0.0

    sharpe = mean_excess / std_excess * np.sqrt(periods_per_year)
    return sharpe


def calculate_max_drawdown(equity: pd.Series) -> float:
    """
    Calculate maximum drawdown.

    Args:
        equity: Equity curve series

    Returns:
        Maximum drawdown as decimal (e.g., -0.20 for -20%)
    """
    if len(equity) < 2:
        return 0.0

    # Calculate running maximum
    running_max = equity.expanding().max()

    # Calculate drawdown
    drawdown = (equity - running_max) / running_max

    max_dd = drawdown.min()
    return max_dd


def calculate_calmar(cagr: float, max_drawdown: float) -> float:
    """
    Calculate Calmar ratio (CAGR / |MaxDD|).

    Args:
        cagr: CAGR
        max_drawdown: Maximum drawdown (negative value)

    Returns:
        Calmar ratio
    """
    if max_drawdown == 0:
        return 0.0

    calmar = cagr / abs(max_drawdown)
    return calmar


def calculate_profit_factor(returns: pd.Series) -> float:
    """
    Calculate Profit Factor (gross gains / gross losses).

    Args:
        returns: Return series

    Returns:
        Profit factor
    """
    if len(returns) == 0:
        return 0.0

    gains = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())

    if losses == 0:
        return float("inf") if gains > 0 else 0.0

    pf = gains / losses
    return pf


def calculate_turnover_annualized(turnover: pd.Series, periods_per_year: float = 252.0) -> float:
    """
    Calculate annualized turnover.

    Args:
        turnover: Turnover series
        periods_per_year: Trading periods per year

    Returns:
        Annualized turnover
    """
    if len(turnover) == 0:
        return 0.0

    avg_daily_turnover = turnover.mean()
    annualized = avg_daily_turnover * periods_per_year
    return annualized


def calculate_all_metrics(
    returns: pd.Series,
    equity: pd.Series,
    turnover: pd.Series,
    periods_per_year: float = 252.0,
) -> dict[str, float]:
    """
    Calculate all backtest metrics.

    Args:
        returns: Return series
        equity: Equity curve series
        turnover: Turnover series
        periods_per_year: Trading periods per year

    Returns:
        Dictionary with all metrics
    """
    cagr_val = calculate_cagr(equity, periods_per_year)
    sharpe_val = calculate_sharpe(returns, periods_per_year=periods_per_year)
    max_dd = calculate_max_drawdown(equity)
    calmar_val = calculate_calmar(cagr_val, max_dd)
    pf = calculate_profit_factor(returns)
    turnover_ann = calculate_turnover_annualized(turnover, periods_per_year)

    metrics = {
        "CAGR": cagr_val,
        "Sharpe": sharpe_val,
        "Calmar": calmar_val,
        "MaxDD": max_dd,
        "PF": pf,
        "Turnover": turnover_ann,
    }

    return metrics
