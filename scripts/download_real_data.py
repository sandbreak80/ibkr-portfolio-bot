"""
Download REAL historical data from Yahoo Finance

Downloads 5 years of daily OHLCV data for all assets in our universe.
Saves to data/real_historical/ as Parquet files for fast loading.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf


def download_real_data(symbols: list[str], start_date: str, end_date: str, output_dir: Path) -> dict:
    """
    Download real historical data from Yahoo Finance.
    
    Args:
        symbols: List of ticker symbols
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_dir: Directory to save Parquet files
        
    Returns:
        Dict mapping symbol -> DataFrame
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("📥 DOWNLOADING REAL HISTORICAL DATA")
    print("=" * 80)
    print()
    print(f"Source:       Yahoo Finance (FREE!)")
    print(f"Period:       {start_date} to {end_date}")
    print(f"Timeframe:    Daily (1D candles)")
    print(f"Assets:       {len(symbols)} symbols")
    print(f"Output:       {output_dir}/")
    print()
    
    data = {}
    failed = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i:2d}/{len(symbols)}] Downloading {symbol:6s}...", end=" ", flush=True)
        
        try:
            # Download from Yahoo Finance
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if df.empty:
                print(f"❌ NO DATA")
                failed.append(symbol)
                continue
            
            # Standardize column names
            df = df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            
            # Keep only OHLCV
            df = df[["open", "high", "low", "close", "volume"]]
            
            # Ensure index is datetime
            df.index = pd.to_datetime(df.index)
            df.index.name = "date"
            
            # Save as Parquet (fast, compressed)
            output_path = output_dir / f"{symbol}.parquet"
            df.to_parquet(output_path)
            
            data[symbol] = df
            
            print(f"✅ {len(df):>5} bars ({df.index[0].date()} to {df.index[-1].date()})")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed.append(symbol)
    
    print()
    print("=" * 80)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 80)
    print()
    print(f"Successful:  {len(data)}/{len(symbols)} symbols")
    print(f"Failed:      {len(failed)} symbols")
    
    if failed:
        print()
        print(f"Failed symbols: {', '.join(failed)}")
        print()
        print("Common reasons:")
        print("  • Symbol not found (check ticker)")
        print("  • Insufficient history (new ETF)")
        print("  • Network error (try again)")
    
    print()
    print(f"Data saved to: {output_dir}/")
    print()
    
    # Data quality report
    if data:
        print("=" * 80)
        print("📋 DATA QUALITY REPORT")
        print("=" * 80)
        print()
        
        # Find common date range
        all_dates = set()
        for df in data.values():
            all_dates.update(df.index)
        
        min_date = min(all_dates)
        max_date = max(all_dates)
        
        print(f"Date range:    {min_date.date()} to {max_date.date()}")
        print(f"Trading days:  {len(all_dates)}")
        print()
        
        # Check for missing data
        print("Coverage by symbol:")
        for symbol, df in sorted(data.items()):
            coverage = len(df) / len(all_dates) * 100
            bars = len(df)
            
            if coverage >= 95:
                status = "✅"
            elif coverage >= 80:
                status = "🟡"
            else:
                status = "⚠️"
            
            print(f"  {status} {symbol:6s} {bars:>5} bars ({coverage:>5.1f}% coverage)")
        
        print()
        
        # Check for data quality issues
        print("Data quality checks:")
        issues = []
        
        for symbol, df in data.items():
            # Check for NaNs
            if df.isnull().any().any():
                issues.append(f"{symbol}: Contains NaN values")
            
            # Check for negative prices
            if (df[["open", "high", "low", "close"]] < 0).any().any():
                issues.append(f"{symbol}: Contains negative prices")
            
            # Check for zero volume
            if (df["volume"] == 0).sum() > 0:
                zero_vol_count = (df["volume"] == 0).sum()
                if zero_vol_count > len(df) * 0.1:  # More than 10%
                    issues.append(f"{symbol}: {zero_vol_count} days with zero volume")
            
            # Check OHLC relationships
            if (df["high"] < df["low"]).any():
                issues.append(f"{symbol}: High < Low (data error)")
            if (df["high"] < df["close"]).any() or (df["high"] < df["open"]).any():
                issues.append(f"{symbol}: High < Close/Open")
            if (df["low"] > df["close"]).any() or (df["low"] > df["open"]).any():
                issues.append(f"{symbol}: Low > Close/Open")
        
        if issues:
            print()
            print("⚠️ Issues found:")
            for issue in issues[:10]:  # Show first 10
                print(f"  • {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")
        else:
            print("  ✅ All checks passed!")
        
        print()
    
    return data


def validate_for_backtesting(data: dict, lookback_days: int = 50) -> None:
    """Check if data is suitable for backtesting."""
    print("=" * 80)
    print("🔍 BACKTEST READINESS CHECK")
    print("=" * 80)
    print()
    
    if not data:
        print("❌ NO DATA - Cannot run backtest")
        return
    
    # Find common date range
    common_dates = None
    for df in data.values():
        if common_dates is None:
            common_dates = set(df.index)
        else:
            common_dates &= set(df.index)
    
    if not common_dates:
        print("❌ NO COMMON DATES - Assets don't overlap")
        return
    
    common_dates = sorted(common_dates)
    n_days = len(common_dates)
    
    print(f"Common date range: {common_dates[0].date()} to {common_dates[-1].date()}")
    print(f"Common days:       {n_days}")
    print()
    
    # Check if enough for backtesting
    if n_days < lookback_days:
        print(f"⚠️ INSUFFICIENT DATA: Need at least {lookback_days} days for indicators")
        print(f"   Current: {n_days} days")
    else:
        print(f"✅ SUFFICIENT DATA: {n_days} days (need {lookback_days})")
    
    # Estimate backtest period
    usable_days = n_days - lookback_days
    weeks = usable_days // 5
    
    print()
    print("Backtest capacity:")
    print(f"  • Lookback period:   {lookback_days} days")
    print(f"  • Usable data:       {usable_days} days")
    print(f"  • Weekly rebalances: ~{weeks} rebalances")
    print(f"  • Years of data:     ~{n_days/252:.1f} years")
    print()
    
    if weeks < 10:
        print("⚠️ LIMITED: < 10 rebalances (results may not be reliable)")
    elif weeks < 50:
        print("🟡 MODERATE: < 50 rebalances (decent sample size)")
    else:
        print("✅ EXCELLENT: 50+ rebalances (good statistical significance)")
    
    print()
    print("🚀 READY TO BACKTEST!")
    print()


def main():
    """Download real historical data."""
    # Load config to get universe
    config = load_config()
    
    # Date range (5 years)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365 + 50)  # 5 years + buffer
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # Output directory
    output_dir = Path("data/real_historical")
    
    print()
    print("=" * 80)
    print("🔥 DOWNLOADING REAL MARKET DATA")
    print("=" * 80)
    print()
    print("This will download ACTUAL historical prices from Yahoo Finance.")
    print("No more synthetic data - this is the REAL DEAL!")
    print()
    print(f"Universe: {config.universe}")
    print()
    
    # Download
    data = download_real_data(config.universe, start_str, end_str, output_dir)
    
    # Validate
    if data:
        validate_for_backtesting(data, lookback_days=50)
    
    print("=" * 80)
    print("✅ DOWNLOAD COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Review data quality report above")
    print("  2. Run backtest with real data:")
    print("     docker compose run --rm app poetry run python3 scripts/backtest_real_data.py")
    print()


if __name__ == "__main__":
    main()

