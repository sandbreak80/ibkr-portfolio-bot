"""
🎰 YOLO LAB: HIGH-RISK CRAZY STRATEGIES

Testing the most dangerous, explosive, YOLO strategies:
1. 100% BITO (Bitcoin ETF) - Crypto all-in
2. YOLO Momentum - Chase the hottest asset weekly
3. Martingale - Double down on losers
4. Inverse Momentum - Buy the biggest losers
5. Concentrated Sector - All-in best sector
6. 3x Leverage Combo - Maximum leverage everywhere
7. Contrarian Panic - Buy crashes, sell rallies
8. Coin Flip - Random selection (control)
9. Max Volatility - Only hold highest vol assets
10. FOMO Strategy - Buy 52-week highs

⚠️  WARNING: These strategies are DANGEROUS!
    We're testing them to show WHY they're bad.
    (But maybe one works? 🤷)

Expected results:
- High returns OR catastrophic losses
- Huge drawdowns (50%+)
- Extreme volatility
- Not for the faint of heart!
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
import random
from typing import Dict

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
            if symbol in prices and weight > 0:
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


def calculate_momentum(df: pd.DataFrame, lookback: int = 21) -> float:
    if len(df) < lookback + 1:
        return -999.0
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback-1] - 1) * 100


def calculate_volatility(df: pd.DataFrame, lookback: int = 20) -> float:
    if len(df) < lookback:
        return 0.0
    returns = df["close"].pct_change().iloc[-lookback:]
    return returns.std() * np.sqrt(252) * 100


# ============================================================================
# YOLO STRATEGY 1: 100% BITO (Bitcoin)
# ============================================================================

def bito_yolo_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    100% Bitcoin ETF (BITO).
    
    RISKS:
    - Crypto volatility (50%+ swings)
    - Not diversified AT ALL
    - Can lose 80% in bear market
    
    POTENTIAL:
    - 5x returns in bull market
    - Outperform everything in crypto rally
    """
    if "BITO" in data and date in data["BITO"].index:
        idx = data["BITO"].index.get_loc(date)
        if idx > 0:  # Has data
            return {"BITO": 1.0}
    
    return {"SHY": 1.0}


# ============================================================================
# YOLO STRATEGY 2: YOLO Momentum (Chase Hottest)
# ============================================================================

def yolo_momentum_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    All-in on the HOTTEST asset (highest 1-week momentum).
    
    RISKS:
    - Chasing momentum = buy high
    - Whipsaw on reversals
    - No diversification
    
    POTENTIAL:
    - Ride explosive trends
    - Catch moonshots early
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # 1-week momentum (YOLO!)
    momentum_scores = {}
    for symbol, df in historical_data.items():
        mom = calculate_momentum(df, lookback=5)  # 1 week
        if mom > -900:
            momentum_scores[symbol] = mom
    
    if not momentum_scores:
        return {"SHY": 1.0}
    
    # ALL-IN on hottest
    hottest = max(momentum_scores, key=momentum_scores.get)
    
    return {hottest: 1.0}


# ============================================================================
# YOLO STRATEGY 3: Martingale (Double Down on Losers)
# ============================================================================

class MartingaleTracker:
    """Track losses and doubling positions."""
    def __init__(self):
        self.losses = {}
    
    def update(self, symbol: str, is_losing: bool):
        if is_losing:
            self.losses[symbol] = self.losses.get(symbol, 0) + 1
        else:
            self.losses[symbol] = 0


martingale_tracker = MartingaleTracker()


def martingale_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Martingale: Double down on losers.
    
    Classic gambler's fallacy: "It has to go up eventually!"
    
    RISKS:
    - Can blow up FAST (2x, 4x, 8x, 16x losses)
    - Unlimited downside
    - Works until it doesn't (then you're broke)
    
    POTENTIAL:
    - If you're right, recover all losses + profit
    - Mean reversion might save you
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Find biggest loser (negative momentum)
    losers = {}
    for symbol, df in historical_data.items():
        mom = calculate_momentum(df, lookback=21)
        if mom < 0:
            losers[symbol] = mom
    
    if not losers:
        return {"SPY": 1.0}
    
    # Biggest loser
    biggest_loser = min(losers, key=losers.get)
    
    # Double down (up to 2x position)
    # In reality, you'd track actual position sizes, but simplified here
    return {biggest_loser: 1.0}


# ============================================================================
# YOLO STRATEGY 4: Inverse Momentum (Catch Falling Knives)
# ============================================================================

