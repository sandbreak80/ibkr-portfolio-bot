"""IBKR client for connection and historical data fetching."""
import asyncio
import time
from datetime import datetime, timedelta

import pandas as pd
from ib_insync import IB, Contract, Stock, util

from src.core.config import IBKRConfig
from src.core.logging import get_logger
from src.core.retry import async_retry_with_backoff

logger = get_logger(__name__)


class IBKRClient:
    """IBKR client for data fetching with pacing and backoff."""

    def __init__(self, config: IBKRConfig) -> None:
        """
        Initialize IBKR client.

        Args:
            config: IBKR configuration
        """
        self.config = config
        self.ib = IB()
        self.connected = False
        self._last_request_time = 0.0
        self._min_request_interval = 0.2  # 200ms minimum between requests

    @async_retry_with_backoff(
        max_attempts=3,
        initial_delay=2.0,
        exceptions=(ConnectionError, OSError, TimeoutError)
    )
    async def connect(self) -> None:
        """
        Connect to TWS/Gateway with automatic retry.

        Raises:
            ConnectionError: If connection fails after retries
        """
        try:
            await self.ib.connectAsync(
                host=self.config.host,
                port=self.config.port,
                clientId=self.config.client_id,
            )
            self.connected = True

            # Set market data type
            market_data_type_map = {
                "live": 1,
                "delayed": 3,
                "delayedFrozen": 4,
            }
            market_data_type = market_data_type_map.get(self.config.market_mode, 3)
            self.ib.reqMarketDataType(market_data_type)

            logger.info(
                f"Connected to IBKR at {self.config.host}:{self.config.port} "
                f"(market mode: {self.config.market_mode})"
            )
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to IBKR: {e}")
            raise ConnectionError(f"IBKR connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")

    def _wait_for_pacing(self) -> None:
        """Wait to respect pacing limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _create_contract(self, symbol: str) -> Contract:
        """
        Create a Stock contract for a symbol.

        Args:
            symbol: Stock symbol (e.g., "SPY")

        Returns:
            Contract object
        """
        contract = Stock(symbol, "SMART", "USD")
        return contract

    async def fetch_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        bar_size: str = "1 day",
    ) -> pd.DataFrame:
        """
        Fetch historical data with pacing and exponential backoff.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            bar_size: Bar size (default: "1 day")

        Returns:
            DataFrame with OHLCV data indexed by datetime

        Raises:
            ConnectionError: If not connected
            ValueError: If data fetch fails
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        contract = self._create_contract(symbol)
        self._wait_for_pacing()

        # IBKR limits historical requests to ~1 year chunks
        # Split into chunks if needed
        max_days_per_request = 365
        all_bars = []

        current_start = start_date
        max_retries = 3
        base_backoff = 1.0

        while current_start < end_date:
            current_end = min(current_start + timedelta(days=max_days_per_request), end_date)

            for attempt in range(max_retries):
                try:
                    self._wait_for_pacing()

                    # Request historical data
                    bars = await self.ib.reqHistoricalDataAsync(
                        contract,
                        endDateTime=current_end,
                        durationStr=f"{max_days_per_request} D",
                        barSizeSetting=bar_size,
                        whatToShow="TRADES",
                        useRTH=True,
                        formatDate=1,
                    )

                    if bars:
                        all_bars.extend(bars)
                        logger.debug(
                            f"Fetched {len(bars)} bars for {symbol} "
                            f"from {current_start.date()} to {current_end.date()}"
                        )
                        break  # Success, exit retry loop

                except Exception as e:
                    if attempt < max_retries - 1:
                        backoff_time = base_backoff * (2**attempt)
                        logger.warning(
                            f"Request failed for {symbol} (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {backoff_time}s: {e}"
                        )
                        await asyncio.sleep(backoff_time)
                    else:
                        logger.error(f"Failed to fetch data for {symbol} after {max_retries} attempts: {e}")
                        raise ValueError(f"Historical data fetch failed for {symbol}: {e}") from e

            current_start = current_end + timedelta(days=1)

        if not all_bars:
            logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()

        # Convert to DataFrame
        df = util.df(all_bars)
        if df.empty:
            return pd.DataFrame()

        # Normalize column names and index
        df = df.rename(
            columns={
                "date": "timestamp",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
            }
        )

        # Ensure timestamp is datetime and set as index
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
        elif df.index.name == "date":
            df.index = pd.to_datetime(df.index)
            df.index.name = "timestamp"

        # Select only OHLCV columns
        required_cols = ["open", "high", "low", "close", "volume"]
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]

        # Sort by timestamp
        df = df.sort_index()

        # Remove duplicates
        df = df[~df.index.duplicated(keep="first")]

        logger.info(f"Fetched {len(df)} bars for {symbol} from {df.index.min()} to {df.index.max()}")
        return df

    def get_account_summary(self) -> dict:
        """
        Get account summary.

        Returns:
            Dictionary with account information

        Raises:
            ConnectionError: If not connected
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        account_values = self.ib.accountValues()
        summary = {}
        for av in account_values:
            summary[av.tag] = av.value

        return summary
