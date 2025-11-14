"""
DUAL MOMENTUM STRATEGY - The Better Way

Based on Gary Antonacci's research:
1. Select assets by RELATIVE momentum (top performers)
2. Only hold if ABSOLUTE momentum is positive
3. Monthly rebalancing (not weekly)
4. Equal weight (not inverse-vol)

This is a PROVEN strategy, not curve-fitted.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config


class PortfolioTracker:
    """Track portfolio without costs (as requested)."""
    
    def __init__(self, initial_cash: float):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}
        
    def get_portfolio_value(self, date: pd.Timestamp, prices: dict) -> float:
        value = self.cash
        for symbol, shares in self.positions.items():
            if symbol in prices:
                value += shares * prices[symbol]
        return value
    
    def rebalance(self, date: pd.Timestamp, prices: dict, target_weights: dict):
        """Execute rebalance (NO commissions, NO slippage as requested)."""
        portfolio_value = self.get_portfolio_value(date, prices)
        
        target_positions = {}
        for symbol, weight in target_weights.items():
            if symbol in prices:
                target_value = portfolio_value * weight
                target_shares = target_value / prices[symbol]
                target_positions[symbol] = target_shares
        
        # Close positions not in target
        for symbol in list(self.positions.keys()):
            if symbol not in target_positions:
                shares = self.positions[symbol]
                price = prices.get(symbol, 0)
                self.cash += shares * price
                del self.positions[symbol]
        
        # Update positions
        for symbol, target_shares in target_positions.items():
            current_shares = self.positions.get(symbol, 0.0)
            delta_shares = target_shares - current_shares
            price = prices[symbol]
            self.positions[symbol] = target_shares
            self.cash -= delta_shares * price


def load_real_data(data_dir: Path) -> dict:
    """Load real historical data."""
    data = {}
    for parquet_file in sorted(data_dir.glob("*.parquet")):
        symbol = parquet_file.stem
        df = pd.read_parquet(parquet_file)
        data[symbol] = df
    return data


def calculate_momentum(df: pd.DataFrame, lookback_months: int = 6) -> float:
    """
    Calculate momentum over lookback period.
    Returns percentage change.
    """
    lookback_days = lookback_months * 21  # ~21 trading days per month
    if len(df) < lookback_days + 1:
        return -999.0  # Invalid
    
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback_days-1] - 1) * 100


def dual_momentum_strategy(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 5,
    lookback_months: int = 6,
    safe_asset: str = "SHY"  # Cash equivalent
) -> dict:
    """
    DUAL MOMENTUM STRATEGY
    
    1. Calculate momentum for all assets
    2. Filter to only positive momentum (ABSOLUTE)
    3. Select top N by momentum (RELATIVE)
    4. Equal weight
    5. If < N assets have positive momentum, allocate rest to safe asset
    """
    # Get historical data (NO LOOK-AHEAD)
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Calculate momentum for all assets
    momentum_scores = {}
    for symbol, df in historical_data.items():
        score = calculate_momentum(df, lookback_months)
        momentum_scores[symbol] = score
    
    # Filter to POSITIVE momentum (ABSOLUTE filter)
    positive_momentum = {s: score for s, score in momentum_scores.items() 
                         if score > 0 and s != safe_asset}
    
    # Select top N by momentum (RELATIVE ranking)
    if len(positive_momentum) == 0:
        # No positive momentum → all cash
        return {safe_asset: 1.0}
    
    selected = sorted(positive_momentum.keys(), 
                     key=lambda x: positive_momentum[x], 
                     reverse=True)[:top_n]
    
    # Equal weight
    if len(selected) < top_n:
        # Not enough positive momentum assets
        # Allocate proportionally to safe asset
        risk_weight = len(selected) / top_n
        safe_weight = 1.0 - risk_weight
        weight_per_asset = risk_weight / len(selected)
        
        weights = {s: weight_per_asset for s in selected}
        weights[safe_asset] = safe_weight
    else:
        # Full allocation to selected assets
        weight_per_asset = 1.0 / top_n
        weights = {s: weight_per_asset for s in selected}
    
    return weights


def run_dual_momentum_backtest(data: dict, config) -> dict:
    """Run dual momentum backtest."""
    print("=" * 80)
    print("🚀 DUAL MOMENTUM STRATEGY")
    print("=" * 80)
    print()
    print("Strategy:")
    print("  1. 6-month momentum ranking")
    print("  2. Only hold assets with POSITIVE momentum")
    print("  3. Equal weight top 5")
    print("  4. Monthly rebalancing (not weekly!)")
    print("  5. Default to cash (SHY) if no positive momentum")
    print()
    print("Why this works:")
    print("  • 6-month momentum captures real trends (not noise)")
    print("  • Absolute filter avoids falling knives")
    print("  • Monthly rebalancing reduces whipsaw")
    print("  • Equal weight doesn't overweight bonds")
    print()
    
    # Find common dates
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    
    tracker = PortfolioTracker(initial_cash=10000.0)
    weekly_snapshots = []
    daily_values = []
    
    print(f"Period: {common_dates[0].date()} to {common_dates[-1].date()}")
    print(f"Trading days: {len(common_dates)}")
    print()
    
    month_num = 0
    last_month = None
    
    for i, date in enumerate(common_dates):
        current_prices = {symbol: df.loc[date, "close"] for symbol, df in data.items()}
        
        # Rebalance MONTHLY (first trading day of month) after 126 days (6 months)
        if i >= 126 and date.month != last_month:
            month_num += 1
            last_month = date.month
            
            # Dual momentum strategy
            weights = dual_momentum_strategy(
                data, 
                date, 
                top_n=5, 
                lookback_months=6,
                safe_asset="SHY"
            )
            
            # Execute
            tracker.rebalance(date, current_prices, weights)
            portfolio_value = tracker.get_portfolio_value(date, current_prices)
            
            # Snapshot
            position_values = {}
            for symbol, shares in tracker.positions.items():
                position_values[symbol] = shares * current_prices[symbol]
            
            weekly_snapshots.append({
                "month": month_num,
                "date": date,
                "weights": weights,
                "portfolio_value": portfolio_value,
                "positions": tracker.positions.copy()
            })
            
            if month_num % 6 == 0 or month_num <= 3:
                print(f"Month {month_num:3d} | {date.date()} | ${portfolio_value:>10,.2f} | Positions: {len(tracker.positions)}")
        
        # Daily value
        daily_value = tracker.get_portfolio_value(date, current_prices)
        daily_values.append({"date": date, "value": daily_value})
    
    # Calculate metrics
    equity_df = pd.DataFrame(daily_values).set_index("date")
    returns = equity_df["value"].pct_change().dropna()
    
    cummax = equity_df["value"].cummax()
    drawdown_series = (equity_df["value"] - cummax) / cummax
    max_dd = drawdown_series.min() * 100
    max_dd_date = drawdown_series.idxmin()
    
    total_return = (equity_df["value"].iloc[-1] / equity_df["value"].iloc[0] - 1) * 100
    n_years = len(equity_df) / 252
    cagr = ((equity_df["value"].iloc[-1] / equity_df["value"].iloc[0]) ** (1 / n_years) - 1) * 100
    
    mean_ret = returns.mean() * 252
    std_ret = returns.std() * np.sqrt(252)
    sharpe = mean_ret / std_ret if std_ret > 0 else 0
    
    volatility = std_ret * 100
    win_rate = (returns > 0).sum() / len(returns) * 100
    
    print()
    print("=" * 80)
    print("📊 DUAL MOMENTUM RESULTS")
    print("=" * 80)
    print()
    print(f"Initial value:     ${equity_df['value'].iloc[0]:>10,.2f}")
    print(f"Final value:       ${equity_df['value'].iloc[-1]:>10,.2f}")
    print()
    print(f"Total return:      {total_return:>10.2f}%")
    print(f"CAGR:              {cagr:>10.2f}%")
    print()
    print(f"Sharpe ratio:      {sharpe:>10.2f}")
    print(f"Max drawdown:      {max_dd:>10.2f}%")
    print(f"  Date:            {max_dd_date.date()}")
    print(f"Volatility:        {volatility:>10.2f}%")
    print(f"Win rate:          {win_rate:>10.1f}%")
    print()
    print(f"Rebalances:        {len(weekly_snapshots)} (monthly)")
    print()
    
    return {
        "equity_curve": equity_df,
        "snapshots": weekly_snapshots,
        "drawdown_series": drawdown_series,
        "metrics": {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "volatility": volatility,
            "win_rate": win_rate,
        }
    }


def compare_strategies(dual_results: dict, original_results: dict, spy_data: pd.DataFrame) -> None:
    """Compare all strategies."""
    print("=" * 80)
    print("🏆 STRATEGY COMPARISON")
    print("=" * 80)
    print()
    
    # SPY
    spy_dates = dual_results["equity_curve"].index
    spy_prices = spy_data.loc[spy_dates, "close"]
    spy_return = (spy_prices.iloc[-1] / spy_prices.iloc[0] - 1) * 100
    n_years = len(spy_prices) / 252
    spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / n_years) - 1) * 100
    spy_returns = spy_prices.pct_change().dropna()
    spy_vol = spy_returns.std() * np.sqrt(252) * 100
    spy_sharpe = (spy_cagr / spy_vol) if spy_vol > 0 else 0
    spy_cummax = spy_prices.cummax()
    spy_dd = ((spy_prices - spy_cummax) / spy_cummax).min() * 100
    
    print(f"{'Metric':<20} {'Original':>12} {'Dual Mom':>12} {'SPY':>12} {'Winner':>10}")
    print("-" * 80)
    
    metrics = [
        ("CAGR", original_results["cagr"], dual_results["metrics"]["cagr"], spy_cagr, "%"),
        ("Sharpe Ratio", original_results["sharpe"], dual_results["metrics"]["sharpe"], spy_sharpe, ""),
        ("Max Drawdown", original_results["max_dd"], dual_results["metrics"]["max_dd"], spy_dd, "%"),
        ("Volatility", original_results["volatility"], dual_results["metrics"]["volatility"], spy_vol, "%"),
    ]
    
    for name, orig, dual, spy, unit in metrics:
        values = {"Original": orig, "Dual": dual, "SPY": spy}
        
        if name in ["CAGR", "Sharpe Ratio"]:
            winner = max(values, key=values.get)
        else:  # Lower is better
            winner = min(values, key=values.get)
        
        emoji = {"Original": "🔴", "Dual": "🟢", "SPY": "🟡"}
        
        print(f"{name:<20} {orig:>11.2f}{unit} {dual:>11.2f}{unit} {spy:>11.2f}{unit} {emoji[winner]} {winner}")
    
    print()
    print("💡 ANALYSIS:")
    
    if dual_results["metrics"]["cagr"] > spy_cagr:
        diff = dual_results["metrics"]["cagr"] - spy_cagr
        print(f"  ✅ Dual Momentum BEATS SPY by {diff:+.2f}% CAGR!")
    else:
        diff = spy_cagr - dual_results["metrics"]["cagr"]
        print(f"  ⚠️  Dual Momentum lags SPY by {diff:.2f}% CAGR")
    
    if dual_results["metrics"]["sharpe"] > spy_sharpe:
        print(f"  ✅ Better risk-adjusted returns (Sharpe: {dual_results['metrics']['sharpe']:.2f} vs {spy_sharpe:.2f})")
    
    if dual_results["metrics"]["max_dd"] > original_results["max_dd"]:
        print(f"  ✅ Smaller drawdown than original ({dual_results['metrics']['max_dd']:.1f}% vs {original_results['max_dd']:.1f}%)")
    
    print()


def main():
    """Test dual momentum strategy."""
    print()
    print("=" * 80)
    print("🎯 TESTING IMPROVED STRATEGY: DUAL MOMENTUM")
    print("=" * 80)
    print()
    
    # Load data
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    # Load config
    config = load_config()
    
    # Run dual momentum
    dual_results = run_dual_momentum_backtest(data, config)
    
    # Load original results for comparison
    original_metrics_path = Path("artifacts/backtest_real/real_backtest_metrics.json")
    with open(original_metrics_path) as f:
        original_metrics = json.load(f)
    
    # Compare
    compare_strategies(dual_results, original_metrics, data["SPY"])
    
    # Save
    output_dir = Path("artifacts/backtest_dual_momentum")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "dual_momentum_metrics.json", "w") as f:
        json.dump(dual_results["metrics"], f, indent=2)
    
    dual_results["equity_curve"].to_csv(output_dir / "dual_momentum_equity.csv")
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ DUAL MOMENTUM BACKTEST COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

