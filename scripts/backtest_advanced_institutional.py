"""
🏛️ ADVANCED INSTITUTIONAL STRATEGIES - PART 2

Testing 5 more sophisticated institutional approaches:
1. Global Macro (currency/commodity cycles)
2. Market Neutral Long/Short (hedged equity)
3. Factor Timing (rotate between factors)
4. Tail Risk Hedging (VIX collar, downside protection)
5. Portable Alpha (equity beta + bond alpha)

These are strategies used by:
- Bridgewater (Global Macro)
- Citadel (Market Neutral)
- AQR (Factor Timing)
- Universa (Tail Risk)
- PIMCO (Portable Alpha)

Goal: Beat SPY using sophisticated institutional techniques!
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import Dict, Set, List

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


def calculate_momentum(df: pd.DataFrame, lookback: int = 126) -> float:
    if len(df) < lookback + 1:
        return -999.0
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback-1] - 1) * 100


def calculate_volatility(df: pd.DataFrame, lookback: int = 63) -> float:
    if len(df) < lookback:
        return 999.0
    returns = df["close"].pct_change().iloc[-lookback:]
    return returns.std() * np.sqrt(252) * 100


# ============================================================================
# STRATEGY 1: GLOBAL MACRO
# ============================================================================

def detect_commodity_cycle(data: dict, date: pd.Timestamp) -> str:
    """Detect if commodities are in bull/bear cycle."""
    commodity_symbols = ["GLD", "SLV", "USO"]
    
    historical_data = {}
    for symbol in commodity_symbols:
        if symbol in data and date in data[symbol].index:
            idx = data[symbol].index.get_loc(date)
            historical_data[symbol] = data[symbol].iloc[:idx+1]
    
    if not historical_data:
        return "NEUTRAL"
    
    # Average 6-month momentum across commodities
    avg_momentum = np.mean([
        calculate_momentum(df, 126) for df in historical_data.values()
    ])
    
    if avg_momentum > 10:
        return "BULL"
    elif avg_momentum < -10:
        return "BEAR"
    else:
        return "NEUTRAL"


def global_macro_strategy(
    data: dict,
    date: pd.Timestamp
) -> dict:
    """
    Global Macro Strategy:
    
    1. Detect commodity super-cycle (bull/bear)
    2. Detect interest rate cycle (rising/falling)
    3. Allocate based on macro regime:
       - Commodity bull → overweight commodities, energy
       - Rising rates → short bonds, long financials
       - Risk-off → long bonds, gold
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Detect commodity cycle
    commodity_cycle = detect_commodity_cycle(data, date)
    
    # Detect rate cycle (using TLT as proxy)
    rate_trend = "NEUTRAL"
    if "TLT" in historical_data:
        tlt_mom = calculate_momentum(historical_data["TLT"], 63)
        if tlt_mom < -5:  # TLT falling = rates rising
            rate_trend = "RISING"
        elif tlt_mom > 5:  # TLT rising = rates falling
            rate_trend = "FALLING"
    
    # Allocate based on macro regime
    weights = {}
    
    if commodity_cycle == "BULL":
        # Commodity bull → overweight commodities
        weights["GLD"] = 0.3
        weights["SLV"] = 0.2
        weights["USO"] = 0.2
        weights["XLE"] = 0.3  # Energy
    elif rate_trend == "RISING":
        # Rising rates → long financials, short duration
        weights["XLF"] = 0.4  # Financials
        weights["SHY"] = 0.3  # Short duration bonds
        weights["SPY"] = 0.3
    elif rate_trend == "FALLING":
        # Falling rates → long duration, growth
        weights["TLT"] = 0.4  # Long duration
        weights["QQQ"] = 0.4  # Growth/tech
        weights["XLK"] = 0.2
    else:
        # Neutral → balanced
        weights["SPY"] = 0.4
        weights["TLT"] = 0.3
        weights["GLD"] = 0.3
    
    # Filter to available
    weights = {s: w for s, w in weights.items() if s in historical_data}
    
    # Normalize
    total = sum(weights.values())
    if total > 0:
        weights = {s: w / total for s, w in weights.items()}
    
    return weights if weights else {"SHY": 1.0}


# ============================================================================
# STRATEGY 2: MARKET NEUTRAL LONG/SHORT
# ============================================================================

