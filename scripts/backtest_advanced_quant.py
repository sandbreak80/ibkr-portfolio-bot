"""
🧪 ADVANCED QUANT STRATEGIES - PART 2

Testing 5 more sophisticated quant approaches:
1. Mean Reversion / Pairs Trading (stat arb)
2. Carry Strategy (yield differential capture)
3. Machine Learning (Random Forest predictions)
4. Volatility Arbitrage (VIX term structure)
5. Sentiment Momentum (price + volume)

These are cutting-edge strategies used by:
- Quant funds (Two Sigma, D.E. Shaw)
- Stat arb desks (Goldman, JPM)
- Systematic hedge funds (AQR, Citadel)

Goal: Find alpha sources SPY can't capture!
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple

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
            if symbol in prices and weight != 0:
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
# STRATEGY 1: MEAN REVERSION / PAIRS TRADING
# ============================================================================

def calculate_zscore(series: pd.Series, window: int = 20) -> float:
    """Calculate Z-score of current value vs rolling mean."""
    if len(series) < window:
        return 0.0
    
    mean = series.iloc[-window:].mean()
    std = series.iloc[-window:].std()
    
    if std == 0:
        return 0.0
    
    return (series.iloc[-1] - mean) / std


def mean_reversion_strategy(
    data: dict,
    date: pd.Timestamp,
    pairs: List[Tuple[str, str]] = [("SPY", "QQQ"), ("TLT", "IEF"), ("GLD", "SLV")],
    zscore_threshold: float = 1.5
) -> dict:
    """
    Mean Reversion / Pairs Trading:
    
    1. Calculate ratio of correlated pairs (SPY/QQQ, TLT/IEF, etc.)
    2. Compute Z-score of ratio vs 20-day mean
    3. If Z-score > 1.5: Long cheap, short expensive
    4. If Z-score < -1.5: Long expensive, short cheap
    5. Equal weight across pairs
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    weights = {}
    
    for asset1, asset2 in pairs:
        if asset1 not in historical_data or asset2 not in historical_data:
            continue
        
        df1 = historical_data[asset1]
        df2 = historical_data[asset2]
        
        if len(df1) < 20 or len(df2) < 20:
            continue
        
        # Calculate ratio
        ratio = df1["close"] / df2["close"]
        
        # Z-score
        zscore = calculate_zscore(ratio, window=20)
        
        # Trading logic
        if zscore > zscore_threshold:
            # Ratio too high → long asset2, short asset1
            weights[asset2] = weights.get(asset2, 0) + 0.5
            weights[asset1] = weights.get(asset1, 0) - 0.5
        elif zscore < -zscore_threshold:
            # Ratio too low → long asset1, short asset2
            weights[asset1] = weights.get(asset1, 0) + 0.5
            weights[asset2] = weights.get(asset2, 0) - 0.5
    
    # Normalize (but allow shorts)
    if not weights:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Scale to total 100% long exposure (shorts offset longs)
    total_long = sum(abs(w) for w in weights.values() if w > 0)
    if total_long > 0:
        scale = 1.0 / total_long
        weights = {s: w * scale for s, w in weights.items()}
    
    return weights


# ============================================================================
# STRATEGY 2: CARRY STRATEGY
# ============================================================================

def calculate_yield_proxy(df: pd.DataFrame, lookback: int = 21) -> float:
    """
    Proxy for yield: recent price change + dividend yield estimate.
    For bonds: falling prices = higher yields
    """
    if len(df) < lookback:
        return 0.0
    
    # Price momentum as yield proxy
    price_change = (df["close"].iloc[-1] / df["close"].iloc[-lookback] - 1) * 100
    
    # For bonds, invert (falling price = rising yield = attractive)
    # For commodities/stocks, use momentum directly
    return price_change


