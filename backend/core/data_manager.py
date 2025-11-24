"""Market data manager for processing ticks and generating bars."""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import polars as pl
import pytz
from loguru import logger

from config.settings import Settings


class DataManager:
    """Manages market data ingestion and bar generation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.ct_tz = pytz.timezone(settings.timezone)
        self.tick_buffers: Dict[str, List[Dict]] = defaultdict(list)
        self.bars: Dict[str, Dict[str, pl.DataFrame]] = defaultdict(
            lambda: defaultdict(lambda: pl.DataFrame())
        )
        self.running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the data manager."""
        self.running = True
        asyncio.create_task(self._bar_generation_loop())

    async def stop(self) -> None:
        """Stop the data manager."""
        self.running = False

    def add_tick(self, symbol: str, tick: Dict) -> None:
        """Add a tick to the buffer."""
        self.tick_buffers[symbol].append(tick)

    async def get_bars(
        self, symbol: str, timeframe: str, limit: Optional[int] = None
    ) -> pl.DataFrame:
        """Get bars for a symbol and timeframe."""
        async with self._lock:
            df = self.bars[symbol][timeframe]
            if limit:
                return df.tail(limit)
            return df

    async def _bar_generation_loop(self) -> None:
        """Continuously generate bars from ticks."""
        while self.running:
            try:
                async with self._lock:
                    for symbol in list(self.tick_buffers.keys()):
                        if self.tick_buffers[symbol]:
                            await self._process_ticks(symbol)

                await asyncio.sleep(1)  # Process every second

            except Exception as e:
                logger.error(f"Error in bar generation loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _process_ticks(self, symbol: str) -> None:
        """Process ticks and generate bars."""
        ticks = self.tick_buffers[symbol]
        if not ticks:
            return

        # Convert ticks to DataFrame
        df = pl.DataFrame(ticks)

        # Ensure timestamp column exists and is datetime
        if "timestamp" not in df.columns:
            df = df.with_columns(
                pl.lit(datetime.now(self.ct_tz)).alias("timestamp")
            )

        # Generate bars for different timeframes
        for timeframe in ["1m", "5m", "15m", "1h"]:
            await self._resample_to_bars(symbol, df, timeframe)

        # Clear processed ticks
        self.tick_buffers[symbol].clear()

    async def _resample_to_bars(
        self, symbol: str, tick_df: pl.DataFrame, timeframe: str
    ) -> None:
        """Resample ticks to OHLCV bars."""
        if tick_df.is_empty():
            return

        # Parse timeframe
        timeframe_minutes = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
        }.get(timeframe, 1)

        # Ensure timestamp is datetime
        tick_df = tick_df.with_columns(
            pl.col("timestamp").cast(pl.Datetime)
        )

        # Round timestamps to timeframe boundaries
        tick_df = tick_df.with_columns(
            pl.col("timestamp")
            .dt.truncate(f"{timeframe_minutes}m")
            .alias("bar_time")
        )

        # Group by bar_time and aggregate
        bars = (
            tick_df.group_by("bar_time")
            .agg(
                [
                    pl.first("price").alias("open"),
                    pl.max("price").alias("high"),
                    pl.min("price").alias("low"),
                    pl.last("price").alias("close"),
                    pl.count().alias("volume"),
                ]
            )
            .sort("bar_time")
        )

        # Merge with existing bars
        existing_bars = self.bars[symbol][timeframe]
        if not existing_bars.is_empty():
            # Combine and remove duplicates
            all_bars = pl.concat([existing_bars, bars])
            all_bars = all_bars.unique(subset=["bar_time"], keep="last").sort("bar_time")
            self.bars[symbol][timeframe] = all_bars
        else:
            self.bars[symbol][timeframe] = bars

        logger.debug(
            f"Generated {len(bars)} {timeframe} bars for {symbol}"
        )

