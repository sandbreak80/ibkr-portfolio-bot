"""CLI entry point."""
import asyncio
import json
import time
from datetime import datetime
from typing import Optional

import click
import pandas as pd

from src.core.alerting import (
    send_data_quality_warning,
    send_rebalance_error_alert,
    send_rebalance_success_alert,
)
from src.core.config import load_config
from src.core.logging import setup_logging
from src.data.cache import ParquetCache
from src.data.ingestion import DataIngestion
from src.data.validation import check_data_quality_batch
from src.strategy.backtest import run_backtest
from src.strategy.permutation import run_permutation_tests_on_windows
from src.strategy.reporting import generate_backtest_report
from src.strategy.selector import select_assets
from src.strategy.walkforward import run_walkforward
from src.strategy.weighting import calculate_weights


@click.group()
@click.option("--log-level", default="INFO", help="Logging level")
@click.pass_context
def main(ctx: click.Context, log_level: str) -> None:
    """IBKR Portfolio Bot - Production-grade swing trading system."""
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    setup_logging(log_level=log_level)


@main.command()
def connect() -> None:
    """Verify TWS/Gateway connection and print account summary."""
    from src.brokers.ibkr_client import IBKRClient

    config = load_config()
    client = IBKRClient(config.ibkr)

    async def run_connect() -> None:
        try:
            await client.connect()
            summary = client.get_account_summary()
            click.echo(f"Connected to IBKR at {config.ibkr.host}:{config.ibkr.port}")
            click.echo(f"Account summary: {summary}")
            await client.disconnect()
        except Exception as e:
            click.echo(f"Connection failed: {e}", err=True)
            raise

    asyncio.run(run_connect())


@main.command()
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--force-refresh", is_flag=True, help="Force refresh all data")
def fetch(start: Optional[str], end: Optional[str], force_refresh: bool) -> None:
    """Fetch/update OHLCV data to Parquet cache."""
    config = load_config()
    ingestion = DataIngestion(config)

    # Parse dates
    start_date = None
    end_date = None
    if start:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    if end:
        end_date = datetime.strptime(end, "%Y-%m-%d")

    click.echo(f"Fetching data for universe: {config.universe}")
    if start_date:
        click.echo(f"Start date: {start_date.date()}")
    if end_date:
        click.echo(f"End date: {end_date.date()}")

    # Run async fetch
    async def run_fetch() -> None:
        results = await ingestion.fetch_all(force_refresh=force_refresh)
        for symbol, df in results.items():
            if not df.empty:
                click.echo(f"✓ {symbol}: {len(df)} bars")
            else:
                click.echo(f"✗ {symbol}: No data")

    asyncio.run(run_fetch())