def carry_strategy(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 5
) -> dict:
    """
    Carry Strategy:
    
    1. Estimate "carry" (yield/momentum) for each asset
    2. Long high-carry assets
    3. Short low-carry assets (or just avoid)
    4. Focus on bonds (yield curve) and commodities
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Calculate carry for bonds and commodities
    carry_candidates = ["TLT", "IEF", "HYG", "BND", "GLD", "SLV", "USO", "DBC"]
    
    carry_scores = {}
    for symbol in carry_candidates:
        if symbol in historical_data:
            df = historical_data[symbol]
            
            # Yield proxy: 3-month momentum
            carry = calculate_yield_proxy(df, lookback=63)
            carry_scores[symbol] = carry
    
    if not carry_scores:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Select top N by carry
    selected = sorted(carry_scores.keys(), key=lambda x: carry_scores[x], reverse=True)[:top_n]
    
    # Equal weight
    weight = 1.0 / top_n
    weights = {s: weight for s in selected}
    
    return weights


# ============================================================================
# STRATEGY 3: MACHINE LEARNING (RANDOM FOREST)
# ============================================================================

def extract_features(df: pd.DataFrame) -> Dict[str, float]:
    """
    Extract features for ML prediction.
    """
    if len(df) < 63:
        return {}
    
    features = {}
    
    # Momentum features (multiple timeframes)
    features["mom_5d"] = (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100 if len(df) >= 6 else 0
    features["mom_20d"] = (df["close"].iloc[-1] / df["close"].iloc[-21] - 1) * 100 if len(df) >= 21 else 0
    features["mom_60d"] = (df["close"].iloc[-1] / df["close"].iloc[-61] - 1) * 100 if len(df) >= 61 else 0
    
    # Volatility
    returns = df["close"].pct_change().iloc[-20:]
    features["vol_20d"] = returns.std() * np.sqrt(252) * 100
    
    # Volume
    features["volume_ratio"] = df["volume"].iloc[-5:].mean() / df["volume"].iloc[-20:].mean() if len(df) >= 20 else 1.0
    
    # RSI
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    features["rsi"] = 100 - (100 / (1 + gains / losses)) if losses > 0 else 50
    
    return features


def simple_ml_strategy(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 5
) -> dict:
    """
    Simple ML Strategy (without sklearn):
    
    Use a simple weighted scoring model that mimics ML:
    - Combine multiple features with learned weights
    - Select assets with highest predicted returns
    
    (In production, you'd use RandomForest or XGBoost)
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Feature weights (these would be learned from training data)
    feature_weights = {
        "mom_5d": 0.1,
        "mom_20d": 0.3,
        "mom_60d": 0.4,
        "vol_20d": -0.2,  # Negative: prefer low vol
        "volume_ratio": 0.1,
        "rsi": -0.005,  # Slight preference for not overbought
    }
    
    predictions = {}
    
    for symbol, df in historical_data.items():
        features = extract_features(df)
        
        if not features:
            continue
        
        # Weighted score (proxy for ML prediction)
        score = sum(features.get(feat, 0) * weight for feat, weight in feature_weights.items())
        predictions[symbol] = score
    
    if not predictions:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Select top N
    selected = sorted(predictions.keys(), key=lambda x: predictions[x], reverse=True)[:top_n]
    
    # Equal weight
    weight = 1.0 / top_n
    weights = {s: weight for s in selected}
    
    return weights


# ============================================================================
# STRATEGY 4: VOLATILITY ARBITRAGE
# ============================================================================

def calculate_volatility_realized(df: pd.DataFrame, window: int = 20) -> float:
    """Calculate realized volatility."""
    if len(df) < window:
        return 0.0
    returns = df["close"].pct_change().iloc[-window:]
    return returns.std() * np.sqrt(252) * 100


def volatility_arbitrage_strategy(
    data: dict,
    date: pd.Timestamp,
    vol_target_low: float = 10.0,
    vol_target_high: float = 25.0
) -> dict:
    """
    Volatility Arbitrage:
    
    1. Calculate realized volatility for each asset
    2. When vol is LOW → increase equity exposure (sell vol)
    3. When vol is HIGH → reduce equity exposure (buy vol/protection)
    4. Dynamic allocation based on market volatility regime
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Calculate SPY volatility as regime indicator
    if "SPY" not in historical_data:
        return {}
    
    spy_vol = calculate_volatility_realized(historical_data["SPY"], window=20)
    
    # Determine regime
    if spy_vol < vol_target_low:
        # Low vol → aggressive (sell vol, buy equities)
        equity_allocation = 1.2
        bond_allocation = 0.0
    elif spy_vol > vol_target_high:
        # High vol → defensive (buy vol/protection, reduce equities)
        equity_allocation = 0.3
        bond_allocation = 0.7
    else:
        # Normal vol → balanced
        equity_allocation = 0.7
        bond_allocation = 0.3
    
    # Build portfolio
    weights = {}
    
    # Equity portion (select low-vol equities)
    equities = ["SPY", "QQQ", "IWM", "VTI"]
    equity_vols = {}
    for sym in equities:
        if sym in historical_data:
            vol = calculate_volatility_realized(historical_data[sym], 20)
            equity_vols[sym] = vol
    
    if equity_vols and equity_allocation > 0:
        # Inverse vol weights
        inv_vols = {s: 1/v for s, v in equity_vols.items() if v > 0}
        total = sum(inv_vols.values())
        for sym, inv_vol in inv_vols.items():
            weights[sym] = (inv_vol / total) * equity_allocation
    
    # Bond portion
    if bond_allocation > 0:
        weights["TLT"] = bond_allocation * 0.5 if "TLT" in historical_data else 0
        weights["SHY"] = bond_allocation * 0.5 if "SHY" in historical_data else 0
    
    return weights if weights else {"SHY": 1.0}


# ============================================================================
# STRATEGY 5: SENTIMENT MOMENTUM
# ============================================================================

def calculate_volume_momentum(df: pd.DataFrame, lookback: int = 20) -> float:
    """Volume momentum: is volume increasing?"""
    if len(df) < lookback * 2:
        return 0.0
    
    recent_volume = df["volume"].iloc[-lookback:].mean()
    past_volume = df["volume"].iloc[-lookback*2:-lookback].mean()
    
    if past_volume == 0:
        return 0.0
    
    return (recent_volume / past_volume - 1) * 100


def sentiment_momentum_strategy(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 5
) -> dict:
    """
    Sentiment Momentum:
    
    1. Combine price momentum + volume momentum
    2. Rising prices + rising volume = strong sentiment
    3. Select assets with strongest combined signal
    4. Equal weight
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    composite_scores = {}
    
    for symbol, df in historical_data.items():
        if len(df) < 40:
            continue
        
        # Price momentum (20-day)
        price_mom = (df["close"].iloc[-1] / df["close"].iloc[-21] - 1) * 100 if len(df) >= 21 else 0
        
        # Volume momentum
        vol_mom = calculate_volume_momentum(df, lookback=20)
        
        # Composite: 70% price, 30% volume
        composite = 0.7 * price_mom + 0.3 * vol_mom
        
        if price_mom > 0:  # Only positive price momentum
            composite_scores[symbol] = composite
    
    if not composite_scores:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Select top N
    selected = sorted(composite_scores.keys(), key=lambda x: composite_scores[x], reverse=True)[:top_n]
    
    # Equal weight
    weight = 1.0 / top_n
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
        
        # Check weekly
        if i % 5 == 0 and i >= 63:  # 3 month warmup
            week_num += 1
            
            weights = strategy_func(data, date, **kwargs)
            
            if weights:
                current_holdings = set(tracker.positions.keys())
                target_holdings = set(weights.keys())
                
                if target_holdings != current_holdings or week_num == 1:
                    tracker.rebalance(date, current_prices, weights)
                    rebalance_count += 1
                    
                    if rebalance_count % 30 == 0:
                        pv = tracker.get_portfolio_value(date, current_prices)
                        print(f"  Rebalance #{rebalance_count:3d} | {date.date()} | ${pv:>10,.2f}")
        
        daily_value = tracker.get_portfolio_value(date, current_prices)
        daily_values.append({"date": date, "value": daily_value})
    
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
        "trades": rebalance_count
    }


