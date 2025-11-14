"""Portfolio weighting: inverse-volatility with caps and cash buffer."""

import numpy as np
import pandas as pd

from src.core.config import AppConfig
from src.core.logging import get_logger
from src.features.indicators import stdev

logger = get_logger(__name__)


def calculate_inverse_vol_weights(
    selected_symbols: list[str],
    returns: pd.DataFrame,
    vol_window: int = 20,
) -> dict[str, float]:
    """
    Calculate inverse-volatility weights.

    Args:
        selected_symbols: List of selected symbols
        returns: DataFrame with returns (columns = symbols, index = dates)
        vol_window: Window for volatility calculation

    Returns:
        Dictionary mapping symbols to raw weights
    """
    if not selected_symbols:
        return {}

    weights = {}
    inv_vols = {}

    for symbol in selected_symbols:
        if symbol not in returns.columns:
            logger.warning(f"Symbol {symbol} not in returns DataFrame")
            continue

        symbol_returns = returns[symbol].dropna()
        if len(symbol_returns) < vol_window:
            logger.warning(f"Insufficient data for {symbol} volatility calculation")
            continue

        # Calculate volatility (standard deviation of returns)
        vol = stdev(symbol_returns, window=vol_window).iloc[-1]

        if vol <= 0 or np.isnan(vol):
            logger.warning(f"Invalid volatility for {symbol}: {vol}")
            continue

        # Inverse volatility
        inv_vol = 1.0 / vol
        inv_vols[symbol] = inv_vol

    if not inv_vols:
        return {}

    # Normalize weights
    total_inv_vol = sum(inv_vols.values())
    if total_inv_vol == 0:
        return {}

    for symbol, inv_vol in inv_vols.items():
        weights[symbol] = inv_vol / total_inv_vol

    return weights


def apply_weight_caps(
    weights: dict[str, float],
    max_weight_per_asset: float = 0.5,
) -> dict[str, float]:
    """
    Apply maximum weight cap per asset.

    Args:
        weights: Dictionary mapping symbols to weights
        max_weight_per_asset: Maximum weight per asset (default: 0.5)

    Returns:
        Dictionary with capped weights (renormalized)
    """
    if not weights:
        return {}

    capped_weights = {}
    excess = 0.0

    for symbol, weight in weights.items():
        if weight > max_weight_per_asset:
            excess += weight - max_weight_per_asset
            capped_weights[symbol] = max_weight_per_asset
        else:
            capped_weights[symbol] = weight

    # Redistribute excess proportionally to uncapped assets
    if excess > 0:
        uncapped_symbols = [s for s, w in capped_weights.items() if w < max_weight_per_asset]
        if uncapped_symbols:
            total_uncapped = sum(capped_weights[s] for s in uncapped_symbols)
            if total_uncapped > 0:
                for symbol in uncapped_symbols:
                    capped_weights[symbol] += excess * (capped_weights[symbol] / total_uncapped)

    # Renormalize to ensure sum = 1.0
    total = sum(capped_weights.values())
    if total > 0:
        capped_weights = {s: w / total for s, w in capped_weights.items()}

    return capped_weights


def apply_cash_buffer(
    weights: dict[str, float],
    cash_buffer: float = 0.05,
) -> dict[str, float]:
    """
    Apply cash buffer by scaling down weights.

    Args:
        weights: Dictionary mapping symbols to weights
        cash_buffer: Cash buffer percentage (default: 0.05 = 5%)

    Returns:
        Dictionary with scaled weights (sum = 1 - cash_buffer)
    """
    if not weights:
        return {}

    scale_factor = 1.0 - cash_buffer
    scaled_weights = {s: w * scale_factor for s, w in weights.items()}

    return scaled_weights


def calculate_weights(
    selected_symbols: list[str],
    returns: pd.DataFrame,
    config: AppConfig,
) -> dict[str, float]:
    """
    Calculate portfolio weights with inverse-volatility, caps, and cash buffer.

    Args:
        selected_symbols: List of selected symbols
        returns: DataFrame with returns (columns = symbols, index = dates)
        config: Application configuration

    Returns:
        Dictionary mapping symbols to final weights
    """
    if not selected_symbols:
        return {}

    # Calculate inverse-volatility weights
    weights = calculate_inverse_vol_weights(
        selected_symbols,
        returns,
        vol_window=config.weights.vol_window,
    )

    if not weights:
        return {}

    # Apply weight caps
    weights = apply_weight_caps(weights, config.weights.max_weight_per_asset)

    # Apply cash buffer
    weights = apply_cash_buffer(weights, config.weights.cash_buffer)

    # Verify weights sum correctly
    total_weight = sum(weights.values())
    expected_total = 1.0 - config.weights.cash_buffer
    if abs(total_weight - expected_total) > 0.01:
        logger.warning(
            f"Weight sum ({total_weight:.4f}) does not match expected ({expected_total:.4f}), "
            "renormalizing"
        )
        if total_weight > 0:
            weights = {s: w / total_weight * expected_total for s, w in weights.items()}

    logger.info(f"Calculated weights: {weights}")
    return weights
