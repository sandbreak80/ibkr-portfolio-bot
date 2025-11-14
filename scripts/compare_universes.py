"""
Backtest comparison: 25 assets vs 30 assets

This script runs backtests on both universes using simulated realistic data
and compares their performance across multiple dimensions.
"""
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

# Asset characteristics for realistic simulation
ASSET_PROFILES = {
    # US Equity Indices - High return, high vol, correlated
    "SPY": {"return": 0.10, "vol": 0.18, "crisis": -0.4, "type": "equity"},
    "QQQ": {"return": 0.12, "vol": 0.22, "crisis": -0.35, "type": "equity"},
    "IWM": {"return": 0.11, "vol": 0.24, "crisis": -0.42, "type": "equity"},
    "DIA": {"return": 0.09, "vol": 0.17, "crisis": -0.38, "type": "equity"},
    "VTI": {"return": 0.10, "vol": 0.18, "crisis": -0.40, "type": "equity"},
    
    # Defensive Equity (30-asset only)
    "USMV": {"return": 0.08, "vol": 0.12, "crisis": -0.20, "type": "defensive"},
    "QUAL": {"return": 0.09, "vol": 0.14, "crisis": -0.25, "type": "defensive"},
    
    # Sectors
    "XLE": {"return": 0.08, "vol": 0.28, "crisis": -0.30, "type": "sector"},
    "XLF": {"return": 0.09, "vol": 0.22, "crisis": -0.45, "type": "sector"},
    "XLV": {"return": 0.10, "vol": 0.15, "crisis": -0.15, "type": "sector"},
    "XLK": {"return": 0.13, "vol": 0.23, "crisis": -0.35, "type": "sector"},
    "XLI": {"return": 0.09, "vol": 0.20, "crisis": -0.38, "type": "sector"},
    "XLY": {"return": 0.11, "vol": 0.21, "crisis": -0.40, "type": "sector"},
    
    # International
    "EFA": {"return": 0.07, "vol": 0.19, "crisis": -0.42, "type": "intl"},
    "EEM": {"return": 0.06, "vol": 0.25, "crisis": -0.50, "type": "intl"},
    "VWO": {"return": 0.06, "vol": 0.26, "crisis": -0.52, "type": "intl"},
    
    # Bonds - Low return, low vol, INVERSE crisis behavior
    "TLT": {"return": 0.03, "vol": 0.12, "crisis": +0.20, "type": "bond"},
    "IEF": {"return": 0.02, "vol": 0.06, "crisis": +0.08, "type": "bond"},
    "SHY": {"return": 0.01, "vol": 0.02, "crisis": +0.01, "type": "bond"},
    "BND": {"return": 0.02, "vol": 0.05, "crisis": +0.05, "type": "bond"},
    "HYG": {"return": 0.04, "vol": 0.10, "crisis": -0.15, "type": "bond"},
    
    # Inflation Protection (30-asset only)
    "TIP": {"return": 0.02, "vol": 0.05, "crisis": +0.03, "type": "inflation"},
    "DBC": {"return": 0.03, "vol": 0.18, "crisis": -0.10, "type": "inflation"},
    
    # Commodities
    "GLD": {"return": 0.05, "vol": 0.16, "crisis": +0.10, "type": "commodity"},
    "SLV": {"return": 0.04, "vol": 0.25, "crisis": +0.05, "type": "commodity"},
    "USO": {"return": 0.02, "vol": 0.35, "crisis": -0.40, "type": "commodity"},
    
    # Real Estate
    "VNQ": {"return": 0.08, "vol": 0.20, "crisis": -0.35, "type": "reit"},
    "VNQI": {"return": 0.06, "vol": 0.21, "crisis": -0.38, "type": "reit"},
    
    # Currency (30-asset only)
    "UUP": {"return": 0.00, "vol": 0.08, "crisis": +0.08, "type": "currency"},
    
    # Crypto
    "BITO": {"return": 0.15, "vol": 0.80, "crisis": -0.60, "type": "crypto"},
}

UNIVERSE_25 = ["SPY", "QQQ", "IWM", "DIA", "VTI", "XLE", "XLF", "XLV", "XLK", "XLI", "XLY",
               "EFA", "EEM", "VWO", "TLT", "IEF", "SHY", "BND", "HYG", "GLD", "SLV", "USO",
               "VNQ", "VNQI", "BITO"]

UNIVERSE_30 = UNIVERSE_25 + ["USMV", "QUAL", "TIP", "DBC", "UUP"]


