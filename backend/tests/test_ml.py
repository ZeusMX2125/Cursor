"""Unit tests for ML components."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from ml.feature_engineering import FeatureEngineer
from ml.signal_validator import SignalValidator
from ml.price_predictor import PricePredictor
# from ml.rl_agent import RLAgent

# Mock pandas/polars data
import polars as pl

@pytest.fixture
def sample_bars():
    return pl.DataFrame({
        "close": [100.0, 101.0, 102.0, 101.5, 103.0] * 10,
        "open": [99.0, 100.0, 101.0, 101.0, 102.0] * 10,
        "high": [101.0, 102.0, 103.0, 102.0, 104.0] * 10,
        "low": [98.0, 99.0, 100.0, 100.0, 101.0] * 10,
        "volume": [1000, 1100, 1200, 900, 1500] * 10
    })

def test_feature_engineering(sample_bars):
    fe = FeatureEngineer()
    df = fe.calculate_indicators(sample_bars)
    
    assert "sma_10" in df.columns
    assert "rsi_14" in df.columns
    assert "macd" in df.columns
    assert "atr_14" in df.columns
    assert "bb_upper" in df.columns
    
    features = fe.extract_features(df)
    assert "current_price" in features
    assert "rsi_14" in features

def test_signal_validator():
    sv = SignalValidator()
    # Mock model
    sv.model = MagicMock()
    sv.model.predict_proba.return_value = [0.2, 0.8] # 80% confidence
    
    signal = {"side": "BUY", "entry_price": 100}
    features = {"current_price": 100, "rsi_14": 50}
    
    is_valid, conf = sv.validate_signal(signal, features)
    assert is_valid is True
    assert conf == 0.8

def test_price_predictor():
    # Requires Torch, skipping if not installed in test env
    try:
        import torch
    except ImportError:
        pytest.skip("Torch not installed")
        
    pp = PricePredictor()
    # Mock internal model
    pp.model = MagicMock()
    pp.model.return_value = torch.tensor([[105.0]])
    
    data = np.zeros((60, 5))
    pred = pp.predict(data)
    assert pred == 105.0

