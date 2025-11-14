"""Backtest plotting and reporting."""
import json
from pathlib import Path

import pandas as pd

from src.core.logging import get_logger
from src.strategy.metrics import calculate_all_metrics

logger = get_logger(__name__)

try:
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")  # Non-interactive backend
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    logger.warning("Matplotlib not available, plotting disabled")


def plot_equity_curve(equity: pd.Series, output_path: Path) -> None:
    """
    Plot equity curve.

    Args:
        equity: Equity curve series
        output_path: Output file path
    """
    if not PLOTTING_AVAILABLE:
        logger.warning("Plotting not available, skipping equity curve")
        return

    if equity.empty:
        logger.warning("Empty equity series, skipping plot")
        return

    plt.figure(figsize=(12, 6))
    plt.plot(equity.index, equity.values)
    plt.title("Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved equity curve to {output_path}")


def plot_drawdown(equity: pd.Series, output_path: Path) -> None:
    """
    Plot drawdown chart.

    Args:
        equity: Equity curve series
        output_path: Output file path
    """
    if not PLOTTING_AVAILABLE:
        logger.warning("Plotting not available, skipping drawdown")
        return

    if equity.empty:
        logger.warning("Empty equity series, skipping plot")
        return

    # Calculate drawdown
    running_max = equity.expanding().max()
    drawdown = (equity - running_max) / running_max

    plt.figure(figsize=(12, 6))
    plt.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color="red")
    plt.plot(drawdown.index, drawdown.values, color="red")
    plt.title("Drawdown")
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved drawdown chart to {output_path}")


def plot_monthly_returns_heatmap(returns: pd.Series, output_path: Path) -> None:
    """
    Plot monthly returns heatmap.

    Args:
        returns: Return series
        output_path: Output file path
    """
    if not PLOTTING_AVAILABLE:
        logger.warning("Plotting not available, skipping heatmap")
        return

    if returns.empty:
        logger.warning("Empty returns series, skipping plot")
        return

    # Convert to monthly returns (ME = month end)
    monthly_returns = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)

    # Create pivot table (year x month)
    monthly_returns.index = pd.to_datetime(monthly_returns.index)
    # Convert to DataFrame if Series to allow column assignment
    if isinstance(monthly_returns, pd.Series):
        monthly_returns = monthly_returns.to_frame(name="returns")
    monthly_returns["year"] = monthly_returns.index.year
    monthly_returns["month"] = monthly_returns.index.month

    pivot = monthly_returns.pivot(index="year", columns="month", values=monthly_returns.columns[0])

    plt.figure(figsize=(12, 8))
    plt.imshow(pivot.values, aspect="auto", cmap="RdYlGn", vmin=-0.1, vmax=0.1)
    plt.colorbar(label="Monthly Return")
    plt.title("Monthly Returns Heatmap")
    plt.xlabel("Month")
    plt.ylabel("Year")
    plt.xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved monthly returns heatmap to {output_path}")


def save_metrics_json(metrics: dict[str, float], output_path: Path) -> None:
    """
    Save metrics to JSON file.

    Args:
        metrics: Dictionary with metrics
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert numpy types to Python types
    metrics_serializable = {}
    for key, value in metrics.items():
        if isinstance(value, (float, int)):
            if pd.isna(value):
                metrics_serializable[key] = None
            else:
                metrics_serializable[key] = float(value)
        else:
            metrics_serializable[key] = value

    with open(output_path, "w") as f:
        json.dump(metrics_serializable, f, indent=2)

    logger.info(f"Saved metrics to {output_path}")


def save_weights_csv(weights_history: list[dict], output_path: Path) -> None:
    """
    Save weights history to CSV.

    Args:
        weights_history: List of weight dictionaries
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for weight_dict in weights_history:
        if not weight_dict:
            continue
        for date, weights in weight_dict.items():
            for symbol, weight in weights.items():
                rows.append({"date": date, "symbol": symbol, "weight": weight})

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        logger.info(f"Saved weights to {output_path}")
    else:
        logger.warning("No weights to save")


def generate_backtest_report(
    backtest_results: dict,
    output_dir: Path,
    periods_per_year: float = 252.0,
) -> dict[str, float]:
    """
    Generate complete backtest report.

    Args:
        backtest_results: Results from run_backtest
        output_dir: Output directory for reports
        periods_per_year: Trading periods per year

    Returns:
        Dictionary with metrics
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    returns = backtest_results.get("returns", pd.Series())
    equity = backtest_results.get("equity", pd.Series())
    turnover = backtest_results.get("turnover", pd.Series())
    weights_history = backtest_results.get("weights_history", [])

    if returns.empty or equity.empty:
        logger.warning("Empty backtest results, cannot generate report")
        return {}

    # Calculate metrics
    metrics = calculate_all_metrics(returns, equity, turnover, periods_per_year)

    # Save metrics JSON
    save_metrics_json(metrics, output_dir / "metrics.json")

    # Save weights CSV
    save_weights_csv(weights_history, output_dir / "weights.csv")

    # Generate plots
    plot_equity_curve(equity, output_dir / "equity.png")
    plot_drawdown(equity, output_dir / "drawdown.png")
    plot_monthly_returns_heatmap(returns, output_dir / "heatmap.png")

    return metrics
