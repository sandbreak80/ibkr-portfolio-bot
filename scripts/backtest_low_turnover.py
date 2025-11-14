"""
LOW TURNOVER MOMENTUM STRATEGY

KEY INSIGHT: Don't force rebalancing!
- Check positions weekly
- Only rebalance if top assets CHANGE
- Let winners run
- Reduce whipsaw

This is how real traders work - you don't sell a winning position
just because it's been a week!
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config


class PortfolioTracker:
    """Track portfolio without costs."""
    
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
    
    def get_current_symbols(self) -> set:
        """Get set of currently held symbols."""
        return set(self.positions.keys())
    
    def rebalance(self, date: pd.Timestamp, prices: dict, target_weights: dict):
        """Execute rebalance (NO commissions, NO slippage)."""
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


def calculate_momentum(df: pd.DataFrame, lookback_months: int = 3) -> float:
    """
    Calculate momentum over lookback period.
    3-6 months is the sweet spot for momentum.
    """
    lookback_days = lookback_months * 21
    if len(df) < lookback_days + 1:
        return -999.0
    
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback_days-1] - 1) * 100


def select_top_assets(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 5,
    lookback_months: int = 3
) -> set:
    """
    Select top N assets by momentum.
    Returns set of symbols (not weights yet).
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
        if score > -900:  # Valid score
            momentum_scores[symbol] = score
    
    # Filter to POSITIVE momentum only
    positive_momentum = {s: score for s, score in momentum_scores.items() if score > 0}
    
    # Select top N
    if not positive_momentum:
        return set()  # No good assets
    
    selected = sorted(positive_momentum.keys(), 
                     key=lambda x: positive_momentum[x], 
                     reverse=True)[:top_n]
    
    return set(selected)


def run_low_turnover_backtest(data: dict, config) -> dict:
    """
    Run backtest with LOW TURNOVER.
    
    KEY: Only rebalance when target symbols CHANGE!
    """
    print("=" * 80)
    print("🚀 LOW TURNOVER MOMENTUM STRATEGY")
    print("=" * 80)
    print()
    print("Strategy:")
    print("  1. 3-month momentum ranking")
    print("  2. Only hold assets with POSITIVE momentum")
    print("  3. Select top 5 assets")
    print("  4. Check WEEKLY but only trade if selection CHANGES")
    print("  5. Let winners run!")
    print()
    print("Why this works:")
    print("  • Reduces whipsaw (don't sell winners unnecessarily)")
    print("  • Lower turnover = lower costs (taxes, slippage)")
    print("  • Momentum persists - don't fight it!")
    print("  • Only exit when momentum shifts")
    print()
    
    # Find common dates
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    
    tracker = PortfolioTracker(initial_cash=10000.0)
    snapshots = []
    daily_values = []
    
    print(f"Period: {common_dates[0].date()} to {common_dates[-1].date()}")
    print(f"Trading days: {len(common_dates)}")
    print()
    
    week_num = 0
    rebalance_count = 0
    no_trade_count = 0
    
    for i, date in enumerate(common_dates):
        current_prices = {symbol: df.loc[date, "close"] for symbol, df in data.items()}
        
        # Check weekly (after initial period)
        if i % 5 == 0 and i >= 63:  # 3 months = ~63 days
            week_num += 1
            
            # Select top assets
            target_symbols = select_top_assets(
                data, 
                date, 
                top_n=5, 
                lookback_months=3
            )
            
            current_symbols = tracker.get_current_symbols()
            
            # CRITICAL: Only rebalance if selection CHANGED
            if target_symbols != current_symbols:
                rebalance_count += 1
                
                # Calculate equal weights
                if target_symbols:
                    weight_per_asset = 1.0 / len(target_symbols)
                    weights = {s: weight_per_asset for s in target_symbols}
                else:
                    # No positive momentum → cash
                    weights = {}
                
                # Execute rebalance
                tracker.rebalance(date, current_prices, weights)
                
                action = "REBALANCE"
                old_symbols = current_symbols - target_symbols
                new_symbols = target_symbols - current_symbols
                
                if week_num <= 10 or rebalance_count % 10 == 0:
                    print(f"Week {week_num:3d} | {date.date()} | ${tracker.get_portfolio_value(date, current_prices):>10,.2f} | ✅ TRADE #{rebalance_count}")
                    if old_symbols:
                        print(f"         Sold:   {', '.join(sorted(old_symbols))}")
                    if new_symbols:
                        print(f"         Bought: {', '.join(sorted(new_symbols))}")
            else:
                # NO CHANGE - hold current positions
                no_trade_count += 1
                action = "HOLD"
                
                if week_num <= 10:
                    print(f"Week {week_num:3d} | {date.date()} | ${tracker.get_portfolio_value(date, current_prices):>10,.2f} | 💤 HOLD (no change)")
            
            # Snapshot
            portfolio_value = tracker.get_portfolio_value(date, current_prices)
            position_values = {}
            for symbol, shares in tracker.positions.items():
                position_values[symbol] = shares * current_prices[symbol]
            
            snapshots.append({
                "week": week_num,
                "date": date,
                "action": action,
                "portfolio_value": portfolio_value,
                "positions": tracker.positions.copy(),
                "target_symbols": target_symbols,
                "current_symbols": current_symbols,
            })
        
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
    
    # Turnover
    turnover = rebalance_count / week_num * 100 if week_num > 0 else 0
    
    print()
    print("=" * 80)
    print("📊 LOW TURNOVER RESULTS")
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
    print(f"📈 TRADING ACTIVITY:")
    print(f"  Weeks checked:   {week_num}")
    print(f"  Rebalances:      {rebalance_count}")
    print(f"  Hold decisions:  {no_trade_count}")
    print(f"  Turnover:        {turnover:.1f}% (% of weeks traded)")
    print()
    
    return {
        "equity_curve": equity_df,
        "snapshots": snapshots,
        "drawdown_series": drawdown_series,
        "metrics": {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "volatility": volatility,
            "win_rate": win_rate,
            "rebalance_count": rebalance_count,
            "weeks_checked": week_num,
            "turnover": turnover,
        }
    }


