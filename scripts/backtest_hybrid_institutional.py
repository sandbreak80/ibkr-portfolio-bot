"""
🚀 HYBRID INSTITUTIONAL STRATEGY

Combining the best institutional approaches:
- 50% Trend Following 200d (11.07% CAGR)
- 30% Risk Parity 2x (0.98 Sharpe, low DD)
- 20% Multi-Factor (diversification)

Theory: Diversification across strategies reduces volatility
and may improve risk-adjusted returns.

Goal: Beat SPY by combining uncorrelated alpha sources.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import strategy functions from institutional script
from backtest_institutional import (
    load_real_data,
    multi_factor_strategy,
    risk_parity_2x_strategy,
    trend_following_strategy,
)


class PortfolioTracker:
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
        portfolio_value = self.get_portfolio_value(date, prices)
        
        target_positions = {}
        for symbol, weight in target_weights.items():
            if symbol in prices:
                target_value = portfolio_value * weight
                target_shares = target_value / prices[symbol]
                target_positions[symbol] = target_shares
        
        for symbol in list(self.positions.keys()):
            if symbol not in target_positions:
                shares = self.positions[symbol]
                price = prices.get(symbol, 0)
                self.cash += shares * price
                del self.positions[symbol]
        
        for symbol, target_shares in target_positions.items():
            current_shares = self.positions.get(symbol, 0.0)
            delta_shares = target_shares - current_shares
            price = prices[symbol]
            self.positions[symbol] = target_shares
            self.cash -= delta_shares * price


def hybrid_institutional_strategy(
    data: dict,
    date: pd.Timestamp,
    trend_weight: float = 0.50,
    rp_weight: float = 0.30,
    mf_weight: float = 0.20
) -> dict:
    """
    Hybrid Institutional Strategy:
    Allocate capital across 3 strategies, combine their signals.
    """
    # Get recommendations from each strategy
    trend_weights = trend_following_strategy(data, date, top_n=5, ma_period=200)
    rp_weights = risk_parity_2x_strategy(data, date, target_vol=15.0)
    mf_weights = multi_factor_strategy(data, date, top_n=5)
    
    # Combine weights
    all_symbols = set(trend_weights.keys()) | set(rp_weights.keys()) | set(mf_weights.keys())
    
    combined_weights = {}
    for symbol in all_symbols:
        combined = 0.0
        
        if symbol in trend_weights:
            combined += trend_weight * trend_weights[symbol]
        
        if symbol in rp_weights:
            combined += rp_weight * rp_weights[symbol]
        
        if symbol in mf_weights:
            combined += mf_weight * mf_weights[symbol]
        
        if combined > 0:
            combined_weights[symbol] = combined
    
    # Normalize to sum to ~1.0 (allow slight leverage from RP)
    total = sum(combined_weights.values())
    if total > 0:
        combined_weights = {s: w / total * 1.0 for s, w in combined_weights.items()}
    
    return combined_weights


def run_hybrid_backtest(data: dict) -> dict:
    """Run hybrid institutional backtest."""
    print("=" * 80)
    print("🚀 HYBRID INSTITUTIONAL STRATEGY")
    print("=" * 80)
    print()
    print("Strategy Allocation:")
    print("  • 50% Trend Following 200d (best CAGR)")
    print("  • 30% Risk Parity 2x (best Sharpe)")
    print("  • 20% Multi-Factor (diversification)")
    print()
    print("Theory: Combine uncorrelated alpha sources")
    print()
    
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    
    tracker = PortfolioTracker(initial_cash=10000.0)
    daily_values = []
    
    rebalance_count = 0
    week_num = 0
    
    for i, date in enumerate(common_dates):
        current_prices = {symbol: df.loc[date, "close"] for symbol, df in data.items()}
        
        # Check weekly
        if i % 5 == 0 and i >= 252:
            week_num += 1
            
            # Get hybrid weights
            weights = hybrid_institutional_strategy(
                data, 
                date,
                trend_weight=0.50,
                rp_weight=0.30,
                mf_weight=0.20
            )
            
            if weights:
                current_holdings = set(tracker.positions.keys())
                target_holdings = set(weights.keys())
                
                if target_holdings != current_holdings or week_num == 1:
                    tracker.rebalance(date, current_prices, weights)
                    rebalance_count += 1
                    
                    if rebalance_count % 20 == 0:
                        pv = tracker.get_portfolio_value(date, current_prices)
                        print(f"  Rebalance #{rebalance_count:3d} | {date.date()} | ${pv:>10,.2f}")
        
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
    
    print()
    print("=" * 80)
    print("📊 HYBRID INSTITUTIONAL RESULTS")
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
    print()
    print(f"Rebalances:        {rebalance_count}")
    print()
    
    return {
        "final_value": equity_df["value"].iloc[-1],
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "volatility": volatility,
        "trades": rebalance_count,
        "equity_curve": equity_df
    }


def main():
    print()
    print("=" * 80)
    print("🚀 TESTING: HYBRID INSTITUTIONAL STRATEGY")
    print("=" * 80)
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    result = run_hybrid_backtest(data)
    
    # Load previous results
    with open("artifacts/institutional_strategies/institutional_results.json") as f:
        prev_results = json.load(f)
    
    spy_cagr = prev_results["spy"]["cagr"]
    spy_sharpe = prev_results["spy"]["sharpe"]
    spy_dd = prev_results["spy"]["max_dd"]
    spy_final = prev_results["spy"]["final_value"]
    
    # Comparison
    print("=" * 80)
    print("🏆 FINAL COMPARISON: ALL STRATEGIES")
    print("=" * 80)
    print()
    
    print(f"{'Strategy':<30} {'Final $':>10} {'CAGR':>8} {'Sharpe':>8} {'Max DD':>10}")
    print("-" * 85)
    
    # Previous institutional strategies
    for name, metrics in sorted(prev_results["strategies"].items(), key=lambda x: x[1]["cagr"], reverse=True):
        print(f"{name:<30} ${metrics['final_value']:>9,.0f} {metrics['cagr']:>7.2f}% {metrics['sharpe']:>8.2f} {metrics['max_dd']:>9.2f}%")
    
    # Hybrid
    print(f"{'Hybrid Institutional':<30} ${result['final_value']:>9,.0f} {result['cagr']:>7.2f}% {result['sharpe']:>8.2f} {result['max_dd']:>9.2f}%")
    
    # SPY
    print(f"{'SPY (buy & hold)':<30} ${spy_final:>9,.0f} {spy_cagr:>7.2f}% {spy_sharpe:>8.2f} {spy_dd:>9.2f}%")
    
    print()
    print("🎯 VERDICT:")
    print()
    
    diff = result["cagr"] - spy_cagr
    
    if diff >= 5:
        print(f"  🎉🎉🎉 MISSION ACCOMPLISHED! 🎉🎉🎉")
        print(f"  Beat SPY by {diff:.2f}% per year!")
    elif diff > 0:
        print(f"  🟢 BEAT SPY by {diff:.2f}% per year!")
        print(f"     Target: +5-10%, Achieved: +{diff:.2f}%")
    else:
        print(f"  🔴 Hybrid lags SPY by {-diff:.2f}%")
        print()
        print(f"  BUT: Consider risk-adjusted returns:")
        print(f"    Hybrid Sharpe: {result['sharpe']:.2f}")
        print(f"    SPY Sharpe:    {spy_sharpe:.2f}")
        
        if result["sharpe"] > spy_sharpe:
            print(f"    ✅ Hybrid has BETTER risk-adjusted returns!")
    
    print()
    
    # Save
    output_dir = Path("artifacts/hybrid_institutional")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "hybrid_results.json", "w") as f:
        json.dump({
            "hybrid": {k: v for k, v in result.items() if k != "equity_curve"},
            "vs_spy": diff
        }, f, indent=2)
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ HYBRID INSTITUTIONAL STRATEGY COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

