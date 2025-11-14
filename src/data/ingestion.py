"""Data ingestion orchestrator."""
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from src.brokers.ibkr_client import IBKRClient
from src.core.config import AppConfig, load_config
from src.core.logging import get_logger
from src.data.cache import ParquetCache
from src.data.universe import UniverseManager

logger = get_logger(__name__)


class DataIngestion:
    """Orchestrates data fetching and caching."""

    def __init__(self, config: Optional[AppConfig] = None, cache_dir: Optional[Path] = None) -> None:
        """
        Initialize data ingestion.

        Args:
            config: Application configuration (loads default if not provided)
            cache_dir: Cache directory (default: data/parquet)
        """
        self.config = config or load_config()
        self.cache_dir = cache_dir or Path("data/parquet")
        self.cache = ParquetCache(self.cache_dir)
        self.universe_manager = UniverseManager(self.config)
        self.client = IBKRClient(self.config.ibkr)

    async def fetch_and_cache_symbol(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch and cache data for a single symbol.

        Args:
            symbol: Stock symbol
            start_date: Start date (uses config default if not provided)
            end_date: End date (uses current date if not provided)
            force_refresh: If True, fetch all data regardless of cache

        Returns:
            DataFrame with OHLCV data
        """
        # Parse dates
        if start_date is None:
            if self.config.ibkr.start:
                start_date = datetime.strptime(self.config.ibkr.start, "%Y-%m-%d")
            else:
                start_date = datetime(2015, 1, 1)

        if end_date is None:
            if self.config.ibkr.end:
                end_date = datetime.strptime(self.config.ibkr.end, "%Y-%m-%d")
            else:
                end_date = datetime.now()

        # Check cache
        if not force_refresh:
            cached_df = self.cache.read(symbol)
            if not cached_df.empty:
                cache_min, cache_max = self.cache.get_date_range(symbol)
                if cache_min and cache_max:
                    # Check if we need to fetch more data
                    if start_date >= cache_min and end_date <= cache_max:
                        logger.info(f"All data for {symbol} already in cache")
                        return cached_df

                    # Fetch missing ranges
                    if start_date < cache_min:
                        logger.info(f"Fetching earlier data for {symbol} (before {cache_min.date()})")
                        new_df = await self.client.fetch_historical_data(
                            symbol, start_date, cache_min - pd.Timedelta(days=1)
                        )
                        if not new_df.empty:
                            self.cache.append(symbol, new_df)

                    if end_date > cache_max:
                        logger.info(f"Fetching later data for {symbol} (after {cache_max.date()})")
                        new_df = await self.client.fetch_historical_data(
                            symbol, cache_max + pd.Timedelta(days=1), end_date
                        )
                        if not new_df.empty:
                            self.cache.append(symbol, new_df)

                    # Return updated cache
                    return self.cache.read(symbol)

        # Fetch all data
        logger.info(f"Fetching data for {symbol} from {start_date.date()} to {end_date.date()}")
        df = await self.client.fetch_historical_data(symbol, start_date, end_date, self.config.ibkr.timeframe)

        if not df.empty:
            if force_refresh:
                self.cache.write(symbol, df)
            else:
                self.cache.append(symbol, df)
        else:
            logger.warning(f"No data returned for {symbol}")

        return df

    async def fetch_all(self, force_refresh: bool = False) -> dict[str, pd.DataFrame]:
        """
        Fetch and cache data for all symbols in universe.

        Args:
            force_refresh: If True, fetch all data regardless of cache

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        # Validate universe
        is_valid, invalid = self.universe_manager.validate_universe()
        if not is_valid:
            logger.warning(f"Invalid symbols in universe: {invalid}")

        # Connect to IBKR
        if not self.client.connected:
            await self.client.connect()

        try:
            universe = self.universe_manager.get_universe()
            results = {}

            for symbol in universe:
                try:
                    df = await self.fetch_and_cache_symbol(symbol, force_refresh=force_refresh)
                    results[symbol] = df
                except Exception as e:
                    logger.error(f"Failed to fetch {symbol}: {e}")
                    results[symbol] = pd.DataFrame()

            return results
        finally:
            await self.client.disconnect()