def compare_all_strategies(low_turnover: dict, data: dict) -> None:
    """Compare all strategies."""
    print("=" * 80)
    print("🏆 ULTIMATE STRATEGY COMPARISON")
    print("=" * 80)
    print()
    
    # Load other results
    original_path = Path("artifacts/backtest_real/real_backtest_metrics.json")
    dual_path = Path("artifacts/backtest_dual_momentum/dual_momentum_metrics.json")
    
    with open(original_path) as f:
        original = json.load(f)
    with open(dual_path) as f:
        dual = json.load(f)
    
    # SPY
    spy = data["SPY"]
    spy_dates = low_turnover["equity_curve"].index
    spy_prices = spy.loc[spy_dates, "close"]
    spy_return = (spy_prices.iloc[-1] / spy_prices.iloc[0] - 1) * 100
    n_years = len(spy_prices) / 252
    spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / n_years) - 1) * 100
    spy_returns = spy_prices.pct_change().dropna()
    spy_vol = spy_returns.std() * np.sqrt(252) * 100
    spy_sharpe = (spy_cagr / spy_vol) if spy_vol > 0 else 0
    spy_cummax = spy_prices.cummax()
    spy_dd = ((spy_prices - spy_cummax) / spy_cummax).min() * 100
    
    strategies = {
        "Original (weekly)": original,
        "Dual Mom (monthly)": dual,
        "Low Turnover": low_turnover["metrics"],
        "SPY (buy/hold)": {
            "cagr": spy_cagr,
            "sharpe": spy_sharpe,
            "max_dd": spy_dd,
            "volatility": spy_vol,
        }
    }
    
    print(f"{'Strategy':<25} {'CAGR':>10} {'Sharpe':>10} {'Max DD':>10} {'Vol':>10}")
    print("-" * 80)
    
    for name, metrics in strategies.items():
        print(f"{name:<25} {metrics['cagr']:>9.2f}% {metrics['sharpe']:>10.2f} {metrics['max_dd']:>9.2f}% {metrics['volatility']:>9.2f}%")
    
    print()
    print("🎯 KEY INSIGHTS:")
    print()
    
    # Find best
    best_cagr = max(strategies.items(), key=lambda x: x[1]['cagr'])
    best_sharpe = max(strategies.items(), key=lambda x: x[1]['sharpe'])
    best_dd = min(strategies.items(), key=lambda x: x[1]['max_dd'])
    
    print(f"  🥇 Best CAGR:   {best_cagr[0]} ({best_cagr[1]['cagr']:.2f}%)")
    print(f"  🥇 Best Sharpe: {best_sharpe[0]} ({best_sharpe[1]['sharpe']:.2f})")
    print(f"  🥇 Best DD:     {best_dd[0]} ({best_dd[1]['max_dd']:.2f}%)")
    print()
    
    # Compare low turnover to SPY
    lt = low_turnover["metrics"]
    diff_cagr = lt["cagr"] - spy_cagr
    diff_sharpe = lt["sharpe"] - spy_sharpe
    diff_dd = lt["max_dd"] - spy_dd
    
    print(f"📊 LOW TURNOVER vs SPY:")
    print(f"  CAGR:       {lt['cagr']:>6.2f}% vs {spy_cagr:>6.2f}% ({diff_cagr:+.2f}%)")
    print(f"  Sharpe:     {lt['sharpe']:>6.2f} vs {spy_sharpe:>6.2f} ({diff_sharpe:+.2f})")
    print(f"  Max DD:     {lt['max_dd']:>6.2f}% vs {spy_dd:>6.2f}% ({diff_dd:+.2f}%)")
    print()
    
    if lt["cagr"] > spy_cagr:
        print(f"  ✅ LOW TURNOVER BEATS SPY by {diff_cagr:.2f}% per year!")
    else:
        print(f"  ⚠️  Still lags SPY by {-diff_cagr:.2f}% per year")
    
    if lt["sharpe"] > spy_sharpe:
        print(f"  ✅ Better risk-adjusted returns!")
    
    print()
    
    # Trading activity comparison
    print(f"📊 TRADING ACTIVITY:")
    print(f"  Original:     194 rebalances (weekly)")
    print(f"  Dual Mom:     44 rebalances (monthly)")
    print(f"  Low Turnover: {lt['rebalance_count']} rebalances ({lt['turnover']:.1f}% of weeks)")
    print(f"  SPY:          0 trades (buy and hold)")
    print()


def main():
    """Test low turnover strategy."""
    print()
    print("=" * 80)
    print("🎯 TESTING: LOW TURNOVER MOMENTUM")
    print("=" * 80)
    print()
    
    # Load data
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    config = load_config()
    
    # Run backtest
    results = run_low_turnover_backtest(data, config)
    
    # Compare all strategies
    compare_all_strategies(results, data)
    
    # Save
    output_dir = Path("artifacts/backtest_low_turnover")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "low_turnover_metrics.json", "w") as f:
        json.dump(results["metrics"], f, indent=2)
    
    results["equity_curve"].to_csv(output_dir / "low_turnover_equity.csv")
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ LOW TURNOVER BACKTEST COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