def generate_synthetic_prices(
    symbols: list[str],
    start_date: datetime,
    end_date: datetime,
    include_crisis: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Generate synthetic but realistic price data.
    
    Includes:
    - Different return/volatility profiles per asset
    - Correlations (equity-equity high, equity-bond negative)
    - Crisis period (Mar 2020 COVID crash)
    """
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    n_days = len(dates)
    
    data = {}
    
    # Generate base market factor (affects all equities)
    market_returns = np.random.normal(0.0004, 0.012, n_days)  # ~10% annual return, 18% vol
    
    # Crisis period (Mar 2020)
    crisis_start = (datetime(2020, 2, 20) - start_date).days
    crisis_end = crisis_start + 23  # 23-day crash
    if include_crisis and 0 <= crisis_start < n_days:
        market_returns[crisis_start:crisis_end] = -0.02  # -2% per day = -35% crash
    
    for symbol in symbols:
        profile = ASSET_PROFILES[symbol]
        
        # Base returns
        daily_return = profile["return"] / 252
        daily_vol = profile["vol"] / np.sqrt(252)
        
        # Generate returns with correlation to market
        if profile["type"] in ["equity", "sector", "intl", "reit", "crypto"]:
            # Correlated with market
            beta = 0.7 if profile["type"] == "intl" else 0.8
            idiosyncratic = np.random.normal(0, daily_vol * 0.5, n_days)
            returns = daily_return + beta * market_returns + idiosyncratic
        elif profile["type"] in ["bond", "inflation", "currency"]:
            # INVERSE correlation with market (defensive)
            returns = daily_return - 0.3 * market_returns + np.random.normal(0, daily_vol, n_days)
        elif profile["type"] == "defensive":
            # Lower beta to market
            beta = 0.5
            idiosyncratic = np.random.normal(0, daily_vol * 0.5, n_days)
            returns = daily_return + beta * market_returns + idiosyncratic
        else:
            # Independent
            returns = np.random.normal(daily_return, daily_vol, n_days)
        
        # Crisis adjustment
        if include_crisis and 0 <= crisis_start < n_days:
            crisis_impact = profile["crisis"] / 23  # Spread over 23 days
            returns[crisis_start:crisis_end] += crisis_impact
        
        # Generate prices from returns
        prices = 100 * np.exp(np.cumsum(returns))
        
        # Create OHLCV DataFrame
        df = pd.DataFrame({
            "open": prices * (1 + np.random.normal(0, 0.001, n_days)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.005, n_days))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.005, n_days))),
            "close": prices,
            "volume": np.random.randint(1_000_000, 10_000_000, n_days),
        }, index=dates)
        
        # Ensure OHLC relationships
        df["high"] = df[["open", "high", "close"]].max(axis=1)
        df["low"] = df[["open", "low", "close"]].min(axis=1)
        
        data[symbol] = df
    
    return data


def run_simple_backtest(
    data: Dict[str, pd.DataFrame],
    top_n: int = 5,
    max_weight: float = 0.30,
    lookback: int = 20
) -> Dict:
    """
    Simple momentum backtest with inv-vol weighting.
    """
    # Get all dates
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    
    # Initialize
    equity = []
    portfolio_value = 10000.0
    cash = portfolio_value
    positions = {}  # symbol -> shares
    
    for i, date in enumerate(all_dates):
        if i < lookback:
            equity.append(portfolio_value)
            continue
        
        # Rebalance logic
        if i % 5 == 0:  # Rebalance every 5 days (weekly)
            # Calculate momentum scores
            scores = {}
            vols = {}
            
            for symbol, df in data.items():
                if date in df.index:
                    # Momentum: return over lookback period
                    end_idx = df.index.get_loc(date)
                    if end_idx >= lookback:
                        start_idx = end_idx - lookback
                        momentum = (df.iloc[end_idx]["close"] / df.iloc[start_idx]["close"] - 1)
                        scores[symbol] = momentum
                        
                        # Volatility
                        returns = df["close"].iloc[start_idx:end_idx+1].pct_change()
                        vols[symbol] = returns.std()
            
            # Select top N by momentum
            top_symbols = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_n]
            
            # Calculate inverse-volatility weights
            inv_vols = {s: 1 / vols[s] if vols[s] > 0 else 0 for s in top_symbols}
            total_inv_vol = sum(inv_vols.values())
            
            weights = {}
            for s in top_symbols:
                weight = (inv_vols[s] / total_inv_vol) if total_inv_vol > 0 else (1 / top_n)
                weights[s] = min(weight, max_weight)  # Cap at max_weight
            
            # Normalize
            total_weight = sum(weights.values())
            weights = {s: w / total_weight * 0.95 for s, w in weights.items()}  # 5% cash buffer
            
            # Calculate current portfolio value
            portfolio_value = cash
            for symbol, shares in positions.items():
                if symbol in data and date in data[symbol].index:
                    price = data[symbol].loc[date, "close"]
                    portfolio_value += shares * price
            
            # Liquidate all
            cash = portfolio_value
            positions = {}
            
            # Buy new positions
            for symbol, weight in weights.items():
                if symbol in data and date in data[symbol].index:
                    target_value = portfolio_value * weight
                    price = data[symbol].loc[date, "close"]
                    shares = target_value / price
                    positions[symbol] = shares
                    cash -= target_value
        
        # Calculate daily portfolio value
        portfolio_value = cash
        for symbol, shares in positions.items():
            if symbol in data and date in data[symbol].index:
                price = data[symbol].loc[date, "close"]
                portfolio_value += shares * price
        
        equity.append(portfolio_value)
    
    # Calculate metrics
    equity_series = pd.Series(equity, index=all_dates)
    returns = equity_series.pct_change().dropna()
    
    total_return = (equity[-1] / equity[0] - 1) * 100
    n_years = len(equity) / 252
    cagr = ((equity[-1] / equity[0]) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    
    mean_ret = returns.mean() * 252
    std_ret = returns.std() * np.sqrt(252)
    sharpe = mean_ret / std_ret if std_ret > 0 else 0
    
    # Max drawdown
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax
    max_dd = drawdown.min() * 100
    
    # Volatility
    volatility = std_ret * 100
    
    # Recovery time (days from max DD to recovery)
    max_dd_date = drawdown.idxmin()
    recovery_dates = equity_series[equity_series.index > max_dd_date]
    recovery_dates = recovery_dates[recovery_dates >= cummax.loc[max_dd_date]]
    recovery_time = (recovery_dates.index[0] - max_dd_date).days if len(recovery_dates) > 0 else None
    
    return {
        "equity": equity_series,
        "returns": returns,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "volatility": volatility,
        "final_equity": equity[-1],
        "recovery_time_days": recovery_time
    }


def main():
    """Run backtest comparison."""
    print("=" * 80)
    print("🔬 BACKTEST COMPARISON: 25 vs 30 ASSETS")
    print("=" * 80)
    print()
    
    # Generate data
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    print("Generating synthetic data (2020-2024)...")
    print("  • Includes realistic returns, volatilities, and correlations")
    print("  • Simulates Mar 2020 COVID crash (-35%)")
    print("  • Models inverse bond/equity correlation")
    print()
    
    data_25 = generate_synthetic_prices(UNIVERSE_25, start_date, end_date)
    data_30 = generate_synthetic_prices(UNIVERSE_30, start_date, end_date)
    
    print(f"✅ Generated {len(data_25)} symbols for 25-asset universe")
    print(f"✅ Generated {len(data_30)} symbols for 30-asset universe")
    print()
    
    # Run backtests
    print("━" * 80)
    print("📊 BACKTEST 1: 25-ASSET UNIVERSE")
    print("━" * 80)
    results_25 = run_simple_backtest(data_25, top_n=5, max_weight=0.30)
    
    print(f"Total Return:      {results_25['total_return']:>8.2f}%")
    print(f"CAGR:              {results_25['cagr']:>8.2f}%")
    print(f"Sharpe Ratio:      {results_25['sharpe']:>8.2f}")
    print(f"Max Drawdown:      {results_25['max_dd']:>8.2f}%")
    print(f"Volatility:        {results_25['volatility']:>8.2f}%")
    print(f"Final Value:       ${results_25['final_equity']:>8,.0f}")
    if results_25['recovery_time_days']:
        print(f"Recovery Time:     {results_25['recovery_time_days']:>8} days")
    print()
    
    print("━" * 80)
    print("📊 BACKTEST 2: 30-ASSET UNIVERSE (ENHANCED)")
    print("━" * 80)
    results_30 = run_simple_backtest(data_30, top_n=6, max_weight=0.25)
    
    print(f"Total Return:      {results_30['total_return']:>8.2f}%")
    print(f"CAGR:              {results_30['cagr']:>8.2f}%")
    print(f"Sharpe Ratio:      {results_30['sharpe']:>8.2f}")
    print(f"Max Drawdown:      {results_30['max_dd']:>8.2f}%")
    print(f"Volatility:        {results_30['volatility']:>8.2f}%")
    print(f"Final Value:       ${results_30['final_equity']:>8,.0f}")
    if results_30['recovery_time_days']:
        print(f"Recovery Time:     {results_30['recovery_time_days']:>8} days")
    print()
    
    # Comparison
    print("=" * 80)
    print("🏆 COMPARISON: 30-ASSET vs 25-ASSET")
    print("=" * 80)
    print()
    
    dd_improvement = ((results_25['max_dd'] - results_30['max_dd']) / abs(results_25['max_dd'])) * 100
    sharpe_improvement = ((results_30['sharpe'] - results_25['sharpe']) / results_25['sharpe']) * 100
    vol_reduction = ((results_25['volatility'] - results_30['volatility']) / results_25['volatility']) * 100
    
    comparisons = [
        ("CAGR", results_25['cagr'], results_30['cagr'], "%", False),
        ("Sharpe Ratio", results_25['sharpe'], results_30['sharpe'], "", True),
        ("Max Drawdown", results_25['max_dd'], results_30['max_dd'], "%", False),
        ("Volatility", results_25['volatility'], results_30['volatility'], "%", False),
        ("Final Value", results_25['final_equity'], results_30['final_equity'], "$", True),
    ]
    
    for metric, val_25, val_30, unit, higher_better in comparisons:
        diff = val_30 - val_25
        if unit == "$":
            diff_pct = (diff / val_25) * 100
            print(f"{metric:20s} │ 25: {unit}{val_25:>8,.2f} │ 30: {unit}{val_30:>8,.2f} │ ", end="")
        elif unit == "%":
            diff_pct = ((val_30 - val_25) / abs(val_25)) * 100 if val_25 != 0 else 0
            print(f"{metric:20s} │ 25: {val_25:>7.2f}{unit} │ 30: {val_30:>7.2f}{unit} │ ", end="")
        else:
            diff_pct = (diff / val_25) * 100 if val_25 != 0 else 0
            print(f"{metric:20s} │ 25: {val_25:>8.2f} │ 30: {val_30:>8.2f} │ ", end="")
        
        if (higher_better and diff > 0) or (not higher_better and diff < 0 and metric != "CAGR"):
            print(f"🟢 {abs(diff_pct):>5.1f}% better")
        elif abs(diff_pct) < 2:
            print(f"🟡 {abs(diff_pct):>5.1f}% similar")
        else:
            print(f"🔴 {abs(diff_pct):>5.1f}% worse")
    
    print()
    print("=" * 80)
    print("💡 KEY INSIGHTS")
    print("=" * 80)
    print()
    
    if results_30['max_dd'] < results_25['max_dd']:
        print(f"✅ 30-asset universe reduces max drawdown by {dd_improvement:.1f}%")
        print(f"   ({results_30['max_dd']:.1f}% vs {results_25['max_dd']:.1f}%)")
    
    if results_30['sharpe'] > results_25['sharpe']:
        print(f"✅ 30-asset universe improves Sharpe ratio by {sharpe_improvement:.1f}%")
        print(f"   ({results_30['sharpe']:.2f} vs {results_25['sharpe']:.2f})")
    
    if results_30['volatility'] < results_25['volatility']:
        print(f"✅ 30-asset universe reduces volatility by {vol_reduction:.1f}%")
        print(f"   ({results_30['volatility']:.1f}% vs {results_25['volatility']:.1f}%)")
    
    if results_30['recovery_time_days'] and results_25['recovery_time_days']:
        if results_30['recovery_time_days'] < results_25['recovery_time_days']:
            recovery_improvement = ((results_25['recovery_time_days'] - results_30['recovery_time_days']) / results_25['recovery_time_days']) * 100
            print(f"✅ 30-asset universe recovers {recovery_improvement:.0f}% faster from drawdowns")
            print(f"   ({results_30['recovery_time_days']} days vs {results_25['recovery_time_days']} days)")
    
    print()
    print("🎯 RECOMMENDATION:")
    if results_30['sharpe'] > results_25['sharpe'] and results_30['max_dd'] > results_25['max_dd']:
        print("   ⭐ 30-ASSET UNIVERSE provides better risk-adjusted returns")
        print("      with significantly lower drawdowns.")
    else:
        print("   Choose based on your priorities:")
        print("   • 25-asset: Simpler, potentially higher returns")
        print("   • 30-asset: Better protection, smoother returns")
    print()
    
    # Save results
    output_dir = Path("artifacts/backtest_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "results_25_assets.json", "w") as f:
        json.dump({
            "total_return": results_25['total_return'],
            "cagr": results_25['cagr'],
            "sharpe": results_25['sharpe'],
            "max_dd": results_25['max_dd'],
            "volatility": results_25['volatility'],
            "final_equity": results_25['final_equity'],
            "universe_size": 25
        }, f, indent=2)
    
    with open(output_dir / "results_30_assets.json", "w") as f:
        json.dump({
            "total_return": results_30['total_return'],
            "cagr": results_30['cagr'],
            "sharpe": results_30['sharpe'],
            "max_dd": results_30['max_dd'],
            "volatility": results_30['volatility'],
            "final_equity": results_30['final_equity'],
            "universe_size": 30
        }, f, indent=2)
    
    print(f"📁 Results saved to {output_dir}/")
    print()


if __name__ == "__main__":
    main()

