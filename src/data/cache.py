"""Parquet cache system with idempotent append."""
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from src.core.logging import get_logger

logger = get_logger(__name__)


class ParquetCache:
    """Parquet-based cache for OHLCV data with idempotent append."""

    def __init__(self, cache_dir: Path) -> None:
        """
        Initialize Parquet cache.

        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, symbol: str) -> Path:
        """
        Get cache file path for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{symbol}.parquet"

    def read(self, symbol: str) -> pd.DataFrame:
        """
        Read cached data for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with OHLCV data, empty if not found
        """
        cache_path = self.get_cache_path(symbol)
        if not cache_path.exists():
            logger.debug(f"No cache found for {symbol}")
            return pd.DataFrame()

        try:
            df = pd.read_parquet(cache_path)
            if not df.empty and df.index.name != "timestamp":
                if "timestamp" in df.columns:
                    df = df.set_index("timestamp")
                else:
                    df.index.name = "timestamp"

            logger.debug(f"Read {len(df)} bars from cache for {symbol}")
            return df
        except Exception as e:
            logger.error(f"Failed to read cache for {symbol}: {e}")
            return pd.DataFrame()

    def write(self, symbol: str, df: pd.DataFrame) -> None:
        """
        Write data to cache (overwrites existing).

        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data
        """
        if df.empty:
            logger.warning(f"Attempted to write empty DataFrame for {symbol}")
            return

        cache_path = self.get_cache_path(symbol)

        # Ensure timestamp is the index
        if df.index.name != "timestamp":
            if "timestamp" in df.columns:
                df = df.set_index("timestamp")
            else:
                df.index.name = "timestamp"

        # Ensure required columns exist
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Sort by timestamp
        df = df.sort_index()

        # Remove duplicates
        df = df[~df.index.duplicated(keep="first")]

        try:
            df.to_parquet(cache_path, engine="pyarrow", index=True)
            logger.info(f"Wrote {len(df)} bars to cache for {symbol}")
        except Exception as e:
            logger.error(f"Failed to write cache for {symbol}: {e}")
            raise

    def append(self, symbol: str, new_df: pd.DataFrame) -> None:
        """
        Append new data to cache (idempotent - only appends missing dates).

        Args:
            symbol: Stock symbol
            new_df: New DataFrame with OHLCV data
        """
        if new_df.empty:
            logger.warning(f"Attempted to append empty DataFrame for {symbol}")
            return

        # Read existing cache
        existing_df = self.read(symbol)

        if existing_df.empty:
            # No existing data, just write
            self.write(symbol, new_df)
            return

        # Ensure timestamp is index
        if new_df.index.name != "timestamp":
            if "timestamp" in new_df.columns:
                new_df = new_df.set_index("timestamp")
            else:
                new_df.index.name = "timestamp"

        # Find dates that don't exist in cache
        existing_dates = set(existing_df.index.date) if not existing_df.empty else set()
        new_dates = set(new_df.index.date)

        # Only append dates that don't exist
        dates_to_append = new_dates - existing_dates
        if not dates_to_append:
            logger.debug(f"All dates for {symbol} already in cache")
            return

        # Filter new data to only missing dates
        new_df_dates = pd.Series([d.date() for d in new_df.index], index=new_df.index)
        mask = new_df_dates.isin(dates_to_append)
        data_to_append = new_df[mask]

        if data_to_append.empty:
            logger.debug(f"No new dates to append for {symbol}")
            return

        # Combine existing and new data
        combined_df = pd.concat([existing_df, data_to_append])
        combined_df = combined_df.sort_index()
        combined_df = combined_df[~combined_df.index.duplicated(keep="first")]

        # Write back
        self.write(symbol, combined_df)
        logger.info(f"Appended {len(data_to_append)} new bars to cache for {symbol}")

    def get_date_range(self, symbol: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Get date range of cached data.

        Args:
            symbol: Stock symbol

        Returns:
            Tuple of (min_date, max_date) or (None, None) if no data
        """
        df = self.read(symbol)
        if df.empty:
            return (None, None)

        return (df.index.min(), df.index.max())
