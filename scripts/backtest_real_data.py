"""
REAL BACKTEST using actual market data from Yahoo Finance

This is THE MOMENT OF TRUTH - testing our strategy on real historical prices.
No synthetic data, no cheating, just honest results.
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config


class PortfolioTracker:
    """Track portfolio with full accounting."""
    
    def __init__(self, initial_cash: float):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}
        self.history = []
        
    def get_portfolio_value(self, date: pd.Timestamp, prices: dict) -> float:
        """Calculate portfolio value."""
        value = self.cash
        for symbol, shares in self.positions.items():
            if symbol in prices:
                value += shares * prices[symbol]
        return value
    
    def rebalance(self, date: pd.Timestamp, prices: dict, target_weights: dict, 
                  commission_per_share: float = 0.0035, slippage_bps: float = 3.0):
        """Execute rebalance with realistic costs."""
        portfolio_value = self.get_portfolio_value(date, prices)
        
        # Calculate target positions
        target_positions = {}
        for symbol, weight in target_weights.items():
            if symbol in prices:
                target_value = portfolio_value * weight
                target_shares = target_value / prices[symbol]
                target_positions[symbol] = target_shares
        
        # Execute trades
        trades = []
        total_commission = 0
        total_slippage = 0
        
        for symbol, target_shares in target_positions.items():
            current_shares = self.positions.get(symbol, 0.0)
            delta_shares = target_shares - current_shares
            
            if abs(delta_shares) > 0.001:
                price = prices[symbol]
                trade_value = delta_shares * price
                
                # Commission (min $0.35 per order)
                commission = max(abs(delta_shares) * commission_per_share, 0.35)
                
                # Slippage (bps of trade value)
                slippage = abs(trade_value) * (slippage_bps / 10000)
                
                total_commission += commission
                total_slippage += slippage
                
                trades.append({
                    "symbol": symbol,
                    "shares": delta_shares,
                    "price": price,
                    "value": trade_value,
                    "commission": commission,
                    "slippage": slippage
                })
                
                self.positions[symbol] = target_shares
                self.cash -= trade_value + commission + slippage
        
        # Close positions not in target
        for symbol in list(self.positions.keys()):
            if symbol not in target_positions:
                shares = self.positions[symbol]
                price = prices.get(symbol, 0)
                trade_value = shares * price
                commission = max(abs(shares) * commission_per_share, 0.35)
                slippage = abs(trade_value) * (slippage_bps / 10000)
                
                total_commission += commission
                total_slippage += slippage
                
                trades.append({
                    "symbol": symbol,
                    "shares": -shares,
                    "price": price,
                    "value": trade_value,
                    "commission": commission,
                    "slippage": slippage
                })
                
                self.cash += trade_value - commission - slippage
                del self.positions[symbol]
        
        return trades, total_commission, total_slippage


def load_real_data(data_dir: Path) -> dict:
    """Load real historical data from Parquet files."""
    print("📂 Loading real market data...")
    
    data = {}
    for parquet_file in sorted(data_dir.glob("*.parquet")):
        symbol = parquet_file.stem
        df = pd.read_parquet(parquet_file)
        data[symbol] = df
        print(f"  ✓ {symbol:6s} {len(df):>5} bars")
    
    print()
    return data


def calculate_momentum_score(df: pd.DataFrame, lookback: int = 20) -> float:
    """Calculate momentum (NO LOOK-AHEAD!)."""
    if len(df) < lookback + 1:
        return 0.0
    return (df["close"].iloc[-1] / df["close"].iloc[-lookback-1] - 1) * 100


def calculate_inverse_vol_weights(symbols: list[str], data: dict, lookback: int = 20, max_weight: float = 0.30) -> dict:
    """Calculate inverse-vol weights (NO LOOK-AHEAD!)."""
    vols = {}
    for symbol in symbols:
        df = data[symbol]
        if len(df) < lookback:
            continue
        returns = df["close"].pct_change().iloc[-lookback:]
        vols[symbol] = returns.std()
    
    inv_vols = {s: 1/v if v > 0 else 0 for s, v in vols.items()}
    total = sum(inv_vols.values())
    
    if total == 0:
        return {s: 1/len(symbols) for s in symbols}
    
    weights = {}
    for s in symbols:
        weight = inv_vols[s] / total
        weights[s] = min(weight, max_weight)
    
    total_weight = sum(weights.values())
    weights = {s: w / total_weight * 0.95 for s, w in weights.items()}
    
    return weights


def run_real_backtest(data: dict, config) -> dict:
    """Run backtest on REAL market data."""
    print("=" * 80)
    print("🔬 REAL BACKTEST: ACTUAL MARKET DATA")
    print("=" * 80)
    print()
    print("This is the REAL DEAL:")
    print("  ✓ Real market prices from Yahoo Finance")
    print("  ✓ Real volatility, crashes, regime changes")
    print("  ✓ Real commissions ($0.35 min per order)")
    print("  ✓ Real slippage (3 bps per trade)")
    print("  ✓ NO look-ahead bias")
    print("  ✓ NO synthetic data")
    print()
    
    # Find common date range
    all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))
    
    # Filter to dates where ALL symbols have data
    common_dates = []
    for date in all_dates:
        if all(date in df.index for df in data.values()):
            common_dates.append(date)
    
    tracker = PortfolioTracker(initial_cash=10000.0)
    weekly_snapshots = []
    daily_values = []
    
    print(f"Period: {common_dates[0].date()} to {common_dates[-1].date()}")
    print(f"Common trading days: {len(common_dates)}")
    print(f"Initial capital: ${tracker.initial_cash:,.2f}")
    print()
    
    week_num = 0
    total_commission = 0
    total_slippage = 0
    
    for i, date in enumerate(common_dates):
        # Get current prices
        current_prices = {symbol: df.loc[date, "close"] for symbol, df in data.items() if date in df.index}
        
        # Rebalance weekly (after 50 days history)
        if i % 5 == 0 and i >= 50:
            week_num += 1
            
            # Historical data only (NO LOOK-AHEAD!)
            historical_data = {}
            for symbol, df in data.items():
                if date in df.index:
                    idx = df.index.get_loc(date)
                    historical_data[symbol] = df.iloc[:idx+1].copy()
            
            # Calculate scores
            scores = {}
            for symbol, df in historical_data.items():
                scores[symbol] = calculate_momentum_score(df, lookback=20)
            
            # Select top N
            top_n = config.selection.top_n
            selected = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_n]
            
            # Calculate weights
            weights = calculate_inverse_vol_weights(selected, historical_data, lookback=20, max_weight=config.weights.max_weight_per_asset)
            
            # Execute rebalance
            trades, commission, slippage = tracker.rebalance(date, current_prices, weights)
            
            total_commission += commission
            total_slippage += slippage
            
            portfolio_value = tracker.get_portfolio_value(date, current_prices)
            
            # Weekly snapshot
            position_values = {}
            for symbol, shares in tracker.positions.items():
                position_values[symbol] = shares * current_prices[symbol]
            
            weekly_snapshots.append({
                "week": week_num,
                "date": date,
                "cash": tracker.cash,
                "positions": tracker.positions.copy(),
                "position_values": position_values,
                "weights": weights,
                "portfolio_value": portfolio_value,
                "trades": len(trades),
                "commission": commission,
                "slippage": slippage,
                "selected": selected,
                "scores": {s: scores[s] for s in selected}
            })
            
            if week_num % 10 == 0 or week_num <= 5:
                print(f"Week {week_num:3d} | {date.date()} | ${portfolio_value:>10,.2f} | Cash: ${tracker.cash:>9,.2f} | Positions: {len(tracker.positions)}")
        
        # Daily value
        daily_value = tracker.get_portfolio_value(date, current_prices)
        daily_values.append({"date": date, "value": daily_value})
    
    # Calculate metrics
    equity_df = pd.DataFrame(daily_values).set_index("date")
    returns = equity_df["value"].pct_change().dropna()
    
    # PROPER DRAWDOWN
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
    win_rate = (returns > 0).sum() / len(returns) * 100
    
    print()
    print("=" * 80)
    print("📊 REAL BACKTEST RESULTS")
    print("=" * 80)
    print()
    print(f"Initial value:     ${equity_df['value'].iloc[0]:>10,.2f}")
    print(f"Final value:       ${equity_df['value'].iloc[-1]:>10,.2f}")
    print(f"Final cash:        ${tracker.cash:>10,.2f}")
    print()
    print(f"Total return:      {total_return:>10.2f}%")
    print(f"CAGR:              {cagr:>10.2f}%")
    print()
    print(f"Sharpe ratio:      {sharpe:>10.2f}")
    print(f"Max drawdown:      {max_dd:>10.2f}%")
    print(f"  Date:            {max_dd_date.date()}")
    print(f"Volatility:        {volatility:>10.2f}%")
    print(f"Win rate:          {win_rate:>10.1f}%")
    print()
    print(f"Trading costs:")
    print(f"  Commissions:     ${total_commission:>10,.2f}")
    print(f"  Slippage:        ${total_slippage:>10,.2f}")
    print(f"  Total costs:     ${total_commission + total_slippage:>10,.2f}")
    print()
    
    return {
        "equity_curve": equity_df,
        "weekly_snapshots": weekly_snapshots,
        "drawdown_series": drawdown_series,
        "metrics": {
            "initial_value": float(equity_df["value"].iloc[0]),
            "final_value": float(equity_df["value"].iloc[-1]),
            "final_cash": tracker.cash,
            "total_return": total_return,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "max_dd_date": max_dd_date.isoformat(),
            "volatility": volatility,
            "win_rate": win_rate,
            "n_weeks": len(weekly_snapshots),
            "n_trading_days": len(equity_df),
            "total_commission": total_commission,
            "total_slippage": total_slippage,
            "total_costs": total_commission + total_slippage
        }
    }


def save_results(results: dict, output_dir: Path) -> None:
    """Save backtest results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "real_backtest_metrics.json", "w") as f:
        json.dump(results["metrics"], f, indent=2)
    
    results["equity_curve"].to_csv(output_dir / "real_equity_curve.csv")
    results["drawdown_series"].to_csv(output_dir / "real_drawdown.csv")
    
    print(f"📁 Results saved to: {output_dir}/")
    print()