@main.command()
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
def backtest(start: Optional[str], end: Optional[str]) -> None:
    """Run daily backtest and produce metrics/plots/logs/weights."""
    from pathlib import Path

    config = load_config()
    cache = ParquetCache(Path("data/parquet"))

    # Load data from cache
    click.echo("Loading data from cache...")
    data = {}
    for symbol in config.universe:
        df = cache.read(symbol)
        if not df.empty:
            data[symbol] = df
            click.echo(f"✓ Loaded {symbol}: {len(df)} bars")

    if not data:
        click.echo("Error: No data found in cache. Run 'fetch' first.", err=True)
        return

    # Calculate returns
    click.echo("Calculating returns...")
    returns_dict = {}
    for symbol, df in data.items():
        returns = df["close"].pct_change()
        returns_dict[symbol] = returns

    returns = pd.DataFrame(returns_dict)
    returns = returns.fillna(0.0)

    # Parse date range
    start_date = None
    end_date = None
    if start:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    if end:
        end_date = datetime.strptime(end, "%Y-%m-%d")

    # Run backtest
    click.echo("Running backtest...")
    results = run_backtest(data, config, start_date, end_date)

    if not results:
        click.echo("Error: Backtest returned no results", err=True)
        return

    # Generate report
    click.echo("Generating report...")
    output_dir = Path("reports")
    metrics = generate_backtest_report(results, output_dir)

    # Display metrics
    click.echo("\nBacktest Metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            click.echo(f"  {key}: {value:.4f}")
        else:
            click.echo(f"  {key}: {value}")

    click.echo(f"\nReports saved to {output_dir}/")


@main.command()
def walkforward() -> None:
    """Run walk-forward test with rolling train/OOS."""
    from pathlib import Path

    config = load_config()
    cache = ParquetCache(Path("data/parquet"))

    # Load data from cache
    click.echo("Loading data from cache...")
    data = {}
    for symbol in config.universe:
        df = cache.read(symbol)
        if not df.empty:
            data[symbol] = df

    if not data:
        click.echo("Error: No data found in cache. Run 'fetch' first.", err=True)
        return

    # Calculate returns
    returns_dict = {}
    for symbol, df in data.items():
        returns = df["close"].pct_change()
        returns_dict[symbol] = returns

    returns = pd.DataFrame(returns_dict)
    returns = returns.fillna(0.0)

    # Run walk-forward
    click.echo("Running walk-forward analysis...")
    results = run_walkforward(data, returns, config)

    if not results:
        click.echo("Error: Walk-forward returned no results", err=True)
        return

    # Display results
    oos_results = results.get("oos_results", [])
    click.echo(f"\nWalk-Forward Results ({len(oos_results)} windows):")
    for result in oos_results:
        window = result.get("window", 0)
        metrics = result.get("metrics", {})
        params = result.get("params", {})
        click.echo(f"\nWindow {window}:")
        click.echo(f"  Params: {params}")
        for key, value in metrics.items():
            if isinstance(value, float):
                click.echo(f"  {key}: {value:.4f}")
            else:
                click.echo(f"  {key}: {value}")


@main.command()
@click.option("--runs", default=200, help="Number of permutation runs")
def permute(runs: int) -> None:
    """Run IMCPT-lite permutation test."""
    from pathlib import Path

    config = load_config()
    config.permutation.runs = runs
    cache = ParquetCache(Path("data/parquet"))

    # Load data from cache
    click.echo("Loading data from cache...")
    data = {}
    for symbol in config.universe:
        df = cache.read(symbol)
        if not df.empty:
            data[symbol] = df

    if not data:
        click.echo("Error: No data found in cache. Run 'fetch' first.", err=True)
        return

    # Calculate returns
    returns_dict = {}
    for symbol, df in data.items():
        returns = df["close"].pct_change()
        returns_dict[symbol] = returns

    returns = pd.DataFrame(returns_dict)
    returns = returns.fillna(0.0)

    # Run permutation tests
    click.echo(f"Running permutation tests ({runs} runs per window)...")
    results = run_permutation_tests_on_windows(data, returns, config)

    if not results:
        click.echo("Error: Permutation tests returned no results", err=True)
        return

    # Display results
    click.echo(f"\nPermutation Test Results ({len(results)} windows):")
    for result in results:
        window = result.get("window", 0)
        p_value = result.get("p_value")
        real_score = result.get("real_score")
        if p_value is not None:
            click.echo(f"\nWindow {window}:")
            click.echo(f"  Real score: {real_score:.4f}")
            click.echo(f"  P-value: {p_value:.4f}")


@main.command()
@click.option("--asof", help="As-of date (YYYY-MM-DD)")
def weights(asof: Optional[str]) -> None:
    """Print target weights JSON as of a date."""
    from pathlib import Path

    config = load_config()
    cache = ParquetCache(Path("data/parquet"))

    # Parse date
    if asof:
        target_date = datetime.strptime(asof, "%Y-%m-%d")
    else:
        target_date = datetime.now()

    # Load data from cache
    click.echo(f"Loading data as of {target_date.date()}...")
    data = {}
    for symbol in config.universe:
        df = cache.read(symbol)
        if not df.empty:
            # Filter to date
            df_filtered = df[df.index <= target_date]
            if not df_filtered.empty:
                data[symbol] = df_filtered

    if not data:
        click.echo("Error: No data found in cache. Run 'fetch' first.", err=True)
        return

    # Calculate returns
    returns_dict = {}
    for symbol, df in data.items():
        returns = df["close"].pct_change()
        returns_dict[symbol] = returns

    returns = pd.DataFrame(returns_dict)
    returns = returns.fillna(0.0)

    # Select assets and calculate weights
    click.echo("Calculating weights...")
    selected = select_assets(data, returns, config, date=target_date)

    if not selected:
        click.echo("No assets selected (all failed gates)")
        weights_dict = {}
    else:
        weights_dict = calculate_weights(selected, returns, config)

    # Output as JSON
    output = {
        "date": target_date.isoformat(),
        "selected": selected,
        "weights": weights_dict,
    }

    click.echo(json.dumps(output, indent=2))


@main.command()
@click.option("--dry-run", is_flag=True, help="Compute orders but don't route")
@click.option("--paper", is_flag=True, help="Route to paper account")
@click.option("--live", is_flag=True, help="Route to live account")
def trade(dry_run: bool, paper: bool, live: bool) -> None:
    """Build orders from weights and route to IBKR."""
    from pathlib import Path

    from src.brokers.ibkr_client import IBKRClient
    from src.brokers.ibkr_exec import IBKRExecutor

    config = load_config()

    # Validate mode
    if live and not config.ibkr.account_live:
        click.echo("Error: Live account not configured", err=True)
        return

    if not paper and not live:
        paper = True  # Default to paper

    # Load data and calculate weights
    cache = ParquetCache(Path("data/parquet"))
    data = {}
    for symbol in config.universe:
        df = cache.read(symbol)
        if not df.empty:
            data[symbol] = df

    if not data:
        click.echo("Error: No data found in cache. Run 'fetch' first.", err=True)
        return

    # Calculate returns
    returns_dict = {}
    for symbol, df in data.items():
        returns = df["close"].pct_change()
        returns_dict[symbol] = returns

    returns = pd.DataFrame(returns_dict)
    returns = returns.fillna(0.0)

    # Calculate weights
    selected = select_assets(data, returns, config)
    if not selected:
        click.echo("No assets selected (all failed gates)")
        return

    weights_dict = calculate_weights(selected, returns, config)

    async def run_trade() -> None:
        start_time = time.time()
        client = None

        try:
            # Validate data quality
            click.echo("Validating data quality...")
            failures = check_data_quality_batch(data, max_staleness_days=2)

            if failures:
                click.echo(f"⚠️  Data quality issues detected for {len(failures)} symbols:")
                for symbol, error in failures.items():
                    click.echo(f"  - {symbol}: {error}")
                    send_data_quality_warning(symbol, error)

                # Remove failed symbols from consideration
                for symbol in failures:
                    if symbol in data:
                        del data[symbol]

                if not data:
                    raise ValueError("All symbols failed data quality checks")

            # Connect to IBKR
            click.echo("Connecting to IBKR...")
            client = IBKRClient(config.ibkr)
            await client.connect()

            executor = IBKRExecutor(client, config)

            # Get account value for metrics
            account_summary = client.get_account_summary()
            account_value = float(account_summary.get("NetLiquidation", 0))

            click.echo(f"Executing rebalance (dry-run={dry_run}, paper={paper}, live={live})")
            click.echo(f"Account value: ${account_value:,.2f}")
            click.echo(f"Target weights: {weights_dict}")

            results = await executor.execute_rebalance(
                weights_dict,
                dry_run=dry_run,
                paper=paper,
                live=live,
            )

            # Display results
            orders_placed = 0
            for result in results:
                status = result.get("status", "unknown")
                order = result.get("order", {})
                click.echo(f"{status}: {order.get('action')} {order.get('quantity')} {order.get('symbol')}")

                if status in ["submitted", "filled"]:
                    orders_placed += 1

            await client.disconnect()

            # Calculate execution time
            execution_time = time.time() - start_time

            # Send success alert (skip for dry-run)
            if not dry_run:
                send_rebalance_success_alert(
                    orders_placed=orders_placed,
                    portfolio_value=account_value,
                    positions=weights_dict,
                    execution_time_seconds=execution_time
                )

            click.echo(f"\n✅ Rebalance completed in {execution_time:.1f}s")

        except Exception as e:
            click.echo(f"❌ Trade execution failed: {e}", err=True)

            # Send error alert
            context = {
                "mode": "live" if live else "paper",
                "dry_run": dry_run,
                "universe_size": len(config.universe),
            }
            send_rebalance_error_alert(e, context=context)

            # Cleanup
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass

            raise

    asyncio.run(run_trade())


if __name__ == "__main__":
    main()
