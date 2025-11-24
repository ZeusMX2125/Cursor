"""Historical data service using ProjectX API."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

import polars as pl
import pytz
from loguru import logger

from api.topstepx_client import TopstepXClient
from api.auth_manager import AuthManager
from config.settings import Settings


class HistoricalDataService:
    """Fetches and caches historical data from ProjectX API."""

    def __init__(self, settings: Settings, auth_manager: AuthManager):
        self.settings = settings
        self.auth_manager = auth_manager
        self.api_client = TopstepXClient(settings, auth_manager)
        self.cache_dir = Path("data/historical")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize the API client."""
        await self.api_client.initialize()

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        use_cache: bool = True,
    ) -> pl.DataFrame:
        """
        Fetch historical bars from API or cache.

        Args:
            symbol: Trading symbol (MNQ, MES, MGC)
            timeframe: Bar timeframe (1m, 5m, 15m, 1h, 1d)
            start_date: Start date
            end_date: End date
            use_cache: Whether to use cached data if available

        Returns:
            DataFrame with OHLCV bars
        """
        # Check cache first
        cache_file = self._get_cache_file(symbol, timeframe, start_date, end_date)
        if use_cache and cache_file.exists():
            logger.info(f"Loading cached data from {cache_file}")
            return pl.read_parquet(cache_file)

        # Fetch from API
        logger.info(
            f"Fetching {symbol} {timeframe} data from {start_date} to {end_date}"
        )

        all_bars = []
        current_start = start_date

        # API rate limit: 50 requests per 30 seconds
        # Fetch in chunks to respect rate limits
        while current_start < end_date:
            # Calculate chunk end (max 30 days per request to avoid large responses)
            chunk_end = min(current_start + timedelta(days=30), end_date)

            try:
                bars = await self.api_client.retrieve_bars(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=current_start.strftime("%Y-%m-%d"),
                    end_date=chunk_end.strftime("%Y-%m-%d"),
                )

                if bars:
                    all_bars.extend(bars)

                # Rate limiting: wait 0.6 seconds between requests (50 req/30s = 0.6s)
                await asyncio.sleep(0.6)

                current_start = chunk_end + timedelta(days=1)

            except Exception as e:
                logger.error(f"Error fetching bars: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait longer on error
                continue

        if not all_bars:
            logger.warning(f"No bars fetched for {symbol} {timeframe}")
            return pl.DataFrame()

        # Convert to DataFrame
        df = pl.DataFrame(all_bars)

        # Ensure timestamp column exists
        if "timestamp" not in df.columns and "time" in df.columns:
            df = df.rename({"time": "timestamp"})

        # Parse timestamp if string
        if "timestamp" in df.columns:
            df = df.with_columns(
                pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S")
            )

        # Ensure required columns
        required_cols = ["timestamp", "open", "high", "low", "close"]
        if "volume" not in df.columns:
            df = df.with_columns(pl.lit(0).alias("volume"))

        # Sort by timestamp
        df = df.sort("timestamp")

        # Cache the data
        if use_cache:
            df.write_parquet(cache_file)
            logger.info(f"Cached data to {cache_file}")

        return df

    async def fetch_multiple_symbols(
        self,
        symbols: List[str],
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, pl.DataFrame]:
        """Fetch bars for multiple symbols."""
        results = {}

        for symbol in symbols:
            try:
                bars = await self.fetch_bars(symbol, timeframe, start_date, end_date)
                results[symbol] = bars
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}", exc_info=True)
                results[symbol] = pl.DataFrame()

        return results

    def _get_cache_file(
        self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime
    ) -> Path:
        """Get cache file path for a data request."""
        filename = f"{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.parquet"
        return self.cache_dir / filename

    async def get_available_dates(
        self, symbol: str, timeframe: str
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Get available date range for a symbol/timeframe.

        Returns:
            (earliest_date, latest_date) or (None, None) if unavailable
        """
        # Try to fetch a small sample to determine range
        try:
            # Try recent data first
            end_date = datetime.now(pytz.timezone(self.settings.timezone))
            start_date = end_date - timedelta(days=7)

            sample = await self.fetch_bars(symbol, timeframe, start_date, end_date, use_cache=False)

            if sample.is_empty():
                return None, None

            earliest = sample["timestamp"].min()
            latest = sample["timestamp"].max()

            return earliest, latest

        except Exception as e:
            logger.error(f"Error getting available dates: {e}", exc_info=True)
            return None, None