def inverse_momentum_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Buy the BIGGEST LOSERS (contrarian).
    
    "Buy when there's blood in the streets!"
    
    RISKS:
    - Falling knives keep falling
    - No stop losses = disaster
    - Could lose 80%+
    
    POTENTIAL:
    - Massive rebounds (V-shaped recovery)
    - Buy panic = sell euphoria
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Find 3 biggest losers (3-month)
    losers = {}
    for symbol, df in historical_data.items():
        mom = calculate_momentum(df, lookback=63)
        if mom < -900:
            continue
        losers[symbol] = mom
    
    if not losers:
        return {"SHY": 1.0}
    
    # Bottom 3
    worst_3 = sorted(losers.keys(), key=lambda x: losers[x])[:3]
    
    # Equal weight
    weight = 1.0 / len(worst_3)
    weights = {s: weight for s in worst_3}
    
    return weights


# ============================================================================
# YOLO STRATEGY 5: Concentrated Sector
# ============================================================================

def concentrated_sector_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    100% in best performing sector.
    
    All-in: Energy, Tech, Financials, etc.
    
    RISKS:
    - Sector rotation kills you
    - No diversification
    - One bad quarter = huge loss
    
    POTENTIAL:
    - Ride sector booms (energy 2022: +60%)
    - Concentrated bets = concentrated gains
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Sector ETFs
    sectors = {
        "Tech": ["XLK", "QQQ"],
        "Energy": ["XLE"],
        "Financials": ["XLF"],
        "Healthcare": ["XLV"],
        "Industrials": ["XLI"],
        "Consumer": ["XLY"],
    }
    
    # Find best sector (3-month momentum)
    sector_scores = {}
    for sector_name, symbols in sectors.items():
        available = [s for s in symbols if s in historical_data]
        if available:
            avg_mom = np.mean([
                calculate_momentum(historical_data[s], 63) 
                for s in available
            ])
            sector_scores[sector_name] = (available, avg_mom)
    
    if not sector_scores:
        return {"SPY": 1.0}
    
    # Best sector
    best_sector, (symbols, score) = max(sector_scores.items(), key=lambda x: x[1][1])
    
    # All-in on best sector
    weight = 1.0 / len(symbols)
    weights = {s: weight for s in symbols}
    
    return weights


# ============================================================================
# YOLO STRATEGY 6: 3x Leverage Combo
# ============================================================================

def max_leverage_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Maximum leverage everywhere:
    - 1.5x equities
    - 1.5x bonds
    - 1.0x commodities
    = 4x total leverage!
    
    RISKS:
    - Massive drawdowns (80%+)
    - Margin calls
    - Can go negative
    
    POTENTIAL:
    - 3-5x returns in bull market
    - Amplify everything
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    weights = {}
    
    # 1.5x equities (top momentum)
    equities = ["SPY", "QQQ", "IWM"]
    equity_scores = {}
    for sym in equities:
        if sym in historical_data:
            mom = calculate_momentum(historical_data[sym], 126)
            if mom > 0:
                equity_scores[sym] = mom
    
    if equity_scores:
        top_equity = max(equity_scores, key=equity_scores.get)
        weights[top_equity] = 1.5
    
    # 1.5x bonds
    if "TLT" in historical_data:
        weights["TLT"] = 1.5
    
    # 1x commodities
    if "GLD" in historical_data:
        weights["GLD"] = 1.0
    
    return weights if weights else {"SPY": 1.0}


# ============================================================================
# YOLO STRATEGY 7: Contrarian Panic
# ============================================================================

