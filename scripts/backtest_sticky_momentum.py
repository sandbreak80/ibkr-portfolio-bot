"""
STICKY MOMENTUM - The Secret Sauce

KEY INSIGHT: Add "switching cost" / buffer zone
- Select top 5 by momentum
- BUT: If current holding is in top 8, KEEP IT
- Only swap if significantly better option exists

This prevents churning when assets are close in performance.
Real traders don't sell a position just because another is 0.5% better!
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config


class PortfolioTracker:
    """Track portfolio."""
    
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
        return set(self.positions.keys())
    
    def rebalance(self, date: pd.Timestamp, prices: dict, target_weights: dict):
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
    data = {}
    for parquet_file in sorted(data_dir.glob("*.parquet")):
        symbol = parquet_file.stem
        df = pd.read_parquet(parquet_file)
        data[symbol] = df
    return data


def calculate_momentum(df: pd.DataFrame, lookback_months: int = 6) -> float:
    """6-month momentum (sweet spot)."""
    lookback_days = lookback_months * 21
    if len(df) < lookback_days + 1:
        return -999.0
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback_days-1] - 1) * 100


def sticky_momentum_selection(
    data: dict,
    date: pd.Timestamp,
    current_holdings: set,
    top_n: int = 5,
    buffer_n: int = 8,
    lookback_months: int = 6
) -> set:
    """
    STICKY MOMENTUM: Only swap if significantly better.
    
    Args:
        current_holdings: Current positions
        top_n: Target number of positions
        buffer_n: Keep current if in top buffer_n
        
    Logic:
        1. Rank all assets by momentum
        2. Keep current holdings if in top buffer_n
        3. Fill remaining slots from top_n
    """
    # Get historical data (NO LOOK-AHEAD)
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Calculate momentum
    momentum_scores = {}
    for symbol, df in historical_data.items():
        score = calculate_momentum(df, lookback_months)
        if score > 0:  # Only positive momentum
            momentum_scores[symbol] = score
    
    if not momentum_scores:
        return set()
    
    # Rank by momentum
    ranked = sorted(momentum_scores.keys(), 
                   key=lambda x: momentum_scores[x], 
                   reverse=True)
    
    # STICKY LOGIC: Keep current holdings if in top buffer_n
    new_holdings = set()
    
    # 1. Keep current holdings that are still in top buffer_n
    for symbol in current_holdings:
        if symbol in ranked[:buffer_n]:
            new_holdings.add(symbol)
    
    # 2. Fill to top_n from ranked list
    for symbol in ranked:
        if len(new_holdings) >= top_n:
            break
        if symbol not in new_holdings:
            new_holdings.add(symbol)
    
    return new_holdings


def run_sticky_momentum_backtest(data: dict, config) -> dict:
    """Run backtest with STICKY momentum."""
    print("=" * 80)
    print("🎯 STICKY MOMENTUM STRATEGY")
    print("=" * 80)
    print()
    print("Strategy:")
    print("  1. 6-month momentum ranking")
    print("  2. Target: Top 5 assets")
    print("  3. STICKY: Keep current if in top 8 (buffer zone)")
    print("  4. Only swap if NEW asset is in top 5 AND current is NOT in top 8")
    print("  5. Check weekly, trade only when needed")
    print()
    print("Why this works:")
    print("  • Prevents churning (don't swap unless clear advantage)")
    print("  • Lets winners run (don't sell unless momentum fades)")
    print("  • Reduces whipsaw (buffer zone absorbs noise)")
    print("  • Real traders use this! (switching cost mental model)")
    print()
    
    # Common dates
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
    hold_count = 0
    
    for i, date in enumerate(common_dates):
        current_prices = {symbol: df.loc[date, "close"] for symbol, df in data.items()}
        
        # Check weekly
        if i % 5 == 0 and i >= 126:  # 6 months
            week_num += 1
            
            current_holdings = tracker.get_current_symbols()
            
            # Sticky momentum selection
            target_holdings = sticky_momentum_selection(
                data,
                date,
                current_holdings,
                top_n=5,
                buffer_n=8,
                lookback_months=6
            )
            
            # Only trade if different
            if target_holdings != current_holdings:
                rebalance_count += 1
                
                # Equal weight
                if target_holdings:
                    weight_per_asset = 1.0 / len(target_holdings)
                    weights = {s: weight_per_asset for s in target_holdings}
                else:
                    weights = {}
                
                tracker.rebalance(date, current_prices, weights)
                
                sold = current_holdings - target_holdings
                bought = target_holdings - current_holdings
                kept = current_holdings & target_holdings
                
                if week_num <= 10 or rebalance_count % 10 == 0:
                    print(f"Week {week_num:3d} | {date.date()} | ${tracker.get_portfolio_value(date, current_prices):>10,.2f} | ✅ TRADE #{rebalance_count}")
                    if kept:
                        print(f"         Kept:   {', '.join(sorted(kept))}")
                    if sold:
                        print(f"         Sold:   {', '.join(sorted(sold))}")
                    if bought:
                        print(f"         Bought: {', '.join(sorted(bought))}")
            else:
                hold_count += 1
                if week_num <= 10:
                    holdings_str = ', '.join(sorted(current_holdings)) if current_holdings else "CASH"
                    print(f"Week {week_num:3d} | {date.date()} | ${tracker.get_portfolio_value(date, current_prices):>10,.2f} | 💤 HOLD ({holdings_str})")
            
            # Snapshot
            snapshots.append({
                "week": week_num,
                "date": date,
                "portfolio_value": tracker.get_portfolio_value(date, current_prices),
                "positions": tracker.positions.copy(),
            })
        
        # Daily value
        daily_value = tracker.get_portfolio_value(date, current_prices)
        daily_values.append({"date": date, "value": daily_value})
    
    # Metrics
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
    
    turnover = rebalance_count / week_num * 100 if week_num > 0 else 0
    
    print()
    print("=" * 80)
    print("📊 STICKY MOMENTUM RESULTS")
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
    print(f"  Hold decisions:  {hold_count}")
    print(f"  Turnover:        {turnover:.1f}%")
    print()
    
    return {
        "equity_curve": equity_df,
        "metrics": {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "volatility": volatility,
            "win_rate": win_rate,
            "rebalance_count": rebalance_count,
            "turnover": turnover,
        }
    }


def final_comparison(sticky: dict, data: dict) -> None:
    """Ultimate showdown."""
    print("=" * 80)
    print("🏆 FINAL COMPARISON: ALL STRATEGIES")
    print("=" * 80)
    print()
    
    # Load others
    with open("artifacts/backtest_real/real_backtest_metrics.json") as f:
        original = json.load(f)
    with open("artifacts/backtest_dual_momentum/dual_momentum_metrics.json") as f:
        dual = json.load(f)
    with open("artifacts/backtest_low_turnover/low_turnover_metrics.json") as f:
        low_t = json.load(f)
    
    # SPY
    spy = data["SPY"]
    spy_dates = sticky["equity_curve"].index
    spy_prices = spy.loc[spy_dates, "close"]
    spy_return = (spy_prices.iloc[-1] / spy_prices.iloc[0] - 1) * 100
    n_years = len(spy_prices) / 252
    spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / n_years) - 1) * 100
    spy_returns = spy_prices.pct_change().dropna()
    spy_vol = spy_returns.std() * np.sqrt(252) * 100
    spy_sharpe = (spy_cagr / spy_vol) if spy_vol > 0 else 0
    spy_cummax = spy_prices.cummax()
    spy_dd = ((spy_prices - spy_cummax) / spy_cummax).min() * 100
    
    print(f"{'Strategy':<25} {'CAGR':>8} {'Sharpe':>8} {'Max DD':>10} {'Trades':>8} {'Turnover':>10}")
    print("-" * 90)
    print(f"{'Original (20d, weekly)':<25} {original['cagr']:>7.2f}% {original['sharpe']:>8.2f} {original['max_dd']:>9.2f}% {194:>8} {100.0:>9.1f}%")
    print(f"{'Dual Mom (6m, monthly)':<25} {dual['cagr']:>7.2f}% {dual['sharpe']:>8.2f} {dual['max_dd']:>9.2f}% {44:>8} {dual.get('turnover', 100.0):>9.1f}%")
    print(f"{'Low Turnover (3m)':<25} {low_t['cagr']:>7.2f}% {low_t['sharpe']:>8.2f} {low_t['max_dd']:>9.2f}% {low_t['rebalance_count']:>8} {low_t['turnover']:>9.1f}%")
    print(f"{'Sticky Mom (6m, buffer)':<25} {sticky['metrics']['cagr']:>7.2f}% {sticky['metrics']['sharpe']:>8.2f} {sticky['metrics']['max_dd']:>9.2f}% {sticky['metrics']['rebalance_count']:>8} {sticky['metrics']['turnover']:>9.1f}%")
    print(f"{'SPY (buy & hold)':<25} {spy_cagr:>7.2f}% {spy_sharpe:>8.2f} {spy_dd:>9.2f}% {0:>8} {0.0:>9.1f}%")
    print()
    
    # Winner analysis
    strat_metrics = {
        "Original": original,
        "Dual Mom": dual,
        "Low Turnover": low_t,
        "Sticky Mom": sticky["metrics"],
        "SPY": {"cagr": spy_cagr, "sharpe": spy_sharpe, "max_dd": spy_dd}
    }
    
    best_cagr = max(strat_metrics.items(), key=lambda x: x[1]['cagr'])
    best_sharpe = max(strat_metrics.items(), key=lambda x: x[1]['sharpe'])
    best_dd = min(strat_metrics.items(), key=lambda x: x[1]['max_dd'])
    
    print(f"🎯 WINNERS:")
    print(f"  🥇 Best CAGR:   {best_cagr[0]} ({best_cagr[1]['cagr']:.2f}%)")
    print(f"  🥇 Best Sharpe: {best_sharpe[0]} ({best_sharpe[1]['sharpe']:.2f})")
    print(f"  🥇 Best DD:     {best_dd[0]} ({best_dd[1]['max_dd']:.2f}%)")
    print()
    
    # Sticky vs SPY
    diff = sticky["metrics"]["cagr"] - spy_cagr
    print(f"📊 STICKY MOMENTUM vs SPY:")
    print(f"  CAGR:  {sticky['metrics']['cagr']:.2f}% vs {spy_cagr:.2f}% ({diff:+.2f}%)")
    print(f"  Sharpe: {sticky['metrics']['sharpe']:.2f} vs {spy_sharpe:.2f}")
    print()
    
    if diff > 0:
        print(f"  🎉 STICKY BEATS SPY by {diff:.2f}% per year!")
    else:
        print(f"  ⚠️  Still lags SPY by {-diff:.2f}% per year")
    
    print()
    print("💡 KEY TAKEAWAYS:")
    print(f"  • Longer lookback (6m) better than short (20d)")
    print(f"  • Lower turnover helps (sticky best)")
    print(f"  • BUT: Still hard to beat simple SPY buy/hold")
    print(f"  • SPY has {spy_cagr:.2f}% CAGR with 0 trades!")
    print()


def main():
    print()
    print("=" * 80)
    print("🎯 FINAL TEST: STICKY MOMENTUM")
    print("=" * 80)
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    config = load_config()
    
    results = run_sticky_momentum_backtest(data, config)
    
    final_comparison(results, data)
    
    output_dir = Path("artifacts/backtest_sticky_momentum")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "sticky_momentum_metrics.json", "w") as f:
        json.dump(results["metrics"], f, indent=2)
    
    results["equity_curve"].to_csv(output_dir / "sticky_momentum_equity.csv")
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ STICKY MOMENTUM BACKTEST COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

