"""API endpoints for ML/AI features."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel

from ml.signal_validator import SignalValidator
from ml.price_predictor import PricePredictor
# from ml.rl_agent import RLAgent

router = APIRouter(prefix="/api/ml", tags=["ML"])

# Singletons (should be initialized in app startup)
signal_validator = SignalValidator()
price_predictor = PricePredictor()

class SignalValidationRequest(BaseModel):
    signal: Dict[str, Any]
    market_features: Dict[str, Any]

class PredictionRequest(BaseModel):
    symbol: str
    timeframe: str = "1m"
    lookback: int = 60

@router.post("/validate-signal")
async def validate_signal(request: SignalValidationRequest):
    """Validate a trading signal."""
    is_valid, confidence = signal_validator.validate_signal(
        request.signal, request.market_features
    )
    return {"is_valid": is_valid, "confidence": confidence}

@router.post("/predict-price")
async def predict_price(request: PredictionRequest):
    """Predict future price for a symbol."""
    # In a real scenario, we would fetch data here using ProjectXService
    # and pass it to the predictor.
    # For now, return a mock prediction or use cached data if available
    
    # prediction = price_predictor.predict(...)
    prediction = 0.0 # Placeholder
    
    return {
        "symbol": request.symbol,
        "predicted_price": prediction, 
        "horizon": "1_bar"
    }

@router.get("/models")
async def list_models():
    """List available ML models and their status."""
    return {
        "signal_validator": {
            "loaded": signal_validator.model is not None,
            "path": signal_validator.model_path
        },
        "price_predictor": {
            "loaded": price_predictor.model is not None,
            "path": price_predictor.model_path
        }
    }