def market_neutral_strategy(
    data: dict,
    date: pd.Timestamp,
    long_count: int = 3,
    short_count: int = 3
) -> dict:
    """
    Market Neutral Long/Short:
    
    1. Rank all assets by 6-month momentum
    2. Long top N (highest momentum)
    3. Short bottom N (lowest momentum)
    4. Equal dollar long/short (net zero market exposure)
    5. Capture spread between winners and losers
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Calculate momentum for all assets
    momentum_scores = {}
    for symbol, df in historical_data.items():
        mom = calculate_momentum(df, 126)
        if mom > -900:
            momentum_scores[symbol] = mom
    
    if len(momentum_scores) < (long_count + short_count):
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Rank by momentum
    ranked = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)
    
    # Long top N
    longs = ranked[:long_count]
    
    # Short bottom N
    shorts = ranked[-short_count:]
    
    # Equal weight long/short
    long_weight = 0.5 / long_count
    short_weight = -0.5 / short_count
    
    weights = {}
    for symbol in longs:
        weights[symbol] = long_weight
    
    for symbol in shorts:
        weights[symbol] = short_weight
    
    return weights


# ============================================================================
# STRATEGY 3: FACTOR TIMING
# ============================================================================

def calculate_factor_momentum(data: dict, date: pd.Timestamp, factor_etfs: List[str]) -> Dict[str, float]:
    """Calculate recent performance of each factor."""
    scores = {}
    
    for symbol in factor_etfs:
        if symbol in data and date in data[symbol].index:
            idx = data[symbol].index.get_loc(date)
            df = data[symbol].iloc[:idx+1]
            
            # 3-month momentum for factor timing
            mom = calculate_momentum(df, 63)
            scores[symbol] = mom
    
    return scores


def factor_timing_strategy(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 3
) -> dict:
    """
    Factor Timing Strategy:
    
    1. Identify factor ETFs: value, momentum, quality, growth, etc.
    2. Rotate to factors with strongest recent performance
    3. Overweight winning factors, underweight losing factors
    
    (In real life, you'd use factor-pure ETFs or construct factors)
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Map assets to factors (simplified - in reality use factor ETFs)
    factor_map = {
        "Value": ["XLF", "XLE", "VNQ"],  # Financials, Energy, REITs (value)
        "Momentum": ["QQQ", "XLK", "XLY"],  # Tech, Discretionary (momentum)
        "Quality": ["XLV", "XLP"],  # Healthcare, Staples (quality)
        "Growth": ["QQQ", "XLK"],  # Tech (growth)
        "Defensive": ["TLT", "GLD", "SHY"],  # Bonds, Gold (defensive)
    }
    
    # Calculate momentum for each factor
    factor_scores = {}
    for factor_name, symbols in factor_map.items():
        available_symbols = [s for s in symbols if s in historical_data]
        if available_symbols:
            # Average momentum across factor's symbols
            avg_mom = np.mean([
                calculate_momentum(historical_data[s], 63) 
                for s in available_symbols
            ])
            factor_scores[factor_name] = (available_symbols, avg_mom)
    
    if not factor_scores:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Select top N factors
    top_factors = sorted(factor_scores.items(), key=lambda x: x[1][1], reverse=True)[:top_n]
    
    # Allocate across top factors
    weights = {}
    weight_per_factor = 1.0 / top_n
    
    for factor_name, (symbols, score) in top_factors:
        weight_per_symbol = weight_per_factor / len(symbols)
        for symbol in symbols:
            weights[symbol] = weights.get(symbol, 0) + weight_per_symbol
    
    return weights


# ============================================================================
# STRATEGY 4: TAIL RISK HEDGING
# ============================================================================

def calculate_drawdown_current(df: pd.DataFrame) -> float:
    """Calculate current drawdown from peak."""
    if len(df) < 20:
        return 0.0
    
    peak = df["close"].iloc[-252:].max() if len(df) >= 252 else df["close"].max()
    current = df["close"].iloc[-1]
    
    return (current / peak - 1) * 100


def tail_risk_hedging_strategy(
    data: dict,
    date: pd.Timestamp,
    equity_allocation: float = 0.90,
    hedge_budget: float = 0.10
) -> dict:
    """
    Tail Risk Hedging (Universa-style):
    
    1. 90% in equity momentum
    2. 10% in tail hedges:
       - Long volatility (would use VIX calls in real life)
       - Long bonds (flight to safety)
       - Long gold (safe haven)
    3. Increase hedge when markets near highs
    4. Reduce hedge after crashes
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    if "SPY" not in historical_data:
        return {}
    
    # Check if we're near all-time highs (vulnerable)
    spy_dd = calculate_drawdown_current(historical_data["SPY"])
    
    # Adjust hedge based on drawdown
    if spy_dd > -5:  # Near highs
        # Increase hedge
        equity_alloc = 0.85
        hedge_alloc = 0.15
    elif spy_dd < -15:  # In drawdown
        # Reduce hedge (already protected)
        equity_alloc = 0.95
        hedge_alloc = 0.05
    else:
        equity_alloc = equity_allocation
        hedge_alloc = hedge_budget
    
    # Equity portion (momentum)
    equity_symbols = ["SPY", "QQQ", "IWM"]
    momentum_scores = {}
    for sym in equity_symbols:
        if sym in historical_data:
            mom = calculate_momentum(historical_data[sym], 126)
            if mom > 0:
                momentum_scores[sym] = mom
    
    weights = {}
    
    if momentum_scores:
        # Allocate equity portion to top momentum
        top_equity = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)[:2]
        equity_weight = equity_alloc / len(top_equity)
        for sym in top_equity:
            weights[sym] = equity_weight
    
    # Hedge portion
    # In real life: VIX calls (we'll use TLT + GLD as proxies)
    if "TLT" in historical_data:
        weights["TLT"] = hedge_alloc * 0.6  # Long duration bonds
    if "GLD" in historical_data:
        weights["GLD"] = hedge_alloc * 0.4  # Gold
    
    return weights if weights else {"SHY": 1.0}


# ============================================================================
# STRATEGY 5: PORTABLE ALPHA
# ============================================================================

def portable_alpha_strategy(
    data: dict,
    date: pd.Timestamp,
    beta_allocation: float = 0.70,
    alpha_allocation: float = 0.30
) -> dict:
    """
    Portable Alpha:
    
    1. Beta (70%): Core equity exposure (SPY)
    2. Alpha (30%): Uncorrelated strategies
       - Bond momentum (alpha from fixed income)
       - Commodity momentum (alpha from commodities)
       - Carry trades (alpha from yield)
    
    Goal: Market beta + independent alpha sources
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    weights = {}
    
    # Beta portion (core equity)
    if "SPY" in historical_data:
        weights["SPY"] = beta_allocation
    
    # Alpha portion (uncorrelated strategies)
    alpha_sources = {}
    
    # Bond alpha (momentum in bonds)
    bond_symbols = ["TLT", "IEF", "HYG"]
    for sym in bond_symbols:
        if sym in historical_data:
            mom = calculate_momentum(historical_data[sym], 63)
            alpha_sources[sym] = mom
    
    # Commodity alpha
    commodity_symbols = ["GLD", "SLV", "USO"]
    for sym in commodity_symbols:
        if sym in historical_data:
            mom = calculate_momentum(historical_data[sym], 63)
            alpha_sources[sym] = mom
    
    if alpha_sources:
        # Select top 2 alpha sources
        top_alpha = sorted(alpha_sources.keys(), key=lambda x: alpha_sources[x], reverse=True)[:2]
        
        alpha_weight = alpha_allocation / len(top_alpha)
        for sym in top_alpha:
            weights[sym] = alpha_weight
    
    return weights if weights else {"SPY": 1.0}


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
    """Test advanced institutional strategies."""
    print()
    print("=" * 80)
    print("🏛️  ADVANCED INSTITUTIONAL STRATEGIES - ROUND 2")
    print("=" * 80)
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    print("Testing 5 sophisticated institutional strategies:")
    print("  1. Global Macro (Bridgewater-style)")
    print("  2. Market Neutral Long/Short (Citadel-style)")
    print("  3. Factor Timing (AQR-style)")
    print("  4. Tail Risk Hedging (Universa-style)")
    print("  5. Portable Alpha (PIMCO-style)")
    print()
    
    strategies = [
        ("Global Macro", global_macro_strategy, {}),
        ("Market Neutral L/S", market_neutral_strategy, {"long_count": 3, "short_count": 3}),
        ("Factor Timing", factor_timing_strategy, {"top_n": 3}),
        ("Tail Risk Hedging", tail_risk_hedging_strategy, {}),
        ("Portable Alpha", portable_alpha_strategy, {}),
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
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    spy_dates = pd.DatetimeIndex([d for d in common_dates if d >= common_dates[126]])
    
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
    print("🏆 ADVANCED INSTITUTIONAL RESULTS")
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
        print(f"  🎉🎉🎉 JACKPOT! Beat SPY by {best['cagr'] - spy_cagr:.2f}%!")
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
    output_dir = Path("artifacts/advanced_institutional")
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
    
    with open(output_dir / "advanced_institutional_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ ADVANCED INSTITUTIONAL STRATEGIES COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