def compare_to_benchmarks(results: dict, data: dict) -> None:
    """Compare to SPY benchmark."""
    print("=" * 80)
    print("📊 COMPARISON TO BENCHMARKS")
    print("=" * 80)
    print()
    
    # Get SPY for comparison
    spy = data.get("SPY")
    if spy is None:
        print("⚠️ SPY data not available for comparison")
        return
    
    # Calculate SPY returns
    spy_dates = results["equity_curve"].index
    spy_prices = spy.loc[spy_dates, "close"]
    spy_return = (spy_prices.iloc[-1] / spy_prices.iloc[0] - 1) * 100
    
    n_years = len(spy_prices) / 252
    spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / n_years) - 1) * 100
    
    spy_returns = spy_prices.pct_change().dropna()
    spy_vol = spy_returns.std() * np.sqrt(252) * 100
    spy_sharpe = (spy_cagr / spy_vol) if spy_vol > 0 else 0
    
    # SPY drawdown
    spy_cummax = spy_prices.cummax()
    spy_dd = ((spy_prices - spy_cummax) / spy_cummax).min() * 100
    
    print(f"{'Metric':<20} {'Your Strategy':>15} {'SPY':>15} {'Difference':>15}")
    print("-" * 80)
    
    metrics = [
        ("Total Return", results["metrics"]["total_return"], spy_return, "%"),
        ("CAGR", results["metrics"]["cagr"], spy_cagr, "%"),
        ("Sharpe Ratio", results["metrics"]["sharpe"], spy_sharpe, ""),
        ("Max Drawdown", results["metrics"]["max_dd"], spy_dd, "%"),
        ("Volatility", results["metrics"]["volatility"], spy_vol, "%"),
    ]
    
    for name, strat, bench, unit in metrics:
        diff = strat - bench
        diff_str = f"{diff:>+6.2f}{unit}"
        
        if name in ["Total Return", "CAGR", "Sharpe Ratio"]:
            emoji = "🟢" if diff > 0 else "🔴"
        elif name in ["Max Drawdown", "Volatility"]:
            emoji = "🟢" if diff < 0 else "🔴"  # Lower is better
        else:
            emoji = "🟡"
        
        print(f"{name:<20} {strat:>14.2f}{unit} {bench:>14.2f}{unit} {emoji} {diff_str:>14}")
    
    print()


def main():
    """Run real backtest."""
    config = load_config()
    
    print()
    print("=" * 80)
    print("🔥 THE MOMENT OF TRUTH: REAL BACKTEST")
    print("=" * 80)
    print()
    
    # Load real data
    data_dir = Path("data/real_historical")
    if not data_dir.exists():
        print("❌ No real data found!")
        print("   Run: docker compose run --rm app poetry run python3 scripts/download_real_data.py")
        return
    
    data = load_real_data(data_dir)
    
    if not data:
        print("❌ No data loaded")
        return
    
    # Run backtest
    results = run_real_backtest(data, config)
    
    # Save results
    output_dir = Path("artifacts/backtest_real")
    save_results(results, output_dir)
    
    # Compare to benchmarks
    compare_to_benchmarks(results, data)
    
    print("=" * 80)
    print("✅ REAL BACKTEST COMPLETE")
    print("=" * 80)
    print()
    print("🎯 THIS IS YOUR STRATEGY'S ACTUAL PERFORMANCE!")
    print()
    print("No synthetic data, no cheating, no curve-fitting.")
    print("These results show what REALLY happened.")
    print()


if __name__ == "__main__":
    main()

