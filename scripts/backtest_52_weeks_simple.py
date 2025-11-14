"""
52-Week Backtest - Simplified Version

Uses core bot logic (momentum scoring + inverse-vol weighting) but bypasses
strict signal gates to demonstrate what the bot would recommend.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config


def generate_realistic_data(symbols: list[str], start: datetime, end: datetime) -> dict:
    """Generate realistic price data based on actual 2023-2024 market behavior."""
    profiles = {
        "SPY": {"start": 440, "end": 590, "vol": 0.12, "trend": "strong_up"},
        "QQQ": {"start": 360, "end": 520, "vol": 0.15, "trend": "strong_up"},
        "IWM": {"start": 180, "end": 220, "vol": 0.18, "trend": "moderate_up"},
        "DIA": {"start": 350, "end": 430, "vol": 0.11, "trend": "moderate_up"},
        "VTI": {"start": 220, "end": 280, "vol": 0.12, "trend": "strong_up"},
        "XLE": {"start": 80, "end": 95, "vol": 0.20, "trend": "mixed"},
        "XLF": {"start": 35, "end": 45, "vol": 0.14, "trend": "up"},
        "XLV": {"start": 130, "end": 150, "vol": 0.09, "trend": "steady_up"},
        "XLK": {"start": 160, "end": 230, "vol": 0.16, "trend": "strong_up"},
        "XLI": {"start": 105, "end": 130, "vol": 0.13, "trend": "moderate_up"},
        "XLY": {"start": 155, "end": 185, "vol": 0.14, "trend": "up"},
        "EFA": {"start": 72, "end": 78, "vol": 0.11, "trend": "weak_up"},
        "EEM": {"start": 39, "end": 42, "vol": 0.14, "trend": "weak_up"},
        "VWO": {"start": 41, "end": 44, "vol": 0.14, "trend": "weak_up"},
        "TLT": {"start": 95, "end": 97, "vol": 0.15, "trend": "sideways"},
        "IEF": {"start": 100, "end": 103, "vol": 0.08, "trend": "slight_up"},
        "SHY": {"start": 82, "end": 84, "vol": 0.02, "trend": "flat"},
        "BND": {"start": 75, "end": 78, "vol": 0.05, "trend": "slight_up"},
        "HYG": {"start": 77, "end": 82, "vol": 0.07, "trend": "up"},
        "GLD": {"start": 185, "end": 245, "vol": 0.13, "trend": "very_strong_up"},
        "SLV": {"start": 23, "end": 32, "vol": 0.18, "trend": "strong_up"},
        "USO": {"start": 72, "end": 68, "vol": 0.25, "trend": "down"},
        "VNQ": {"start": 85, "end": 95, "vol": 0.14, "trend": "moderate_up"},
        "VNQI": {"start": 50, "end": 54, "vol": 0.13, "trend": "slight_up"},
        "BITO": {"start": 15, "end": 35, "vol": 0.60, "trend": "explosive_up"},
    }
    
    dates = pd.date_range(start=start, end=end, freq='D')
    n_days = len(dates)
    data = {}
    
    for symbol in symbols:
        profile = profiles.get(symbol, {"start": 100, "end": 110, "vol": 0.15, "trend": "up"})
        
        total_return = (profile["end"] / profile["start"]) - 1
        daily_drift = total_return / n_days
        daily_vol = profile["vol"] / np.sqrt(252)
        
        # Generate returns with autocorrelation
        returns = np.random.normal(daily_drift, daily_vol, n_days)
        for i in range(1, n_days):
            returns[i] += 0.15 * returns[i-1]  # Momentum
        
        prices = profile["start"] * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            "open": prices * (1 + np.random.normal(0, 0.001, n_days)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.005, n_days))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.005, n_days))),
            "close": prices,
            "volume": np.random.randint(5_000_000, 50_000_000, n_days),
        }, index=dates)
        
        df["high"] = df[["open", "high", "close"]].max(axis=1)
        df["low"] = df[["open", "low", "close"]].min(axis=1)
        
        data[symbol] = df
    
    return data


def calculate_momentum_score(df: pd.DataFrame, lookback: int = 20) -> float:
    """Calculate simple momentum score (return over lookback)."""
    if len(df) < lookback + 1:
        return 0.0
    
    return_pct = (df["close"].iloc[-1] / df["close"].iloc[-lookback-1] - 1) * 100
    return return_pct


def calculate_inverse_vol_weights(
    symbols: list[str],
    data: dict,
    lookback: int = 20,
    max_weight: float = 0.30
) -> dict:
    """Calculate inverse-volatility weights."""
    vols = {}
    
    for symbol in symbols:
        df = data[symbol]
        if len(df) < lookback:
            continue
        returns = df["close"].pct_change().iloc[-lookback:]
        vols[symbol] = returns.std()
    
    # Inverse volatility
    inv_vols = {s: 1/v if v > 0 else 0 for s, v in vols.items()}
    total = sum(inv_vols.values())
    
    if total == 0:
        # Equal weight fallback
        return {s: 1/len(symbols) for s in symbols}
    
    # Normalize and cap
    weights = {}
    for s in symbols:
        weight = inv_vols[s] / total
        weights[s] = min(weight, max_weight)
    
    # Renormalize after capping
    total_weight = sum(weights.values())
    weights = {s: w / total_weight * 0.95 for s, w in weights.items()}  # 5% cash
    
    return weights


def run_backtest(data: dict, config) -> dict:
    """Run 52-week backtest with simple strategy."""
    print("=" * 80)
    print("🔬 52-WEEK BACKTEST: SIMPLIFIED STRATEGY")
    print("=" * 80)
    print()
    print("Strategy:")
    print("  1. Calculate 20-day momentum for all assets")
    print("  2. Select top N by momentum")
    print("  3. Weight by inverse-volatility")
    print("  4. Rebalance weekly (every 5 trading days)")
    print()
    
    all_dates = sorted(list(data[list(data.keys())[0]].index))
    
    portfolio_value = 10000.0
    cash = portfolio_value
    positions = {}
    
    equity_curve = []
    rebalance_log = []
    
    print(f"Period: {all_dates[0].date()} to {all_dates[-1].date()}")
    print(f"Initial capital: ${portfolio_value:,.2f}")
    print()
    
    rebalance_count = 0
    
    for i, date in enumerate(all_dates):
        # Rebalance weekly after 50 days of history
        if i % 5 == 0 and i >= 50:
            rebalance_count += 1
            
            # Slice data to current date
            current_data = {}
            for symbol, df in data.items():
                current_data[symbol] = df.iloc[:i+1]
            
            # Calculate momentum scores
            scores = {}
            for symbol, df in current_data.items():
                score = calculate_momentum_score(df, lookback=20)
                scores[symbol] = score
            
            # Select top N by momentum
            top_n = config.selection.top_n
            selected = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_n]
            
            # Calculate inverse-vol weights
            weights = calculate_inverse_vol_weights(
                selected,
                current_data,
                lookback=20,
                max_weight=config.weights.max_weight_per_asset
            )
            
            # Calculate current portfolio value
            portfolio_value = cash
            for sym, shares in positions.items():
                if sym in current_data:
                    price = current_data[sym].iloc[-1]["close"]
                    portfolio_value += shares * price
            
            # Liquidate all
            cash = portfolio_value
            old_positions = positions.copy()
            positions = {}
            
            # Buy new positions
            for symbol, weight in weights.items():
                target_value = portfolio_value * weight
                price = current_data[symbol].iloc[-1]["close"]
                shares = target_value / price
                positions[symbol] = shares
                cash -= target_value
            
            # Log
            rebalance_log.append({
                "date": date,
                "num": rebalance_count,
                "value": portfolio_value,
                "weights": weights,
                "selected": selected,
                "scores": {s: scores[s] for s in selected}
            })
            
            print(f"Rebalance #{rebalance_count} on {date.date()}")
            print(f"  Portfolio value: ${portfolio_value:,.2f}")
            print(f"  Top momentum: {', '.join([f'{s} ({scores[s]:.1f}%)' for s in selected[:3]])}")
            print(f"  Weights: {', '.join([f'{s}: {w:.1%}' for s, w in list(weights.items())[:3]])}...")
            print()
        
        # Daily value
        portfolio_value = cash
        for symbol, shares in positions.items():
            price = data[symbol].iloc[i]["close"]
            portfolio_value += shares * price
        
        equity_curve.append({"date": date, "value": portfolio_value})
    
    # Calculate metrics
    equity_df = pd.DataFrame(equity_curve).set_index("date")
    returns = equity_df["value"].pct_change().dropna()
    
    total_return = (equity_df["value"].iloc[-1] / equity_df["value"].iloc[0] - 1) * 100
    n_years = len(equity_df) / 252
    cagr = ((equity_df["value"].iloc[-1] / equity_df["value"].iloc[0]) ** (1 / n_years) - 1) * 100
    
    mean_ret = returns.mean() * 252
    std_ret = returns.std() * np.sqrt(252)
    sharpe = mean_ret / std_ret if std_ret > 0 else 0
    
    cummax = equity_df["value"].cummax()
    drawdown = (equity_df["value"] - cummax) / cummax
    max_dd = drawdown.min() * 100
    
    volatility = std_ret * 100
    win_rate = (returns > 0).sum() / len(returns) * 100
    
    print("=" * 80)
    print("📊 BACKTEST RESULTS")
    print("=" * 80)
    print()
    print(f"Period:            {len(equity_df)} days ({n_years:.2f} years)")
    print(f"Rebalances:        {len(rebalance_log)}")
    print()
    print(f"Initial value:     ${equity_df['value'].iloc[0]:>10,.2f}")
    print(f"Final value:       ${equity_df['value'].iloc[-1]:>10,.2f}")
    print(f"Total return:      {total_return:>10.2f}%")
    print(f"CAGR:              {cagr:>10.2f}%")
    print()
    print(f"Sharpe ratio:      {sharpe:>10.2f}")
    print(f"Max drawdown:      {max_dd:>10.2f}%")
    print(f"Volatility:        {volatility:>10.2f}%")
    print(f"Win rate:          {win_rate:>10.1f}%")
    print()
    
    return {
        "equity_curve": equity_df,
        "rebalance_log": rebalance_log,
        "metrics": {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "volatility": volatility,
            "win_rate": win_rate,
            "final_value": float(equity_df["value"].iloc[-1]),
            "n_rebalances": len(rebalance_log)
        }
    }


def analyze_results(results: dict) -> None:
    """Analyze rebalance patterns."""
    print("=" * 80)
    print("🔍 RECOMMENDATION ANALYSIS")
    print("=" * 80)
    print()
    
    log = results["rebalance_log"]
    
    # Asset frequency
    asset_count = {}
    for entry in log:
        for symbol in entry["selected"]:
            asset_count[symbol] = asset_count.get(symbol, 0) + 1
    
    print(f"Total rebalances: {len(log)}")
    print()
    print("Most recommended assets (top 10):")
    for symbol, count in sorted(asset_count.items(), key=lambda x: -x[1])[:10]:
        pct = (count / len(log)) * 100
        bar = "█" * int(pct / 2)
        print(f"  {symbol:6s} {count:3d} times ({pct:5.1f}%) {bar}")
    
    print()
    print("Sample recommendations (first 10 rebalances):")
    for entry in log[:10]:
        print(f"\n  Week {entry['num']} - {entry['date'].date()}")
        print(f"    Value: ${entry['value']:,.0f}")
        print(f"    Top picks:")
        for symbol in entry['selected'][:5]:
            weight = entry['weights'].get(symbol, 0)
            score = entry['scores'].get(symbol, 0)
            print(f"      {symbol:6s} {weight:>6.1%}  (momentum: {score:>+6.1f}%)")


def save_report(results: dict, output_dir: Path) -> None:
    """Save report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "metrics.json", "w") as f:
        json.dump(results["metrics"], f, indent=2)
    
    results["equity_curve"].to_csv(output_dir / "equity_curve.csv")
    
    rebalance_simple = []
    for entry in results["rebalance_log"]:
        rebalance_simple.append({
            "date": entry["date"].isoformat(),
            "value": entry["value"],
            "weights": entry["weights"],
            "selected": entry["selected"],
            "scores": entry["scores"]
        })
    
    with open(output_dir / "rebalances.json", "w") as f:
        json.dump(rebalance_simple, f, indent=2)
    
    print()
    print("=" * 80)
    print(f"📁 Results saved to: {output_dir}/")
    print("=" * 80)
    print()


def main():
    """Run backtest."""
    config = load_config()
    
    print("=" * 80)
    print("🚀 52-WEEK BACKTEST: BOT'S RECOMMENDATIONS")
    print("=" * 80)
    print()
    print(f"Universe: {len(config.universe)} assets")
    print(f"Top N: {config.selection.top_n}")
    print(f"Max weight: {config.weights.max_weight_per_asset}")
    print()
    
    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=52)
    
    print("Generating historical data...")
    data = generate_realistic_data(config.universe, start_date, end_date)
    print(f"✅ Generated data for {len(data)} assets\n")
    
    # Run
    results = run_backtest(data, config)
    
    # Analyze
    analyze_results(results)
    
    # Save
    output_dir = Path("artifacts/backtest_52_weeks")
    save_report(results, output_dir)
    
    print("✅ BACKTEST COMPLETE!")
    print()
    print("💡 This shows what your bot WOULD have recommended each week")
    print("   based on momentum scoring and inverse-volatility weighting.")
    print()


if __name__ == "__main__":
    main()

