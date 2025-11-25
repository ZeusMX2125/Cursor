"""Feature engineering for ML models."""

from typing import Dict, List

import polars as pl
import numpy as np


class FeatureEngineer:
    """Generates features from market data for ML models."""

    @staticmethod
    def calculate_indicators(bars: pl.DataFrame) -> pl.DataFrame:
        """
        Calculate technical indicators from OHLCV data.

        Returns:
            DataFrame with added indicator columns
        """
        df = bars.clone()

        # Moving Averages
        df = df.with_columns([
            pl.col("close").ewm_mean(span=10).alias("sma_10"),
            pl.col("close").ewm_mean(span=20).alias("sma_20"),
            pl.col("close").ewm_mean(span=50).alias("sma_50"),
            pl.col("close").ewm_mean(span=200).alias("sma_200"),
        ])

        # RSI
        df = df.with_columns([
            FeatureEngineer._calculate_rsi(df["close"], 14).alias("rsi_14"),
        ])

        # MACD
        macd_line = df["close"].ewm_mean(span=12) - df["close"].ewm_mean(span=26)
        signal_line = macd_line.ewm_mean(span=9)
        df = df.with_columns([
            macd_line.alias("macd"),
            signal_line.alias("macd_signal"),
            (macd_line - signal_line).alias("macd_histogram"),
        ])

        # ATR
        df = df.with_columns([
            FeatureEngineer._calculate_atr(df, 14).alias("atr_14"),
        ])

        # Bollinger Bands
        sma_20 = df["close"].ewm_mean(span=20)
        std_20 = df["close"].rolling_std(20)
        df = df.with_columns([
            sma_20.alias("bb_middle"),
            (sma_20 + 2 * std_20).alias("bb_upper"),
            (sma_20 - 2 * std_20).alias("bb_lower"),
            ((pl.col("close") - (sma_20 - 2 * std_20)) / (4 * std_20)).alias("bb_percent_b")
        ])

        # VWAP
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        if "volume" in df.columns:
            vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
            df = df.with_columns([vwap.alias("vwap")])
            
            # OBV (On Balance Volume)
            price_change = df["close"].diff().fill_null(0)
            direction = pl.when(price_change > 0).then(1).when(price_change < 0).then(-1).otherwise(0)
            obv = (direction * df["volume"]).cumsum()
            df = df.with_columns([obv.alias("obv")])

        # Price Action Features
        body_size = (df["close"] - df["open"]).abs()
        upper_shadow = df["high"] - pl.max_horizontal(df["open"], df["close"])
        lower_shadow = pl.min_horizontal(df["open"], df["close"]) - df["low"]
        candle_range = df["high"] - df["low"]
        
        df = df.with_columns([
            body_size.alias("candle_body_size"),
            upper_shadow.alias("candle_upper_shadow"),
            lower_shadow.alias("candle_lower_shadow"),
            candle_range.alias("candle_range"),
            (body_size / (candle_range + 1e-9)).alias("body_to_range_ratio"),
            (upper_shadow / (body_size + 1e-9)).alias("upper_shadow_ratio"),
            (lower_shadow / (body_size + 1e-9)).alias("lower_shadow_ratio")
        ])

        # Momentum / ROC
        df = df.with_columns([
            (pl.col("close") / pl.col("close").shift(10) - 1).alias("roc_10"),
            (pl.col("close") / pl.col("close").shift(20) - 1).alias("roc_20")
        ])

        return df

    @staticmethod
    def _calculate_rsi(prices: pl.Series, period: int = 14) -> pl.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling_mean(period)
        avg_loss = loss.rolling_mean(period)

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def _calculate_atr(bars: pl.DataFrame, period: int = 14) -> pl.Series:
        """Calculate ATR."""
        high_low = bars["high"] - bars["low"]
        high_close = (bars["high"] - bars["close"].shift(1)).abs()
        low_close = (bars["low"] - bars["close"].shift(1)).abs()

        tr = pl.concat([high_low, high_close, low_close], how="horizontal").max(axis=1)
        atr = tr.rolling_mean(period)

        return atr

    @staticmethod
    def extract_features(bars: pl.DataFrame) -> Dict:
        """Extract features for ML model from the latest bar."""
        if bars.is_empty():
            return {}

        latest = bars.tail(1)

        # Helper to safely get value or default
        def get_val(col, default=0.0):
            return float(latest.get(col, [default])[0]) if col in latest.columns else default

        features = {
            # Price & Trend
            "current_price": get_val("close"),
            "sma_10_dist": (get_val("close") - get_val("sma_10")) / (get_val("sma_10") + 1e-9),
            "sma_20_dist": (get_val("close") - get_val("sma_20")) / (get_val("sma_20") + 1e-9),
            "sma_50_dist": (get_val("close") - get_val("sma_50")) / (get_val("sma_50") + 1e-9),
            "sma_200_dist": (get_val("close") - get_val("sma_200")) / (get_val("sma_200") + 1e-9),
            
            # Momentum
            "rsi_14": get_val("rsi_14", 50.0),
            "macd": get_val("macd"),
            "macd_signal": get_val("macd_signal"),
            "macd_hist": get_val("macd_histogram"),
            "roc_10": get_val("roc_10"),
            "roc_20": get_val("roc_20"),
            
            # Volatility
            "atr_14": get_val("atr_14"),
            "bb_width": (get_val("bb_upper") - get_val("bb_lower")) / (get_val("bb_middle") + 1e-9),
            "bb_percent_b": get_val("bb_percent_b"),
            
            # Volume
            "vwap_dist": (get_val("close") - get_val("vwap")) / (get_val("vwap") + 1e-9),
            "obv": get_val("obv"),
            "volume_ratio": get_val("volume") / (latest["volume"].mean() + 1e-9), # simplified relative volume
            
            # Price Action
            "body_size_norm": get_val("body_to_range_ratio"),
            "upper_shadow_norm": get_val("upper_shadow_ratio"),
            "lower_shadow_norm": get_val("lower_shadow_ratio"),
        }

        return features
