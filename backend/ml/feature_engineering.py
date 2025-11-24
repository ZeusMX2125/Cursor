"""Feature engineering for ML models."""

from typing import Dict, List

import polars as pl


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
        ])

        # VWAP
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        if "volume" in df.columns:
            vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
            df = df.with_columns([vwap.alias("vwap")])

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
        """Extract features for ML model."""
        if bars.is_empty():
            return {}

        latest = bars.tail(1)

        features = {
            "current_price": latest["close"].item(),
            "sma_10": latest.get("sma_10", [0])[0] if "sma_10" in latest.columns else 0,
            "sma_20": latest.get("sma_20", [0])[0] if "sma_20" in latest.columns else 0,
            "sma_50": latest.get("sma_50", [0])[0] if "sma_50" in latest.columns else 0,
            "sma_200": latest.get("sma_200", [0])[0] if "sma_200" in latest.columns else 0,
            "rsi_14": latest.get("rsi_14", [50])[0] if "rsi_14" in latest.columns else 50,
            "macd": latest.get("macd", [0])[0] if "macd" in latest.columns else 0,
            "macd_signal": latest.get("macd_signal", [0])[0] if "macd_signal" in latest.columns else 0,
            "atr_14": latest.get("atr_14", [0])[0] if "atr_14" in latest.columns else 0,
            "bb_upper": latest.get("bb_upper", [0])[0] if "bb_upper" in latest.columns else 0,
            "bb_lower": latest.get("bb_lower", [0])[0] if "bb_lower" in latest.columns else 0,
            "vwap": latest.get("vwap", [0])[0] if "vwap" in latest.columns else 0,
        }

        return features

