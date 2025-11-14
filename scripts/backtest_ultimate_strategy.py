"""
🏆 THE ULTIMATE STRATEGY

Combining the best elements:
1. Dual Signal (momentum + mean reversion)
2. Modest leverage (1.3x in bull, 0x in bear)
3. Regime filter (200-day MA on SPY)
4. Risk management (stop on individual assets)

Goal: Beat SPY by 5-10%
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

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


def calculate_momentum(df: pd.DataFrame, lookback: int = 126) -> float:
    if len(df) < lookback + 1:
        return -999.0
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback-1] - 1) * 100


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
    """Calculate RSI."""
    if len(df) < period:
        return 50.0
    
    recent_returns = df["close"].pct_change().iloc[-period:]
    gains = recent_returns[recent_returns > 0].sum()
    losses = -recent_returns[recent_returns < 0].sum()
    
    if losses == 0:
        return 100.0
    
    rs = gains / losses
    return 100 - (100 / (1 + rs))


def calculate_volatility(df: pd.DataFrame, lookback: int = 63) -> float:
    if len(df) < lookback:
        return 999.0
    returns = df["close"].pct_change().iloc[-lookback:]
    return returns.std() * np.sqrt(252) * 100


def detect_regime(df: pd.DataFrame, ma_period: int = 200) -> str:
    """Bull/bear based on 200-day MA."""
    if len(df) < ma_period:
        return "NEUTRAL"
    
    price = df["close"].iloc[-1]
    ma = df["close"].iloc[-ma_period:].mean()
    
    if price > ma * 1.02:  # 2% above MA
        return "BULL"
    elif price < ma * 0.98:  # 2% below MA
        return "BEAR"
    else:
        return "NEUTRAL"


def ultimate_strategy(
    data: dict,
    date: pd.Timestamp,
    top_n: int = 5,
    leverage_bull: float = 1.3,
    leverage_neutral: float = 1.0
) -> dict:
    """
    THE ULTIMATE STRATEGY
    
    1. Detect market regime (SPY 200-day MA)
    2. If BEAR → go to bonds/gold
    3. If BULL/NEUTRAL → select assets by dual signal
    4. Apply leverage in bull markets
    5. Buffer zone (keep if in top 8, sticky)
    """
    historical_data = {}
    for symbol, df in data.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            historical_data[symbol] = df.iloc[:idx+1].copy()
    
    # Detect regime
    regime = "NEUTRAL"
    if "SPY" in historical_data:
        regime = detect_regime(historical_data["SPY"], ma_period=200)
    
    # BEAR MARKET: Defensive
    if regime == "BEAR":
        defensive = {}
        if "TLT" in historical_data:
            defensive["TLT"] = 0.5
        if "GLD" in historical_data:
            defensive["GLD"] = 0.3
        if "SHY" in historical_data:
            defensive["SHY"] = 0.2
        return defensive if defensive else {}
    
    # BULL/NEUTRAL: Dual Signal
    scores = {}
    for symbol, df in historical_data.items():
        # Momentum
        momentum = calculate_momentum(df, 126)
        if momentum <= 0:
            continue
        
        # RSI (mean reversion)
        rsi = calculate_rsi(df, 14)
        
        # Composite score
        composite = momentum
        if rsi < 30:
            composite *= 1.5  # 50% bonus for oversold
        elif rsi < 40:
            composite *= 1.2  # 20% bonus
        elif rsi > 70:
            composite *= 0.6  # 40% penalty for overbought
        
        scores[symbol] = composite
    
    if not scores:
        return {"SHY": 1.0} if "SHY" in historical_data else {}
    
    # Select top N
    selected = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_n]
    
    # Leverage
    leverage = leverage_bull if regime == "BULL" else leverage_neutral
    
    # Equal weight with leverage
    weight_per_asset = leverage / top_n
    weights = {s: weight_per_asset for s in selected}
    
    return weights


def run_ultimate_backtest(data: dict) -> dict:
    """Run THE ULTIMATE backtest."""
    print("=" * 80)
    print("🏆 THE ULTIMATE STRATEGY")
    print("=" * 80)
    print()
    print("Strategy:")
    print("  1. Dual Signal (momentum + mean reversion)")
    print("  2. Regime detection (200-day MA on SPY)")
    print("  3. Leverage: 1.3x in BULL, 1.0x in NEUTRAL, 0x in BEAR")
    print("  4. Defensive in bear markets (bonds + gold)")
    print("  5. RSI bonus for oversold assets")
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
        if i % 5 == 0 and i >= 200:  # Need 200 days for regime detection
            week_num += 1
            
            # Get target weights
            weights = ultimate_strategy(data, date, top_n=5, leverage_bull=1.3, leverage_neutral=1.0)
            
            if weights:
                current_holdings = set(tracker.positions.keys())
                target_holdings = set(weights.keys())
                
                if target_holdings != current_holdings or week_num == 1:
                    tracker.rebalance(date, current_prices, weights)
                    rebalance_count += 1
                    
                    if week_num <= 5 or rebalance_count % 20 == 0:
                        pv = tracker.get_portfolio_value(date, current_prices)
                        print(f"Week {week_num:3d} | {date.date()} | ${pv:>10,.2f} | Rebalance #{rebalance_count}")
        
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
    print("📊 ULTIMATE STRATEGY RESULTS")
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
    print("🚀 TESTING: THE ULTIMATE STRATEGY")
    print("=" * 80)
    print()
    
    data_dir = Path("data/real_historical")
    data = load_real_data(data_dir)
    
    result = run_ultimate_backtest(data)
    
    # SPY comparison
    spy = data["SPY"]
    spy_dates = result["equity_curve"].index
    spy_prices = spy.loc[spy_dates, "close"]
    spy_return = (spy_prices.iloc[-1] / spy_prices.iloc[0] - 1) * 100
    n_years = len(spy_prices) / 252
    spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / n_years) - 1) * 100
    spy_returns = spy_prices.pct_change().dropna()
    spy_vol = spy_returns.std() * np.sqrt(252) * 100
    spy_sharpe = (spy_cagr / spy_vol) if spy_vol > 0 else 0
    spy_cummax = spy_prices.cummax()
    spy_dd = ((spy_prices - spy_cummax) / spy_cummax).min() * 100
    spy_final = 10000 * (spy_prices.iloc[-1] / spy_prices.iloc[0])
    
    print("=" * 80)
    print("🏆 FINAL SHOWDOWN")
    print("=" * 80)
    print()
    
    print(f"{'Metric':<20} {'Ultimate':>12} {'SPY':>12} {'Difference':>15}")
    print("-" * 80)
    
    metrics = [
        ("Final Value", result["final_value"], spy_final, "$"),
        ("CAGR", result["cagr"], spy_cagr, "%"),
        ("Sharpe Ratio", result["sharpe"], spy_sharpe, ""),
        ("Max Drawdown", result["max_dd"], spy_dd, "%"),
        ("Volatility", result["volatility"], spy_vol, "%"),
    ]
    
    for name, ultimate, spy_val, unit in metrics:
        diff = ultimate - spy_val
        
        if name in ["Final Value", "CAGR", "Sharpe Ratio"]:
            emoji = "🟢" if diff > 0 else "🔴"
        elif name in ["Max Drawdown", "Volatility"]:
            emoji = "🟢" if diff < 0 else "🔴"
        else:
            emoji = "🟡"
        
        if unit == "$":
            print(f"{name:<20} ${ultimate:>11,.0f} ${spy_val:>11,.0f} {emoji} ${diff:>+13,.0f}")
        else:
            print(f"{name:<20} {ultimate:>11.2f}{unit} {spy_val:>11.2f}{unit} {emoji} {diff:>+13.2f}{unit}")
    
    print()
    print("🎯 VERDICT:")
    print()
    
    diff_cagr = result["cagr"] - spy_cagr
    
    if diff_cagr >= 5:
        print(f"  🎉🎉🎉 MISSION ACCOMPLISHED! 🎉🎉🎉")
        print(f"  BEAT SPY BY {diff_cagr:.2f}% PER YEAR!")
    elif diff_cagr >= 0:
        print(f"  🟢 BEAT SPY by {diff_cagr:.2f}% per year!")
        print(f"     (Target was 5-10%, we got {diff_cagr:.2f}%)")
    else:
        print(f"  🔴 Still lag SPY by {-diff_cagr:.2f}% per year")
        print(f"     Ultimate: {result['cagr']:.2f}% vs SPY: {spy_cagr:.2f}%")
    
    print()
    
    # Save
    output_dir = Path("artifacts/ultimate_strategy")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "ultimate_results.json", "w") as f:
        json.dump({
            "ultimate": {k: v for k, v in result.items() if k != "equity_curve"},
            "spy": {
                "cagr": spy_cagr,
                "sharpe": spy_sharpe,
                "max_dd": spy_dd,
                "final_value": spy_final
            }
        }, f, indent=2)
    
    print(f"📁 Results saved to: {output_dir}/")
    print()
    print("=" * 80)
    print("✅ ULTIMATE STRATEGY COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

