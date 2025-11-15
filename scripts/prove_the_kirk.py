"""
PROVE THE KIRK: Show every single trade and calculation
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path("data/real_historical")
OUTPUT_DIR = Path("artifacts/the_kirk_proof")
INITIAL_CAPITAL = 10000.0
COMMISSION = 0.35
SLIPPAGE_BPS = 3


def load_data():
    data = {}
    for f in sorted(DATA_DIR.glob("*.parquet")):
        df = pd.read_parquet(f)
        data[f.stem] = df
    return data


def sentiment_strategy(data, date):
    """The Kirk: Volume spike + momentum"""
    scores = {}
    
    for symbol, df in data.items():
        if date not in df.index:
            continue
        
        hist = df[df.index <= date]
        if len(hist) < 21:
            continue
        
        # Volume spike
        recent_vol = hist["volume"].iloc[-1]
        avg_vol = hist["volume"].iloc[-20:].mean()
        vol_spike = recent_vol / avg_vol if avg_vol > 0 else 1.0
        
        # 5-day momentum
        if len(hist) < 6:
            continue
        mom = (hist["close"].iloc[-1] / hist["close"].iloc[-6] - 1) * 100
        
        # Sentiment score
        sentiment = vol_spike * (1 + mom / 100)
        
        if sentiment > 1.2:  # Threshold
            scores[symbol] = sentiment
    
    # Select top 3
    if not scores:
        return {"SPY": 1.0}
    
    top3 = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:3]
    return {s: 1/len(top3) for s in top3}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*100)
    print("🔬 THE KIRK: COMPLETE PROOF WITH EVERY TRADE")
    print("="*100)
    
    data = load_data()
    
    # Get common dates
    common_start = max(df.index.min() for df in data.values())
    common_end = min(df.index.max() for df in data.values())
    all_dates = pd.bdate_range(common_start, common_end)
    
    # Skip first 21 days for indicators
    trading_dates = all_dates[21:]
    
    print(f"\nPeriod: {trading_dates[0].date()} to {trading_dates[-1].date()}")
    print(f"Trading days: {len(trading_dates)}")
    print(f"Initial capital: ${INITIAL_CAPITAL:,.2f}\n")
    
    cash = INITIAL_CAPITAL
    positions = {}
    equity_curve = []
    trades_log = []
    
    last_holdings = set()
    rebalance_count = 0
    
    for i, date in enumerate(trading_dates):
        # Get prices
        prices = {}
        for symbol, df in data.items():
            if date in df.index:
                prices[symbol] = df.loc[date, "close"]
        
        # Portfolio value
        portfolio_value = cash
        for symbol, shares in positions.items():
            if symbol in prices:
                portfolio_value += shares * prices[symbol]
        
        equity_curve.append({"date": date, "value": portfolio_value})
        
        # Rebalance weekly (every 5 days)
        if i % 5 == 0:
            weights = sentiment_strategy(data, date)
            current_holdings = set(weights.keys())
            
            # Only trade if holdings changed
            if current_holdings != last_holdings:
                rebalance_count += 1
                print(f"\n{'='*100}")
                print(f"REBALANCE #{rebalance_count} - {date.date()} (Week {i//5})")
                print(f"Portfolio Value: ${portfolio_value:,.2f}")
                print(f"{'='*100}")
                
                # Sell old positions
                for symbol in list(positions.keys()):
                    if symbol not in weights:
                        shares = positions[symbol]
                        price = prices.get(symbol, 0)
                        if price > 0:
                            proceeds = shares * price * (1 - SLIPPAGE_BPS/10000) - COMMISSION
                            cash += proceeds
                            print(f"  SELL {shares:>8.4f} shares of {symbol:<5} @ ${price:>7.2f} = ${proceeds:>9.2f}")
                            trades_log.append({
                                "date": str(date.date()),
                                "action": "SELL",
                                "symbol": symbol,
                                "shares": shares,
                                "price": price,
                                "value": proceeds
                            })
                            del positions[symbol]
                
                # Buy new positions
                for symbol, weight in weights.items():
                    target_value = portfolio_value * weight
                    price = prices.get(symbol, 0)
                    if price <= 0:
                        continue
                    
                    target_shares = target_value / price
                    current_shares = positions.get(symbol, 0)
                    delta_shares = target_shares - current_shares
                    
                    if abs(delta_shares * price) > COMMISSION * 2:
                        cost = delta_shares * price * (1 + SLIPPAGE_BPS/10000) + COMMISSION
                        if cash >= cost:
                            cash -= cost
                            positions[symbol] = target_shares
                            print(f"  BUY  {delta_shares:>8.4f} shares of {symbol:<5} @ ${price:>7.2f} = ${cost:>9.2f}")
                            trades_log.append({
                                "date": str(date.date()),
                                "action": "BUY",
                                "symbol": symbol,
                                "shares": delta_shares,
                                "price": price,
                                "value": cost
                            })
                
                print(f"\nNew Holdings: {', '.join(sorted(weights.keys()))}")
                print(f"Cash Remaining: ${cash:,.2f}")
                
                last_holdings = current_holdings
    
    # Final metrics
    equity_df = pd.DataFrame(equity_curve).set_index("date")
    final_value = equity_df["value"].iloc[-1]
    
    years = (trading_dates[-1] - trading_dates[0]).days / 365.25
    cagr = (final_value / INITIAL_CAPITAL)**(1/years) - 1
    
    returns = equity_df["value"].pct_change().dropna()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
    
    peak = equity_df["value"].expanding().max()
    drawdown = (equity_df["value"] - peak) / peak
    max_dd = drawdown.min()
    
    print("\n" + "="*100)
    print("📊 FINAL RESULTS")
    print("="*100)
    print(f"\nInitial Capital:    ${INITIAL_CAPITAL:,.2f}")
    print(f"Final Value:        ${final_value:,.2f}")
    print(f"Total Return:       {(final_value/INITIAL_CAPITAL - 1)*100:.2f}%")
    print(f"\nCAGR:               {cagr*100:.2f}%")
    print(f"Sharpe Ratio:       {sharpe:.2f}")
    print(f"Max Drawdown:       {max_dd*100:.2f}%")
    print(f"\nTotal Rebalances:   {rebalance_count}")
    print(f"Total Trades:       {len(trades_log)}")
    print(f"Avg Trades/Year:    {len(trades_log)/years:.0f}")
    
    # Save everything
    equity_df.to_csv(OUTPUT_DIR / "equity_curve.csv")
    
    trades_df = pd.DataFrame(trades_log)
    trades_df.to_csv(OUTPUT_DIR / "all_trades.csv", index=False)
    
    summary = {
        "initial_capital": INITIAL_CAPITAL,
        "final_value": float(final_value),
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "max_dd": float(max_dd),
        "total_trades": len(trades_log),
        "rebalances": rebalance_count
    }
    
    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📁 All results saved to: {OUTPUT_DIR}/")
    print("   - equity_curve.csv (daily portfolio value)")
    print("   - all_trades.csv (every single trade)")
    print("   - summary.json (final metrics)")
    print("\n" + "="*100)
    print("✅ PROOF COMPLETE - CHECK THE FILES!")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
