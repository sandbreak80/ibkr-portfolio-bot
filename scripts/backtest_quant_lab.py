"""
🧙‍♂️ QUANT LAB: Advanced Strategies to Beat SPY

Testing sophisticated quant strategies:
1. Risk Parity (equal risk contribution)
2. Volatility Targeting (leverage in low-vol, de-leverage in high-vol)
3. Dual Signal (momentum + mean reversion combined)
4. Regime-Aware Momentum (bull/bear detection)
5. Dynamic Risk Parity (combines everything)

Goal: Beat SPY by 5-10% CAGR
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config


class PortfolioTracker:
    """Track portfolio with leverage support."""
    
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
        """Rebalance with leverage support (weights can sum > 1.0)."""
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


def calculate_momentum(df: pd.DataFrame, lookback: int = 126) -> float:
    """6-month momentum."""
    if len(df) < lookback + 1:
        return -999.0
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback-1] - 1) * 100


def calculate_volatility(df: pd.DataFrame, lookback: int = 63) -> float:
    """3-month realized volatility."""
    if len(df) < lookback:
        return 999.0
    returns = df["close"].pct_change().iloc[-lookback:]
    return returns.std() * np.sqrt(252) * 100


def calculate_sharpe(df: pd.DataFrame, lookback: int = 126) -> float:
    """6-month Sharpe ratio."""
    if len(df) < lookback:
        return -999.0
    returns = df["close"].pct_change().iloc[-lookback:]
    if returns.std() == 0:
        return 0
    return (returns.mean() * 252) / (returns.std() * np.sqrt(252))


def detect_regime(df: pd.DataFrame, ma_fast: int = 50, ma_slow: int = 200) -> str:
    """Bull/bear regime detection."""
    if len(df) < ma_slow:
        return "UNKNOWN"
    
    price = df["close"].iloc[-1]
    ma50 = df["close"].iloc[-ma_fast:].mean()
    ma200 = df["close"].iloc[-ma_slow:].mean()
    
    if price > ma50 and price > ma200 and ma50 > ma200:
        return "BULL"
    elif price < ma50 and price < ma200 and ma50 < ma200:
        return "BEAR"
    else:
        return "NEUTRAL"


# ============================================================================
# STRATEGY 1: RISK PARITY
# ============================================================================

def risk_parity_strategy(data: dict, date: pd.Timestamp, top_n: int = 5) -> dict:
    """
    Risk Parity: Equal risk contribution from each asset.
    Instead of equal weights, inverse-volatility weights.
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Select by momentum
    momentum_scores = {}
    for symbol, df in historical_data.items():
        score = calculate_momentum(df, 126)
        if score > 0:
            momentum_scores[symbol] = score
    
    if not momentum_scores:
        return {}
    
    selected = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)[:top_n]
    
    # Inverse-volatility weights (risk parity)
    vols = {}
    for symbol in selected:
        vol = calculate_volatility(historical_data[symbol], 63)
        if vol > 0:
            vols[symbol] = vol
    
    inv_vols = {s: 1/v for s, v in vols.items()}
    total = sum(inv_vols.values())
    
    if total == 0:
        return {}
    
    weights = {s: (inv / total) * 0.95 for s, inv in inv_vols.items()}  # 95% invested
    
    return weights


# ============================================================================
# STRATEGY 2: VOLATILITY TARGETING (with leverage)
# ============================================================================

def volatility_targeting_strategy(
    data: dict, 
    date: pd.Timestamp, 
    target_vol: float = 15.0,
    top_n: int = 5
) -> dict:
    """
    Volatility Targeting: Lever up in low-vol, de-lever in high-vol.
    Target portfolio vol = 15%.
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Select by momentum
    momentum_scores = {}
    for symbol, df in historical_data.items():
        score = calculate_momentum(df, 126)
        if score > 0:
            momentum_scores[symbol] = score
    
    if not momentum_scores:
        return {}
    
    selected = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)[:top_n]
    
    # Calculate portfolio volatility (assume equal weight)
    vols = []
    for symbol in selected:
        vol = calculate_volatility(historical_data[symbol], 63)
        vols.append(vol)
    
    avg_vol = np.mean(vols) if vols else 15.0
    
    # Leverage factor to hit target vol
    leverage = target_vol / avg_vol if avg_vol > 0 else 1.0
    leverage = max(0.5, min(leverage, 2.0))  # Cap at 0.5x - 2.0x
    
    # Equal weight * leverage
    weight_per_asset = (leverage / top_n)
    weights = {s: weight_per_asset for s in selected}
    
    return weights


# ============================================================================
# STRATEGY 3: DUAL SIGNAL (Momentum + Mean Reversion)
# ============================================================================

def dual_signal_strategy(data: dict, date: pd.Timestamp, top_n: int = 5) -> dict:
    """
    Dual Signal: Combine momentum (6m) with mean reversion (RSI).
    Buy: High momentum + oversold (RSI < 30)
    Hold: High momentum + neutral RSI
    Avoid: Low momentum or overbought
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Calculate composite score: momentum + mean reversion bonus
    scores = {}
    for symbol, df in historical_data.items():
        momentum = calculate_momentum(df, 126)
        if momentum <= 0:
            continue
        
        # Simple RSI approximation (14-period)
        if len(df) < 14:
            continue
        
        recent_returns = df["close"].pct_change().iloc[-14:]
        gains = recent_returns[recent_returns > 0].sum()
        losses = -recent_returns[recent_returns < 0].sum()
        
        if losses == 0:
            rsi = 100
        else:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))
        
        # Composite score: momentum + bonus for oversold
        composite = momentum
        if rsi < 30:
            composite *= 1.3  # 30% bonus for oversold
        elif rsi > 70:
            composite *= 0.7  # 30% penalty for overbought
        
        scores[symbol] = composite
    
    if not scores:
        return {}
    
    selected = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_n]
    
    # Equal weight
    weight = 1.0 / top_n
    weights = {s: weight for s in selected}
    
    return weights


