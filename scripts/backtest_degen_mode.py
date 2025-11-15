"""
🤡 DEGEN MODE: THE MOST DEGENERATE STRATEGIES

WARNING: DO NOT TRY THESE AT HOME!

These strategies are designed to LOSE MONEY or provide entertainment value only:

1. Leveraged Options Proxy (3x daily moves)
2. Penny Stock Momentum (under $20, high volume)
3. Sentiment Analysis (volume spikes + price action)
4. WSB YOLO (single position meme stocks)
5. 0DTE Options Proxy (same-day trading simulation)
6. Breakout Chaser (buy new highs, sell new lows)
7. Reverse Correlation (do opposite of market)
8. Maximum Risk (combine ALL bad ideas)
9. Pattern Day Trader (daily in/out, max trades)
10. Pure Speculation (no analysis, just vibes)

⚠️  EXTREME RISK WARNING:
    - These strategies are GAMBLING
    - You WILL lose money
    - 90%+ chance of total loss
    - For EDUCATIONAL purposes ONLY
    - If you try this with real money, you deserve what happens

Expected results:
- Massive gains OR total loss
- 80%+ drawdowns possible
- Blown accounts
- Tears and regret
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
import random
from typing import Dict, List

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
        return max(value, 0)  # Can't go negative (account blown)
    
    def rebalance(self, date: pd.Timestamp, prices: dict, target_weights: dict):
        portfolio_value = self.get_portfolio_value(date, prices)
        
        if portfolio_value <= 100:  # Account blown
            self.cash = 0
            self.positions = {}
            return
        
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


# ============================================================================
# DEGEN 1: LEVERAGED OPTIONS PROXY (3x Daily Moves)
# ============================================================================

def leveraged_options_strategy(data: dict, date: pd.Timestamp, leverage: float = 3.0) -> dict:
    """
    Simulate leveraged options by applying 3x multiplier to daily moves.
    
    In reality: Options can give you 10x, 20x, 100x leverage
    But they also expire worthless 90% of the time
    
    We'll use top momentum asset with 3x leverage simulation
    
    RISKS:
    - Can lose EVERYTHING in one bad day
    - Decay/theta not modeled (real options worse)
    - Massive volatility
    
    POTENTIAL:
    - 10x returns in bull run
    - Catch explosive moves
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Select highest 1-week momentum (most likely to gap)
    momentum_scores = {}
    for symbol, df in historical_data.items():
        if len(df) < 6:
            continue
        mom = (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100
        momentum_scores[symbol] = mom
    
    if not momentum_scores:
        return {"SHY": 1.0}
    
    # All-in on hottest with "leverage" (simulated)
    hottest = max(momentum_scores, key=momentum_scores.get)
    
    # Apply leverage (dangerous!)
    return {hottest: min(leverage, 3.0)}  # Cap at 3x


# ============================================================================
# DEGEN 2: PENNY STOCK MOMENTUM (Under $20)
# ============================================================================

def penny_stock_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Trade only "penny stocks" (ETFs under $20) with highest volume.
    
    Simulates trading most active list where price < $20
    
    RISKS:
    - Low price ≠ cheap (market cap matters)
    - High vol often = high risk
    - Pump and dumps
    
    POTENTIAL:
    - Explosive moves (100%+ in days)
    - Catch runners
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Filter to "cheap" ETFs (< $20) with high volume
    candidates = {}
    for symbol, df in historical_data.items():
        current_price = df["close"].iloc[-1]
        
        if current_price < 20:  # "Penny stock"
            # Volume momentum (recent vol / avg vol)
            recent_vol = df["volume"].iloc[-5:].mean()
            avg_vol = df["volume"].iloc[-20:].mean()
            
            if avg_vol > 0:
                vol_ratio = recent_vol / avg_vol
                # Price momentum
                price_mom = (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100
                
                # Combined score (volume + momentum)
                score = vol_ratio * (1 + price_mom / 100)
                candidates[symbol] = score
    
    if not candidates:
        return {"SHY": 1.0}
    
    # Top 2 "penny stocks"
    top_2 = sorted(candidates.keys(), key=lambda x: candidates[x], reverse=True)[:2]
    
    weight = 0.5
    weights = {s: weight for s in top_2}
    
    return weights


# ============================================================================
# DEGEN 3: SENTIMENT ANALYSIS (Volume Spikes)
# ============================================================================

def sentiment_analysis_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Trade based on "sentiment" = volume spikes + price action.
    
    Simulates social media buzz / sentiment analysis:
    - High volume = people talking about it
    - Price + volume = bullish sentiment
    - Price - volume = bearish sentiment
    
    RISKS:
    - Volume spike often = top
    - Sentiment lags price
    - False signals everywhere
    
    POTENTIAL:
    - Catch viral moves
    - Ride hype waves
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    sentiment_scores = {}
    
    for symbol, df in historical_data.items():
        if len(df) < 20:
            continue
        
        # Volume spike (vs 20-day avg)
        recent_vol = df["volume"].iloc[-1]
        avg_vol = df["volume"].iloc[-20:].mean()
        
        if avg_vol == 0:
            continue
        
        vol_spike = recent_vol / avg_vol
        
        # Price action (5-day momentum)
        price_mom = (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100 if len(df) >= 6 else 0
        
        # Sentiment = volume spike * price direction
        # High vol + up = bullish buzz
        # High vol + down = bearish buzz (avoid)
        sentiment = vol_spike * (1 + price_mom / 100)
        
        if sentiment > 1.2:  # Above average buzz
            sentiment_scores[symbol] = sentiment
    
    if not sentiment_scores:
        return {"SPY": 1.0}
    
    # Top 3 by sentiment
    top_3 = sorted(sentiment_scores.keys(), key=lambda x: sentiment_scores[x], reverse=True)[:3]
    
    weight = 1.0 / len(top_3)
    weights = {s: weight for s in top_3}
    
    return weights


# ============================================================================
# DEGEN 4: WSB YOLO (Single Position, Meme Stocks)
# ============================================================================

def wsb_yolo_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    r/wallstreetbets style:
    - All-in single position
    - Highest volatility + momentum
    - YOLO or bust
    
    "TSLA 690C 0DTE! 🚀🚀🚀"
    
    RISKS:
    - Everything (literally)
    - Single position = no diversification
    - High vol = high risk
    
    POTENTIAL:
    - 10x gains if right
    - Meme stock runs
    - Diamond hands rewards
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Find "meme stock" proxy: high vol + positive momentum
    meme_scores = {}
    
    for symbol, df in historical_data.items():
        if len(df) < 20:
            continue
        
        # Volatility (more vol = more meme)
        returns = df["close"].pct_change().iloc[-20:]
        vol = returns.std() * np.sqrt(252) * 100
        
        # Momentum (1-week)
        mom = (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100 if len(df) >= 6 else 0
        
        # Meme score = vol * momentum
        # High vol + up = meme status
        if mom > 0:
            meme_score = vol * mom
            meme_scores[symbol] = meme_score
    
    if not meme_scores:
        return {"BITO": 1.0}  # Default to crypto (ultimate meme)
    
    # Pick THE meme (highest score)
    the_meme = max(meme_scores, key=meme_scores.get)
    
    # ALL IN 🚀🚀🚀
    return {the_meme: 1.0}


# ============================================================================
# DEGEN 5: 0DTE OPTIONS PROXY (Ultra Short-Term)
# ============================================================================

def dte_options_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    0DTE (Zero Days To Expiration) options simulation.
    
    We'll simulate by trading daily momentum (buy morning, sell evening).
    In our daily data, we'll use intraday proxy: high volatility assets.
    
    RISKS:
    - Theta decay (time decay)
    - Can go to zero FAST
    - Need to be right TODAY
    
    POTENTIAL:
    - 500%+ gains in hours
    - Scalp market moves
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Select highest intraday volatility (proxy for 0DTE)
    # We'll use: (high - low) / open as volatility proxy
    daily_vol_scores = {}
    
    for symbol, df in historical_data.items():
        if len(df) < 5:
            continue
        
        # Recent intraday volatility
        recent_days = df.iloc[-5:]
        avg_daily_range = ((recent_days["high"] - recent_days["low"]) / recent_days["open"]).mean() * 100
        
        # Momentum (immediate)
        mom = (df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100 if len(df) >= 2 else 0
        
        # Score: vol + momentum
        if mom > 0:
            score = avg_daily_range * (1 + mom / 100)
            daily_vol_scores[symbol] = score
    
    if not daily_vol_scores:
        return {"SPY": 1.0}
    
    # Top 1 (0DTE is single bet)
    top_pick = max(daily_vol_scores, key=daily_vol_scores.get)
    
    # All-in (0DTE style)
    return {top_pick: 1.0}


# ============================================================================
# DEGEN 6: BREAKOUT CHASER
# ============================================================================

def breakout_chaser_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Buy breakouts (new 20-day highs), sell breakdowns.
    
    Classic retail mistake: buy momentum, panic sell dips.
    
    RISKS:
    - Buy tops, sell bottoms
    - Whipsaw central
    - False breakouts
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    breakouts = {}
    
    for symbol, df in historical_data.items():
        if len(df) < 21:
            continue
        
        current_price = df["close"].iloc[-1]
        high_20d = df["high"].iloc[-21:-1].max()  # Previous 20 days
        
        # Breaking out?
        if current_price >= high_20d:
            # How much above?
            breakout_strength = (current_price / high_20d - 1) * 100
            breakouts[symbol] = breakout_strength
    
    if not breakouts:
        return {"SHY": 1.0}
    
    # Top 3 breakouts
    top_3 = sorted(breakouts.keys(), key=lambda x: breakouts[x], reverse=True)[:3]
    
    weight = 1.0 / len(top_3)
    weights = {s: weight for s in top_3}
    
    return weights


# ============================================================================
# DEGEN 7: MAXIMUM RISK (Combine ALL Bad Ideas)
# ============================================================================

def maximum_risk_strategy(data: dict, date: pd.Timestamp) -> dict:
    """
    Combine EVERY bad idea:
    - Leverage (3x)
    - Single position
    - Highest volatility
    - Chase momentum
    - No risk management
    
    This is the "blow up guaranteed" strategy.
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Find most dangerous asset
    danger_scores = {}
    
    for symbol, df in historical_data.items():
        if len(df) < 20:
            continue
        
        # Volatility
        returns = df["close"].pct_change().iloc[-20:]
        vol = returns.std() * np.sqrt(252) * 100
        
        # Momentum (1-week)
        mom = (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100 if len(df) >= 6 else 0
        
        # Danger score = high vol + momentum
        danger = vol * abs(mom)
        danger_scores[symbol] = danger
    
    if not danger_scores:
        return {"BITO": 3.0}  # Max danger default
    
    # Most dangerous
    most_dangerous = max(danger_scores, key=danger_scores.get)
    
    # Max leverage, single position
    return {most_dangerous: 3.0}


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_degen_backtest(
    data: dict,
    strategy_func,
    strategy_name: str,
    **kwargs
) -> dict:
    """Run degen backtest (with account blow-up tracking)."""
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    
    tracker = PortfolioTracker(initial_cash=10000.0)
    daily_values = []
    
    rebalance_count = 0
    day_num = 0
    blown_up = False
    blow_up_date = None
    
    for i, date in enumerate(common_dates):
        current_prices = {symbol: df.loc[date, "close"] for symbol, df in data.items()}
        
        # Daily trading (degen mode!)
        if i >= 5:
            day_num += 1
            
            portfolio_value = tracker.get_portfolio_value(date, current_prices)
            
            # Check if account blown
            if portfolio_value < 100 and not blown_up:
                blown_up = True
                blow_up_date = date
            
            if not blown_up:
                weights = strategy_func(data, date, **kwargs)
                
                if weights:
                    tracker.rebalance(date, current_prices, weights)
                    rebalance_count += 1
        
        daily_value = tracker.get_portfolio_value(date, current_prices)
        daily_values.append({"date": date, "value": max(daily_value, 0)})
    
    equity_df = pd.DataFrame(daily_values).set_index("date")
    returns = equity_df["value"].pct_change().dropna()
    
    cummax = equity_df["value"].cummax()
    drawdown_series = (equity_df["value"] - cummax) / cummax
    max_dd = drawdown_series.min() * 100
    
    total_return = (equity_df["value"].iloc[-1] / equity_df["value"].iloc[0] - 1) * 100
    n_years = len(equity_df) / 252
    
    if equity_df["value"].iloc[-1] > 0:
        cagr = ((equity_df["value"].iloc[-1] / equity_df["value"].iloc[0]) ** (1 / n_years) - 1) * 100
    else:
        cagr = -100.0
    
    mean_ret = returns.mean() * 252
    std_ret = returns.std() * np.sqrt(252)
    sharpe = mean_ret / std_ret if std_ret > 0 else -999
    
    volatility = std_ret * 100
    
    best_day = returns.max() * 100 if len(returns) > 0 else 0
    worst_day = returns.min() * 100 if len(returns) > 0 else 0
    
    return {
        "name": strategy_name,
        "final_value": equity_df["value"].iloc[-1],
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "volatility": volatility,
        "best_day": best_day,
        "worst_day": worst_day,
        "trades": rebalance_count,
        "blown_up": blown_up,
        "blow_up_date": blow_up_date.strftime("%Y-%m-%d") if blow_up_date else None
    }


def main():
    """Test degen strategies."""
    print()
    print("=" * 90)
    print("🤡 DEGEN MODE: MAXIMUM RISK STRATEGIES")
    print("=" * 90)
    print()
    print("⚠️  ⚠️  ⚠️  EXTREME WARNING  ⚠️  ⚠️  ⚠️")
    print()
    print("These strategies are DESIGNED TO LOSE MONEY.")
    print("This is for EDUCATIONAL purposes to show WHY these are bad.")
    print()
    print("DO NOT TRY WITH REAL MONEY!")
    print("You WILL lose everything.")
    print("Your spouse WILL leave you.")
    print("You WILL end up behind Wendy's.")
    print()
    print("Proceed at your own risk...")
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    strategies = [
        ("Leveraged Options (3x)", leveraged_options_strategy, {"leverage": 3.0}),
        ("Penny Stock Momentum", penny_stock_strategy, {}),
        ("Sentiment Analysis", sentiment_analysis_strategy, {}),
        ("WSB YOLO", wsb_yolo_strategy, {}),
        ("0DTE Options Proxy", dte_options_strategy, {}),
        ("Breakout Chaser", breakout_chaser_strategy, {}),
        ("Maximum Risk", maximum_risk_strategy, {}),
    ]
    
    results = []
    
    for name, func, kwargs in strategies:
        print(f"🎰 Running: {name}...", end=" ", flush=True)
        result = run_degen_backtest(data, func, name, **kwargs)
        results.append(result)
        
        if result["blown_up"]:
            print(f"💀 ACCOUNT BLOWN on {result['blow_up_date']}")
        else:
            print(f"✅ Survived! CAGR: {result['cagr']:>7.2f}%")
    
    # SPY
    spy_df = data["SPY"]
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    common_dates = [d for d in all_dates if all(d in df.index for df in data.values())]
    spy_dates = pd.DatetimeIndex([d for d in common_dates if d >= common_dates[5]])
    
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
    print("=" * 110)
    print("🤡 DEGEN MODE RESULTS")
    print("=" * 110)
    print()
    
    print(f"{'Strategy':<25} {'Final $':>10} {'CAGR':>8} {'Sharpe':>8} {'Max DD':>10} {'Best Day':>10} {'Worst Day':>10} {'Blown?':>8}")
    print("-" * 110)
    
    for result in results:
        blown_str = "💀 YES" if result["blown_up"] else "✅ NO"
        print(f"{result['name']:<25} ${result['final_value']:>9,.0f} {result['cagr']:>7.2f}% {result['sharpe']:>8.2f} {result['max_dd']:>9.2f}% {result['best_day']:>9.1f}% {result['worst_day']:>9.1f}% {blown_str:>8}")
    
    print(f"{'SPY (buy & hold)':<25} ${spy_final:>9,.0f} {spy_cagr:>7.2f}% {spy_sharpe:>8.2f} {spy_dd:>9.2f}% {spy_returns.max()*100:>9.1f}% {spy_returns.min()*100:>9.1f}% {'✅ NO':>8}")
    
    print()
    print("=" * 110)
    print("🎯 DEGEN ANALYSIS")
    print("=" * 110)
    print()
    
    # Stats
    blown_count = sum(1 for r in results if r["blown_up"])
    survivors = [r for r in results if not r["blown_up"]]
    
    print(f"💀 Accounts Blown: {blown_count}/{len(results)}")
    print(f"✅ Survivors: {len(survivors)}/{len(results)}")
    print()
    
    if survivors:
        best = max(survivors, key=lambda x: x["cagr"])
        print(f"🏆 Best Survivor: {best['name']}")
        print(f"   CAGR: {best['cagr']:.2f}%")
        print(f"   vs SPY: {best['cagr'] - spy_cagr:+.2f}%")
        print()
    
    worst = min(results, key=lambda x: x["final_value"])
    print(f"💀 Worst Loss: {worst['name']}")
    print(f"   Final: ${worst['final_value']:,.0f}")
    print(f"   Lost: ${10000 - worst['final_value']:,.0f}")
    print()
    
    # Save
    output_dir = Path("artifacts/degen_mode")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "strategies": {r["name"]: {
            "cagr": r["cagr"],
            "sharpe": r["sharpe"],
            "max_dd": r["max_dd"],
            "final_value": r["final_value"],
            "blown_up": r["blown_up"],
            "vs_spy": r["cagr"] - spy_cagr
        } for r in results}
    }
    
    with open(output_dir / "degen_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 110)
    print("⚠️  FINAL WARNING:")
    print("   If you learned anything from this, it should be:")
    print("   THESE STRATEGIES ARE TERRIBLE!")
    print("   Stick to boring SPY.")
    print("   Your future self will thank you.")
    print("=" * 110)
    print()


if __name__ == "__main__":
    main()

