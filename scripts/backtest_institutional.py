"""
🏛️ INSTITUTIONAL STRATEGIES

Implementing proven institutional approaches:
1. Multi-Factor Selection (Fama-French inspired)
2. Risk Parity with 2x Leverage (Bridgewater inspired)
3. Trend Following with 200-day MA (CTA inspired)

These strategies are used by:
- AQR Capital (multi-factor)
- Bridgewater (risk parity)
- Winton Group (trend following)

Goal: Beat SPY by 5-10% using proven institutional methods.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import Dict, Set

sys.path.insert(0, str(Path(__file__).parent.parent))


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


def load_real_data(data_dir: Path) -> dict:
    data = {}
    for parquet_file in sorted(data_dir.glob("*.parquet")):
        symbol = parquet_file.stem
        df = pd.read_parquet(parquet_file)
        data[symbol] = df
    return data


# ============================================================================
# FACTOR CALCULATIONS
# ============================================================================

def calculate_momentum_factor(df: pd.DataFrame, lookback: int = 126) -> float:
    """6-month momentum (Jegadeesh & Titman)."""
    if len(df) < lookback + 1:
        return -999.0
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback-1] - 1) * 100


def calculate_value_factor(df: pd.DataFrame, lookback: int = 252) -> float:
    """
    Value: Recent low price relative to 1-year range.
    Proxy for P/E or P/B (which we don't have for ETFs).
    
    Low value score = expensive (high in range)
    High value score = cheap (low in range)
    """
    if len(df) < lookback:
        return 0.0
    
    recent_prices = df["close"].iloc[-lookback:]
    current_price = df["close"].iloc[-1]
    price_range = recent_prices.max() - recent_prices.min()
    
    if price_range == 0:
        return 50.0
    
    # How far from high? (0 = at high, 100 = at low)
    pct_from_high = (recent_prices.max() - current_price) / price_range * 100
    
    return pct_from_high


def calculate_quality_factor(df: pd.DataFrame, lookback: int = 126) -> float:
    """
    Quality: Consistent returns with low volatility.
    Sharpe-like measure.
    """
    if len(df) < lookback:
        return 0.0
    
    returns = df["close"].pct_change().iloc[-lookback:]
    
    if returns.std() == 0:
        return 0.0
    
    sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252))
    
    # Convert to 0-100 scale (Sharpe 1.0 = 50, Sharpe 2.0 = 100)
    quality_score = min(max(sharpe * 50, 0), 100)
    
    return quality_score


def calculate_volatility(df: pd.DataFrame, lookback: int = 63) -> float:
    """3-month realized volatility."""
    if len(df) < lookback:
        return 999.0
    returns = df["close"].pct_change().iloc[-lookback:]
    return returns.std() * np.sqrt(252) * 100


def calculate_trend(df: pd.DataFrame, ma_period: int = 200) -> float:
    """Trend strength: % above/below MA."""
    if len(df) < ma_period:
        return 0.0
    
    current_price = df["close"].iloc[-1]
    ma = df["close"].iloc[-ma_period:].mean()
    
    return (current_price / ma - 1) * 100


# ============================================================================
# STRATEGY 1: MULTI-FACTOR SELECTION
# ============================================================================

def multi_factor_strategy(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 5,
    momentum_weight: float = 0.4,
    value_weight: float = 0.3,
    quality_weight: float = 0.3
) -> dict:
    """
    Multi-Factor Selection (AQR-style):
    - Score each asset on momentum, value, quality
    - Combine scores with weights
    - Select top N
    - Equal weight
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Calculate factor scores for each asset
    composite_scores = {}
    
    for symbol, df in historical_data.items():
        # Individual factor scores
        momentum = calculate_momentum_factor(df, 126)
        value = calculate_value_factor(df, 252)
        quality = calculate_quality_factor(df, 126)
        
        # Skip if invalid
        if momentum < -900:
            continue
        
        # Composite score (weighted average)
        composite = (
            momentum_weight * momentum +
            value_weight * value +
            quality_weight * quality
        )
        
        composite_scores[symbol] = composite
    
    if not composite_scores:
        return {}
    
    # Select top N
    selected = sorted(composite_scores.keys(), key=lambda x: composite_scores[x], reverse=True)[:top_n]
    
    # Equal weight
    weight = 1.0 / top_n
    weights = {s: weight for s in selected}
    
    return weights


# ============================================================================
# STRATEGY 2: RISK PARITY WITH 2X LEVERAGE
# ============================================================================

def risk_parity_2x_strategy(
    data: dict,
    date: pd.Timestamp,
    target_vol: float = 15.0
) -> dict:
    """
    Risk Parity with Leverage (Bridgewater-style):
    
    1. Select diverse assets: stocks, bonds, commodities, gold
    2. Weight by inverse volatility (risk parity)
    3. Apply leverage to hit target volatility (15%)
    4. Cap leverage at 2x
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Asset classes
    stocks = ["SPY", "QQQ", "IWM", "VTI", "EFA", "EEM"]
    bonds = ["TLT", "IEF", "BND", "HYG"]
    commodities = ["GLD", "SLV", "USO", "DBC"]
    
    # Select best from each class
    selected = {}
    
    for asset_class, symbols in [("stocks", stocks), ("bonds", bonds), ("commodities", commodities)]:
        candidates = {s: calculate_momentum_factor(historical_data[s], 126) 
                     for s in symbols if s in historical_data}
        
        if candidates:
            best = max(candidates, key=candidates.get)
            if candidates[best] > 0:  # Only if positive momentum
                selected[best] = historical_data[best]
    
    if not selected:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Calculate inverse-volatility weights (risk parity)
    vols = {}
    for symbol, df in selected.items():
        vol = calculate_volatility(df, 63)
        if vol > 0:
            vols[symbol] = vol
    
    inv_vols = {s: 1/v for s, v in vols.items()}
    total = sum(inv_vols.values())
    base_weights = {s: inv / total for s, inv in inv_vols.items()}
    
    # Calculate portfolio volatility
    portfolio_vol = sum(base_weights[s] * vols[s] for s in selected.keys())
    
    # Leverage to hit target vol (cap at 2x)
    leverage = target_vol / portfolio_vol if portfolio_vol > 0 else 1.0
    leverage = max(0.5, min(leverage, 2.0))
    
    # Apply leverage
    weights = {s: w * leverage for s, w in base_weights.items()}
    
    return weights


# ============================================================================
# STRATEGY 3: TREND FOLLOWING (200-DAY MA)
# ============================================================================

def trend_following_strategy(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 5,
    ma_period: int = 200
) -> dict:
    """
    Trend Following (CTA-style):
    
    1. Calculate 200-day MA for each asset
    2. Only hold assets ABOVE their 200-day MA
    3. Within trending assets, select by momentum
    4. Equal weight
    5. If no assets trending up, go to cash (SHY)
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Filter to assets above 200-day MA
    trending_up = {}
    
    for symbol, df in historical_data.items():
        trend = calculate_trend(df, ma_period)
        
        if trend > 0:  # Above MA
            momentum = calculate_momentum_factor(df, 126)
            if momentum > 0:
                trending_up[symbol] = momentum
    
    if not trending_up:
        # No uptrends → go to cash
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Select top N by momentum
    selected = sorted(trending_up.keys(), key=lambda x: trending_up[x], reverse=True)[:top_n]
    
    # Equal weight
    weight = 1.0 / len(selected)
    weights = {s: weight for s in selected}
    
    return weights


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_strategy_backtest(
    data: dict,
    strategy_func,
    strategy_name: str,
    **kwargs
) -> dict:
    """Run backtest for a strategy."""
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    
    tracker = PortfolioTracker(initial_cash=10000.0)
    daily_values = []
    
    rebalance_count = 0
    week_num = 0
    
    for i, date in enumerate(common_dates):
        current_prices = {symbol: df.loc[date, "close"] for symbol, df in data.items()}
        
        # Check weekly (after warmup period)
        if i % 5 == 0 and i >= 252:  # 1 year warmup for factors
            week_num += 1
            
            # Get target weights from strategy
            weights = strategy_func(data, date, **kwargs)
            
            if weights:
                current_holdings = set(tracker.positions.keys())
                target_holdings = set(weights.keys())
                
                # Only rebalance if holdings changed
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
    
    total_return = (equity_df["value"].iloc[-1] / equity_df["value"].iloc[0] - 1) * 100
    n_years = len(equity_df) / 252
    cagr = ((equity_df["value"].iloc[-1] / equity_df["value"].iloc[0]) ** (1 / n_years) - 1) * 100
    
    mean_ret = returns.mean() * 252
    std_ret = returns.std() * np.sqrt(252)
    sharpe = mean_ret / std_ret if std_ret > 0 else 0
    
    volatility = std_ret * 100
    
    return {
        "name": strategy_name,
        "final_value": equity_df["value"].iloc[-1],
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "volatility": volatility,
        "trades": rebalance_count,
        "equity_curve": equity_df
    }


def main():
    """Test institutional strategies."""
    print()
    print("=" * 80)
    print("🏛️  INSTITUTIONAL STRATEGIES")
    print("=" * 80)
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    print("Testing 3 institutional strategies:")
    print("  1. Multi-Factor Selection (AQR-style)")
    print("  2. Risk Parity 2x (Bridgewater-style)")
    print("  3. Trend Following 200-day (CTA-style)")
    print()
    
    strategies = [
        ("Multi-Factor", multi_factor_strategy, {"top_n": 5}),
        ("Risk Parity 2x", risk_parity_2x_strategy, {"target_vol": 15.0}),
        ("Trend Following 200d", trend_following_strategy, {"top_n": 5, "ma_period": 200}),
    ]
    
    results = []
    
    for name, func, kwargs in strategies:
        print(f"\n📊 Running: {name}")
        result = run_strategy_backtest(data, func, name, **kwargs)
        results.append(result)
        print(f"   ✅ CAGR: {result['cagr']:.2f}%, Sharpe: {result['sharpe']:.2f}")
    
    # SPY benchmark
    print(f"\n📊 Running: SPY Benchmark")
    spy_df = data["SPY"]
    spy_dates = results[0]["equity_curve"].index
    spy_prices = spy_df.loc[spy_dates, "close"]
    n_years = len(spy_prices) / 252
    spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / n_years) - 1) * 100
    spy_returns = spy_prices.pct_change().dropna()
    spy_vol = spy_returns.std() * np.sqrt(252) * 100
    spy_sharpe = (spy_cagr / spy_vol) if spy_vol > 0 else 0
    spy_cummax = spy_prices.cummax()
    spy_dd = ((spy_prices - spy_cummax) / spy_cummax).min() * 100
    spy_final = 10000 * (spy_prices.iloc[-1] / spy_prices.iloc[0])
    print(f"   ✅ CAGR: {spy_cagr:.2f}%, Sharpe: {spy_sharpe:.2f}")
    
    # Results table
    print()
    print("=" * 80)
    print("🏆 INSTITUTIONAL STRATEGIES - RESULTS")
    print("=" * 80)
    print()
    
    print(f"{'Strategy':<30} {'Final $':>10} {'CAGR':>8} {'Sharpe':>8} {'Max DD':>10} {'Trades':>8}")
    print("-" * 95)
    
    for result in results:
        print(f"{result['name']:<30} ${result['final_value']:>9,.0f} {result['cagr']:>7.2f}% {result['sharpe']:>8.2f} {result['max_dd']:>9.2f}% {result['trades']:>8}")
    
    print(f"{'SPY (buy & hold)':<30} ${spy_final:>9,.0f} {spy_cagr:>7.2f}% {spy_sharpe:>8.2f} {spy_dd:>9.2f}% {0:>8}")
    
    print()
    print("🎯 ANALYSIS:")
    print()
    
    # Find winners
    best = max(results, key=lambda x: x["cagr"])
    
    print(f"  Best Strategy: {best['name']}")
    print(f"  CAGR: {best['cagr']:.2f}%")
    print(f"  vs SPY: {best['cagr'] - spy_cagr:+.2f}%")
    print()
    
    if best["cagr"] >= spy_cagr + 5:
        print(f"  🎉🎉🎉 SUCCESS! Beat SPY by {best['cagr'] - spy_cagr:.2f}% !!!")
    elif best["cagr"] > spy_cagr:
        print(f"  🟢 Beat SPY by {best['cagr'] - spy_cagr:.2f}%")
        print(f"     (Target was +5-10%, we got +{best['cagr'] - spy_cagr:.2f}%)")
    else:
        print(f"  🔴 Still lag SPY by {spy_cagr - best['cagr']:.2f}%")
    
    print()
    print("💡 OBSERVATIONS:")
    print()
    
    for result in sorted(results, key=lambda x: x["cagr"], reverse=True):
        vs_spy = result["cagr"] - spy_cagr
        emoji = "🟢" if vs_spy >= 5 else "🟡" if vs_spy > 0 else "🔴"
        print(f"  {emoji} {result['name']:<28} {vs_spy:>+6.2f}% vs SPY | Sharpe: {result['sharpe']:.2f}")
    
    print()
    
    # Save results
    output_dir = Path("artifacts/institutional_strategies")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "strategies": {r["name"]: {
            "cagr": r["cagr"],
            "sharpe": r["sharpe"],
            "max_dd": r["max_dd"],
            "final_value": r["final_value"],
            "vs_spy": r["cagr"] - spy_cagr
        } for r in results},
        "spy": {
            "cagr": spy_cagr,
            "sharpe": spy_sharpe,
            "max_dd": spy_dd,
            "final_value": spy_final
        }
    }
    
    with open(output_dir / "institutional_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ INSTITUTIONAL STRATEGIES COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

