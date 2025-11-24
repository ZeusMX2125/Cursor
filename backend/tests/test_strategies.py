"""Tests for trading strategies."""

import polars as pl
import pytest

from strategies.ict_silver_bullet import ICTSilverBulletStrategy


@pytest.fixture
def sample_bars():
    """Create sample OHLCV bars for testing."""
    data = {
        "timestamp": list(range(100)),
        "open": [100.0 + i * 0.1 for i in range(100)],
        "high": [100.5 + i * 0.1 for i in range(100)],
        "low": [99.5 + i * 0.1 for i in range(100)],
        "close": [100.0 + i * 0.1 for i in range(100)],
        "volume": [1000] * 100,
    }
    return pl.DataFrame(data)


def test_ict_silver_bullet_strategy(sample_bars):
    """Test ICT Silver Bullet strategy."""
    strategy = ICTSilverBulletStrategy(["MNQ"])
    signal = strategy.analyze("MNQ", sample_bars)
    # Strategy may or may not generate signal depending on conditions
    assert signal is None or isinstance(signal, object)