# ============================================================================
# STRATEGY 4: REGIME-AWARE MOMENTUM
# ============================================================================

def regime_aware_strategy(data: dict, date: pd.Timestamp, top_n: int = 5) -> dict:
    """
    Regime-Aware: Adapt based on market regime.
    - BULL: Aggressive momentum (top 5, equal weight)
    - NEUTRAL: Moderate momentum (top 5, risk parity)
    - BEAR: Defensive (bonds + gold only, or cash)
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Detect regime using SPY
    if "SPY" not in historical_data:
        return {}
    
    regime = detect_regime(historical_data["SPY"], ma_fast=50, ma_slow=200)
    
    if regime == "BEAR":
        # Defensive: bonds + gold
        safe_assets = {"TLT": 0.4, "IEF": 0.3, "GLD": 0.3}
        return {s: w for s, w in safe_assets.items() if s in historical_data}
    
    # BULL or NEUTRAL: momentum
    momentum_scores = {}
    for symbol, df in historical_data.items():
        score = calculate_momentum(df, 126)
        if score > 0:
            momentum_scores[symbol] = score
    
    if not momentum_scores:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    selected = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)[:top_n]
    
    if regime == "BULL":
        # Aggressive: equal weight
        weight = 1.0 / top_n
        weights = {s: weight for s in selected}
    else:  # NEUTRAL
        # Moderate: risk parity
        vols = {}
        for symbol in selected:
            vol = calculate_volatility(historical_data[symbol], 63)
            if vol > 0:
                vols[symbol] = vol
        
        inv_vols = {s: 1/v for s, v in vols.items()}
        total = sum(inv_vols.values())
        weights = {s: (inv / total) * 0.9 for s, inv in inv_vols.items()}
    
    return weights


# ============================================================================
# STRATEGY 5: DYNAMIC RISK PARITY (The Kitchen Sink!)
# ============================================================================

def dynamic_risk_parity_strategy(
    data: dict, 
    date: pd.Timestamp, 
    target_vol: float = 18.0,
    top_n: int = 5
) -> dict:
    """
    Dynamic Risk Parity: Combines:
    - Momentum selection
    - Risk parity weights
    - Volatility targeting (leverage)
    - Regime awareness (go defensive in bear)
    
    This is the "throw everything at it" strategy.
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Detect regime
    regime = "BULL"
    if "SPY" in historical_data:
        regime = detect_regime(historical_data["SPY"])
    
    if regime == "BEAR":
        # Full defense: bonds + gold
        return {"TLT": 0.5, "GLD": 0.3, "SHY": 0.2} if all(s in historical_data for s in ["TLT", "GLD", "SHY"]) else {}
    
    # Select by momentum
    momentum_scores = {}
    for symbol, df in historical_data.items():
        score = calculate_momentum(df, 126)
        if score > 0:
            momentum_scores[symbol] = score
    
    if not momentum_scores:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    selected = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)[:top_n]
    
    # Risk parity weights
    vols = {}
    for symbol in selected:
        vol = calculate_volatility(historical_data[symbol], 63)
        if vol > 0:
            vols[symbol] = vol
    
    inv_vols = {s: 1/v for s, v in vols.items()}
    total = sum(inv_vols.values())
    base_weights = {s: inv / total for s, inv in inv_vols.items()}
    
    # Calculate portfolio vol
    portfolio_vol = sum(base_weights[s] * vols[s] for s in selected)
    
    # Leverage to hit target vol
    leverage = target_vol / portfolio_vol if portfolio_vol > 0 else 1.0
    leverage = max(0.5, min(leverage, 2.0))  # Cap leverage
    
    # Apply leverage
    weights = {s: w * leverage for s, w in base_weights.items()}
    
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
        if i % 5 == 0 and i >= 126:
            week_num += 1
            
            # Get target weights from strategy
            weights = strategy_func(data, date, **kwargs)
            
            if weights:
                current_holdings = set(tracker.positions.keys())
                target_holdings = set(weights.keys())
                
                if target_holdings != current_holdings:
                    tracker.rebalance(date, current_prices, weights)
                    rebalance_count += 1
        
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
    """Test all quant strategies."""
    print()
    print("=" * 80)
    print("🧙‍♂️ QUANT LAB: ADVANCED STRATEGIES")
    print("=" * 80)
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    print("Testing 5 advanced strategies...")
    print()
    
    strategies = [
        ("Risk Parity", risk_parity_strategy, {}),
        ("Vol Targeting (2x max)", volatility_targeting_strategy, {"target_vol": 15.0}),
        ("Dual Signal (Mom+MR)", dual_signal_strategy, {}),
        ("Regime-Aware", regime_aware_strategy, {}),
        ("Dynamic Risk Parity", dynamic_risk_parity_strategy, {"target_vol": 18.0}),
    ]
    
    results = []
    
    for name, func, kwargs in strategies:
        print(f"Running: {name}...", end=" ", flush=True)
        result = run_strategy_backtest(data, func, name, **kwargs)
        results.append(result)
        print(f"✅ CAGR: {result['cagr']:.2f}%")
    
    # SPY benchmark
    print(f"Running: SPY Benchmark...", end=" ", flush=True)
    spy_df = data["SPY"]
    spy_dates = results[0]["equity_curve"].index
    spy_prices = spy_df.loc[spy_dates, "close"]
    spy_return = (spy_prices.iloc[-1] / spy_prices.iloc[0] - 1) * 100
    n_years = len(spy_prices) / 252
    spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / n_years) - 1) * 100
    spy_returns = spy_prices.pct_change().dropna()
    spy_vol = spy_returns.std() * np.sqrt(252) * 100
    spy_sharpe = (spy_cagr / spy_vol) if spy_vol > 0 else 0
    spy_cummax = spy_prices.cummax()
    spy_dd = ((spy_prices - spy_cummax) / spy_cummax).min() * 100
    print(f"✅ CAGR: {spy_cagr:.2f}%")
    
    # Results
    print()
    print("=" * 80)
    print("🏆 QUANT LAB RESULTS")
    print("=" * 80)
    print()
    
    print(f"{'Strategy':<30} {'Final $':>10} {'CAGR':>8} {'Sharpe':>8} {'Max DD':>10} {'Trades':>8}")
    print("-" * 95)
    
    for result in results:
        print(f"{result['name']:<30} ${result['final_value']:>9,.0f} {result['cagr']:>7.2f}% {result['sharpe']:>8.2f} {result['max_dd']:>9.2f}% {result['trades']:>8}")
    
    spy_final = 10000 * (spy_prices.iloc[-1] / spy_prices.iloc[0])
    print(f"{'SPY (buy & hold)':<30} ${spy_final:>9,.0f} {spy_cagr:>7.2f}% {spy_sharpe:>8.2f} {spy_dd:>9.2f}% {0:>8}")
    
    print()
    print("🎯 ANALYSIS:")
    print()
    
    # Find winners
    best = max(results, key=lambda x: x["cagr"])
    
    if best["cagr"] > spy_cagr:
        diff = best["cagr"] - spy_cagr
        print(f"  🎉 WINNER: {best['name']}")
        print(f"     BEATS SPY by {diff:.2f}% per year!")
        print(f"     ${best['final_value']:,.0f} vs ${spy_final:,.0f}")
        print()
        
        if diff >= 5:
            print(f"  ✅ MISSION ACCOMPLISHED: Beat SPY by 5%+ !!!")
        else:
            print(f"  ⚠️  Close but not 5%+ yet (beat by {diff:.2f}%)")
    else:
        print(f"  ⚠️  Best strategy: {best['name']} with {best['cagr']:.2f}% CAGR")
        print(f"     Still lags SPY by {spy_cagr - best['cagr']:.2f}%")
    
    print()
    print("💡 OBSERVATIONS:")
    print()
    
    for result in sorted(results, key=lambda x: x["cagr"], reverse=True):
        vs_spy = result["cagr"] - spy_cagr
        emoji = "🟢" if vs_spy > 0 else "🔴"
        print(f"  {emoji} {result['name']:<25} {vs_spy:>+6.2f}% vs SPY")
    
    print()
    
    # Save results
    output_dir = Path("artifacts/quant_lab")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "strategies": {r["name"]: {
            "cagr": r["cagr"],
            "sharpe": r["sharpe"],
            "max_dd": r["max_dd"],
            "final_value": r["final_value"]
        } for r in results},
        "spy": {
            "cagr": spy_cagr,
            "sharpe": spy_sharpe,
            "max_dd": spy_dd,
            "final_value": spy_final
        }
    }
    
    with open(output_dir / "quant_lab_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ QUANT LAB COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