def contrarian_panic_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Buy crashes, sell rallies (extreme contrarian).
    
    If SPY down > 10%: All-in equities
    If SPY up > 10%: All-in cash
    
    RISKS:
    - Miss entire bull runs
    - Buy falling knives
    - Bad timing = rekt
    
    POTENTIAL:
    - Buy panic, sell greed
    - Warren Buffett style (kind of)
    """
    if "SPY" not in data or date not in data["SPY"].index:
        return {}
    
    idx = data["SPY"].index.get_loc(date)
    spy_df = data["SPY"].iloc[:idx+1]
    
    if len(spy_df) < 63:
        return {"SPY": 0.5, "SHY": 0.5}
    
    # 3-month return
    spy_return = (spy_df["close"].iloc[-1] / spy_df["close"].iloc[-64] - 1) * 100
    
    if spy_return < -10:
        # Crash → buy everything!
        return {"SPY": 0.5, "QQQ": 0.3, "IWM": 0.2}
    elif spy_return > 15:
        # Rally → sell everything, go to cash
        return {"SHY": 1.0}
    else:
        # Neutral → balanced
        return {"SPY": 0.6, "TLT": 0.4}


# ============================================================================
# YOLO STRATEGY 8: Coin Flip (Random - Control)
# ============================================================================

def coin_flip_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Random selection (control experiment).
    
    Picks 3 random assets weekly.
    
    This is our "monkey throwing darts" baseline.
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    available = list(historical_data.keys())
    
    if len(available) < 3:
        return {"SPY": 1.0}
    
    # Random seed based on date (deterministic)
    random.seed(int(date.timestamp()))
    
    selected = random.sample(available, min(3, len(available)))
    
    weight = 1.0 / len(selected)
    weights = {s: weight for s in selected}
    
    return weights


# ============================================================================
# YOLO STRATEGY 9: Max Volatility
# ============================================================================

def max_volatility_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Only hold HIGHEST volatility assets.
    
    More vol = more risk = more reward (maybe?).
    
    RISKS:
    - Huge swings
    - Emotional rollercoaster
    - Can lose 50%+ fast
    
    POTENTIAL:
    - Explosive gains
    - Capture big moves
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Calculate volatility
    vols = {}
    for symbol, df in historical_data.items():
        vol = calculate_volatility(df, 20)
        if vol > 0:
            vols[symbol] = vol
    
    if not vols:
        return {"SPY": 1.0}
    
    # Top 3 highest vol
    highest_vol = sorted(vols.keys(), key=lambda x: vols[x], reverse=True)[:3]
    
    weight = 1.0 / len(highest_vol)
    weights = {s: weight for s in highest_vol}
    
    return weights


# ============================================================================
# YOLO STRATEGY 10: FOMO (Buy 52-week highs)
# ============================================================================

def fomo_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Buy assets at 52-week highs (FOMO!).
    
    "It's going to the moon! Don't miss out!"
    
    RISKS:
    - Buy tops
    - Overpay
    - Reversal destroys you
    
    POTENTIAL:
    - Momentum continuation
    - Ride parabolic moves
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Find assets at/near 52-week highs
    near_highs = {}
    for symbol, df in historical_data.items():
        if len(df) < 252:
            continue
        
        high_52w = df["close"].iloc[-252:].max()
        current = df["close"].iloc[-1]
        
        # Within 5% of high
        if current >= high_52w * 0.95:
            near_highs[symbol] = current / high_52w
    
    if not near_highs:
        return {"SPY": 1.0}
    
    # Top 3 closest to highs
    top_3 = sorted(near_highs.keys(), key=lambda x: near_highs[x], reverse=True)[:3]
    
    weight = 1.0 / len(top_3)
    weights = {s: weight for s in top_3}
    
    return weights


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_yolo_backtest(
    data: dict,
    strategy_func,
    strategy_name: str,
    **kwargs
) -> dict:
    """Run YOLO backtest."""
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    
    tracker = PortfolioTracker(initial_cash=10000.0)
    daily_values = []
    
    rebalance_count = 0
    week_num = 0
    
    for i, date in enumerate(common_dates):
        current_prices = {symbol: df.loc[date, "close"] for symbol, df in data.items()}
        
        # Weekly rebalancing (YOLO!)
        if i % 5 == 0 and i >= 21:
            week_num += 1
            
            weights = strategy_func(data, date, **kwargs)
            
            if weights:
                tracker.rebalance(date, current_prices, weights)
                rebalance_count += 1
        
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
    
    # Best/worst day
    best_day = returns.max() * 100
    worst_day = returns.min() * 100
    
    return {
        "name": strategy_name,
        "final_value": equity_df["value"].iloc[-1],
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "volatility": volatility,
        "best_day": best_day,
        "worst_day": worst_day,
        "trades": rebalance_count
    }


def main():
    """Test YOLO strategies."""
    print()
    print("=" * 80)
    print("🎰 YOLO LAB: HIGH-RISK CRAZY STRATEGIES")
    print("=" * 80)
    print()
    print("⚠️  WARNING: These strategies are EXTREMELY RISKY!")
    print("   We're testing them for EDUCATIONAL purposes.")
    print("   DO NOT try this with real money (unless you're a degen).")
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    strategies = [
        ("100% BITO (Bitcoin)", bito_yolo_strategy, {}),
        ("YOLO Momentum", yolo_momentum_strategy, {}),
        ("Martingale", martingale_strategy, {}),
        ("Inverse Momentum", inverse_momentum_strategy, {}),
        ("Concentrated Sector", concentrated_sector_strategy, {}),
        ("3x Leverage Combo", max_leverage_strategy, {}),
        ("Contrarian Panic", contrarian_panic_strategy, {}),
        ("Coin Flip (Random)", coin_flip_strategy, {}),
        ("Max Volatility", max_volatility_strategy, {}),
        ("FOMO (52w Highs)", fomo_strategy, {}),
    ]
    
    results = []
    
    print("Testing 10 YOLO strategies:")
    for i, (name, func, kwargs) in enumerate(strategies, 1):
        print(f"  {i}. {name}")
    print()
    
    for name, func, kwargs in strategies:
        print(f"📊 Running: {name}...", end=" ", flush=True)
        result = run_yolo_backtest(data, func, name, **kwargs)
        results.append(result)
        print(f"✅ CAGR: {result['cagr']:>7.2f}%, Max DD: {result['max_dd']:>7.2f}%")
    
    # SPY
    spy_df = data["SPY"]
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    spy_dates = pd.DatetimeIndex([d for d in common_dates if d >= common_dates[21]])
    
    spy_prices = spy_df.loc[spy_dates, "close"]
    n_years = len(spy_prices) / 252
    spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / n_years) - 1) * 100
    spy_returns = spy_prices.pct_change().dropna()
    spy_vol = spy_returns.std() * np.sqrt(252) * 100
    spy_sharpe = (spy_cagr / spy_vol) if spy_vol > 0 else 0
    spy_cummax = spy_prices.cummax()
    spy_dd = ((spy_prices - spy_cummax) / spy_cummax).min() * 100
    spy_final = 10000 * (spy_prices.iloc[-1] / spy_prices.iloc[0])
    
    # Results
    print()
    print("=" * 90)
    print("🎰 YOLO LAB RESULTS")
    print("=" * 90)
    print()
    
    print(f"{'Strategy':<25} {'Final $':>10} {'CAGR':>8} {'Sharpe':>8} {'Max DD':>10} {'Vol':>8} {'Best Day':>10} {'Worst Day':>10}")
    print("-" * 115)
    
    for result in results:
        print(f"{result['name']:<25} ${result['final_value']:>9,.0f} {result['cagr']:>7.2f}% {result['sharpe']:>8.2f} {result['max_dd']:>9.2f}% {result['volatility']:>7.1f}% {result['best_day']:>9.1f}% {result['worst_day']:>9.1f}%")
    
    print(f"{'SPY (buy & hold)':<25} ${spy_final:>9,.0f} {spy_cagr:>7.2f}% {spy_sharpe:>8.2f} {spy_dd:>9.2f}% {spy_vol:>7.1f}% {spy_returns.max()*100:>9.1f}% {spy_returns.min()*100:>9.1f}%")
    
    print()
    print("=" * 90)
    print("🎯 ANALYSIS")
    print("=" * 90)
    print()
    
    # Winners and losers
    best = max(results, key=lambda x: x["cagr"])
    worst = min(results, key=lambda x: x["cagr"])
    craziest_dd = min(results, key=lambda x: x["max_dd"])
    
    print(f"🏆 BEST RETURN:    {best['name']}")
    print(f"   CAGR: {best['cagr']:.2f}%")
    print(f"   vs SPY: {best['cagr'] - spy_cagr:+.2f}%")
    print()
    
    print(f"💀 WORST RETURN:   {worst['name']}")
    print(f"   CAGR: {worst['cagr']:.2f}%")
    print(f"   Lost: ${10000 - worst['final_value']:,.0f}")
    print()
    
    print(f"🔥 BIGGEST DRAWDOWN: {craziest_dd['name']}")
    print(f"   Max DD: {craziest_dd['max_dd']:.2f}%")
    print(f"   (You'd be down ${10000 * abs(craziest_dd['max_dd']) / 100:,.0f} at worst!)")
    print()
    
    # Count winners vs losers
    winners = [r for r in results if r["cagr"] > spy_cagr]
    losers = [r for r in results if r["cagr"] < 0]
    
    print(f"📊 SUMMARY:")
    print(f"   Beat SPY: {len(winners)}/10")
    print(f"   Lost money: {len(losers)}/10")
    print()
    
    # Save
    output_dir = Path("artifacts/yolo_lab")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "strategies": {r["name"]: {
            "cagr": r["cagr"],
            "sharpe": r["sharpe"],
            "max_dd": r["max_dd"],
            "final_value": r["final_value"],
            "volatility": r["volatility"],
            "vs_spy": r["cagr"] - spy_cagr
        } for r in results},
        "spy": {
            "cagr": spy_cagr,
            "sharpe": spy_sharpe,
            "max_dd": spy_dd,
            "final_value": spy_final
        }
    }
    
    with open(output_dir / "yolo_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 90)
    print("⚠️  DISCLAIMER:")
    print("   These strategies are YOLO for a reason!")
    print("   High risk, high reward (or high loss).")
    print("   DO NOT YOLO your life savings!")
    print("=" * 90)
    print()


if __name__ == "__main__":
    main()