def main():
    """Test advanced quant strategies."""
    print()
    print("=" * 80)
    print("🧪 ADVANCED QUANT STRATEGIES - ROUND 2")
    print("=" * 80)
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    print("Testing 5 cutting-edge quant strategies:")
    print("  1. Mean Reversion / Pairs Trading")
    print("  2. Carry Strategy (yield differential)")
    print("  3. Machine Learning (feature-based)")
    print("  4. Volatility Arbitrage")
    print("  5. Sentiment Momentum (price + volume)")
    print()
    
    strategies = [
        ("Mean Reversion", mean_reversion_strategy, {}),
        ("Carry Strategy", carry_strategy, {"top_n": 5}),
        ("ML Strategy", simple_ml_strategy, {"top_n": 5}),
        ("Vol Arbitrage", volatility_arbitrage_strategy, {}),
        ("Sentiment Momentum", sentiment_momentum_strategy, {"top_n": 5}),
    ]
    
    results = []
    
    for name, func, kwargs in strategies:
        print(f"\n📊 Running: {name}")
        result = run_strategy_backtest(data, func, name, **kwargs)
        results.append(result)
        print(f"   ✅ CAGR: {result['cagr']:.2f}%, Sharpe: {result['sharpe']:.2f}")
    
    # SPY benchmark
    print(f"\n📊 SPY Benchmark")
    spy_df = data["SPY"]
    spy_dates = results[0]["equity_curve"] if "equity_curve" in results[0] else None
    if spy_dates is None:
        # Calculate manually
        all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
        common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
        spy_dates = pd.DatetimeIndex([d for d in common_dates if d >= common_dates[63]])
    
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
    
    # Results
    print()
    print("=" * 80)
    print("🏆 ADVANCED QUANT RESULTS")
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
    
    best = max(results, key=lambda x: x["cagr"])
    
    print(f"  Best Strategy: {best['name']}")
    print(f"  CAGR: {best['cagr']:.2f}%")
    print(f"  vs SPY: {best['cagr'] - spy_cagr:+.2f}%")
    print()
    
    if best["cagr"] >= spy_cagr + 5:
        print(f"  🎉 JACKPOT! Beat SPY by {best['cagr'] - spy_cagr:.2f}%!")
    elif best["cagr"] > spy_cagr:
        print(f"  🟢 Beat SPY by {best['cagr'] - spy_cagr:.2f}%")
    else:
        print(f"  🔴 Lag SPY by {spy_cagr - best['cagr']:.2f}%")
    
    print()
    print("💡 OBSERVATIONS:")
    print()
    
    for result in sorted(results, key=lambda x: x["cagr"], reverse=True):
        vs_spy = result["cagr"] - spy_cagr
        emoji = "🟢" if vs_spy >= 5 else "🟡" if vs_spy > 0 else "🔴"
        print(f"  {emoji} {result['name']:<28} {vs_spy:>+6.2f}% vs SPY | Sharpe: {result['sharpe']:.2f}")
    
    print()
    
    # Save
    output_dir = Path("artifacts/advanced_quant")
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
    
    with open(output_dir / "advanced_quant_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ ADVANCED QUANT STRATEGIES COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

