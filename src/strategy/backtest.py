"""Backtesting engine with lagged positions and cost modeling."""
from datetime import datetime
from typing import Optional

import pandas as pd

from src.core.config import AppConfig
from src.core.logging import get_logger
from src.strategy.selector import select_assets
from src.strategy.weighting import calculate_weights

logger = get_logger(__name__)


def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate returns from OHLCV DataFrame.

    Args:
        df: DataFrame with OHLCV data (MultiIndex: symbol, date or single symbol)

    Returns:
        DataFrame with returns
    """
    if df.empty:
        return pd.DataFrame()

    if isinstance(df.index, pd.MultiIndex):
        # MultiIndex case: calculate returns per symbol
        returns_dict = {}
        for symbol in df.index.get_level_values(0).unique():
            symbol_df = df.loc[symbol]
            if "close" in symbol_df.columns:
                returns_dict[symbol] = symbol_df["close"].pct_change()
        if returns_dict:
            returns = pd.DataFrame(returns_dict)
            returns.index = df.index.get_level_values(1).unique()[: len(returns)]
        else:
            returns = pd.DataFrame()
    else:
        # Single symbol case
        if "close" in df.columns:
            returns = df["close"].pct_change().to_frame()
            returns.columns = [df.index.name if df.index.name else "returns"]
        else:
            returns = pd.DataFrame()

    return returns


def calculate_costs(
    turnover: pd.Series,
    commission_per_share: float = 0.0035,
    slippage_bps: float = 1.0,
    prices: Optional[pd.Series] = None,
) -> pd.Series:
    """
    Calculate trading costs (commission + slippage).

    Args:
        turnover: Turnover series (absolute change in weights)
        commission_per_share: Commission per share
        slippage_bps: Slippage in basis points
        prices: Price series for slippage calculation (optional)

    Returns:
        Series with costs
    """
    # Commission (simplified: assume average price for commission calculation)
    # In practice, commission is per share, but we approximate with turnover
    commission = turnover * commission_per_share

    # Slippage (basis points of notional)
    slippage = turnover * (slippage_bps / 10000.0)

    total_costs = commission + slippage
    return total_costs


def run_backtest(
    data: dict[str, pd.DataFrame],
    config: AppConfig,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """
    Run backtest with lagged positions.

    Args:
        data: Dictionary mapping symbols to OHLCV DataFrames
        config: Application configuration
        start_date: Start date for backtest
        end_date: End date for backtest

    Returns:
        Dictionary with backtest results
    """
    if not data:
        logger.warning("No data provided for backtest")
        return {}

    # Align all dataframes by date
    all_dates = set()
    for df in data.values():
        if not df.empty:
            all_dates.update(df.index)

    if not all_dates:
        logger.warning("No dates found in data")
        return {}

    all_dates = sorted(all_dates)

    # Filter by date range
    if start_date:
        all_dates = [d for d in all_dates if d >= start_date]
    if end_date:
        all_dates = [d for d in all_dates if d <= end_date]

    if not all_dates:
        logger.warning("No dates in specified range")
        return {}

    # Create aligned returns DataFrame
    returns_dict = {}
    for symbol, df in data.items():
        if df.empty:
            continue
        symbol_returns = df["close"].pct_change()
        returns_dict[symbol] = symbol_returns

    if not returns_dict:
        logger.warning("No returns calculated")
        return {}

    returns = pd.DataFrame(returns_dict)
    returns = returns.loc[all_dates]
    returns = returns.fillna(0.0)

    # Initialize positions (lagged by +1 bar)
    positions = pd.DataFrame(0.0, index=returns.index, columns=returns.columns)
    weights_history = []

    # Rebalance dates (daily for now)
    rebalance_dates = all_dates

    for i, date in enumerate(rebalance_dates):
        if i == 0:
            # First date: no positions yet (lagged)
            weights_history.append({date: {}})
            continue

        # Get data up to current date (for selection/weighting)
        date_data = {}
        for symbol, df in data.items():
            if not df.empty:
                date_df = df[df.index <= date]
                if not date_df.empty:
                    date_data[symbol] = date_df

        if not date_data:
            weights_history.append({date: {}})
            continue

        try:
            # Select assets
            selected = select_assets(date_data, returns, config, date=date)

            if not selected:
                weights_history.append({date: {}})
                # Positions remain 0 (from previous)
                continue

            # Calculate weights
            asset_weights = calculate_weights(selected, returns, config)

            if not asset_weights:
                weights_history.append({date: {}})
                continue

            # Store weights for this date
            weights_history.append({date: asset_weights})

            # Apply positions with +1 bar lag
            # Positions at date i are based on weights calculated at date i-1
            if i < len(returns.index):
                next_date_idx = returns.index.get_loc(date)
                if next_date_idx < len(returns.index) - 1:
                    # Set positions for NEXT bar (lagged)
                    next_date = returns.index[next_date_idx + 1]
                    for symbol, weight in asset_weights.items():
                        if symbol in positions.columns:
                            positions.loc[next_date, symbol] = weight

        except Exception as e:
            logger.error(f"Error in backtest at {date}: {e}")
            weights_history.append({date: {}})

    # Calculate portfolio returns (lagged positions)
    # Position at t-1 * return at t
    portfolio_returns = pd.Series(0.0, index=returns.index)

    for i in range(1, len(returns.index)):
        date = returns.index[i]
        prev_date = returns.index[i - 1]

        # Get positions from previous bar
        prev_positions = positions.loc[prev_date]

        # Calculate portfolio return
        date_returns = returns.loc[date]
        portfolio_return = (prev_positions * date_returns).sum()
        portfolio_returns.loc[date] = portfolio_return

    # Calculate turnover
    turnover = pd.Series(0.0, index=returns.index)
    for i in range(1, len(weights_history)):
        if i < len(returns.index):
            date = returns.index[i]
            prev_weights = weights_history[i - 1].get(list(weights_history[i - 1].keys())[0], {})
            curr_weights = weights_history[i].get(list(weights_history[i].keys())[0], {})

            # Calculate absolute change
            all_symbols = set(prev_weights.keys()) | set(curr_weights.keys())
            total_turnover = sum(abs(curr_weights.get(s, 0) - prev_weights.get(s, 0)) for s in all_symbols)
            turnover.loc[date] = total_turnover

    # Calculate costs
    costs = calculate_costs(
        turnover,
        commission_per_share=config.costs.commission_per_share,
        slippage_bps=config.costs.slippage_bps,
    )

    # Net returns (after costs)
    net_returns = portfolio_returns - costs

    # Calculate equity curve
    equity = (1 + net_returns).cumprod()

    results = {
        "returns": net_returns,
        "equity": equity,
        "positions": positions,
        "weights_history": weights_history,
        "turnover": turnover,
        "costs": costs,
        "dates": all_dates,
    }

    return results
