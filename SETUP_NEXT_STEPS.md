# Critical Next Steps - Setup Complete

## ✅ Completed Automatically

1. **ML Router Registered**: Added ML endpoints router to `backend/app.py`
2. **Search Endpoint Added**: Created `/api/market/search` for TradingView symbol search
3. **Installation Script**: Created `install_ml_dependencies.bat` for easy dependency installation

## 🔧 Action Required: Install Dependencies

Run the installation script:

```batch
install_ml_dependencies.bat
```

Or manually install:

```batch
cd backend
py -m pip install torch>=2.0.0 stable-baselines3>=2.0.0 gymnasium>=0.29.0 xgboost>=2.0.3 joblib
```

**Note**: PyTorch installation may take 5-10 minutes depending on your internet speed.

## 📦 Action Required: Install TradingView Library

**You must download the TradingView Charting Library manually:**

1. Visit: https://www.tradingview.com/charting-library/
2. Download the "Charting Library" (Advanced Charts)
3. Extract the `charting_library` folder to `frontend/public/charting_library/`
4. Verify `charting_library.standalone.js` exists (should be several MB, not a placeholder)

See `TRADINGVIEW_INSTALL.md` for detailed instructions.

## 🚀 Restart Services

After installing dependencies and TradingView library:

```batch
stop.bat
start.bat
```

## ✅ Verification

After restart, verify:

1. **Backend**: Check `http://localhost:8000/api/ml/models` - should return model status
2. **Backend**: Check `http://localhost:8000/api/market/search?query=ES` - should return contracts
3. **Frontend**: Open browser console - should NOT show "TradingView Library not installed"
4. **Frontend**: Charts should load with TradingView interface

## 📝 Notes

- ML models will run in "pass-through" mode until trained models are placed in `backend/models/`
- To train models, run:
  - `python backend/ml/train_validator.py` (for signal validator)
  - `python backend/ml/rl_trainer.py` (for RL agent)
- TradingView charts require the actual library file - the placeholder will not work

## 🐛 Troubleshooting

**If backend fails to start:**
- Check that all dependencies installed correctly
- Verify Python version (3.8+)
- Check `backend/logs/` for error messages

**If charts don't load:**
- Verify TradingView library is in correct location
- Check browser console for errors
- Ensure `charting_library.standalone.js` is the actual file (not placeholder)

**If ML features don't work:**
- Models default to pass-through mode if not found (this is expected)
- Train models using the training scripts
- Check `backend/models/` directory exists

