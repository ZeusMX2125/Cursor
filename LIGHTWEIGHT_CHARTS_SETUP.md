# TradingView Lightweight Charts - Setup Complete

## ✅ What Changed

Switched from **TradingView Advanced Charts** (requires license/download) to **TradingView Lightweight Charts** (open source, free, npm-installable).

## ✅ Completed

1. **Updated package.json**: Added `lightweight-charts` dependency
2. **Rewrote TradingViewChart.tsx**: Now uses Lightweight Charts API
3. **Removed Advanced Charts dependency**: No manual download needed
4. **Fixed PATH warning**: Added `--no-warn-script-location` to pip installs

## 📦 Installation

### Frontend (Lightweight Charts)

Run in the `frontend` directory:
```bash
cd frontend
npm install
```

This will automatically install `lightweight-charts` from npm.

### Backend (ML Dependencies)

Run:
```batch
install_ml_dependencies.bat
```

The PATH warning is now suppressed with `--no-warn-script-location` flag.

## 🎯 Key Differences

**Lightweight Charts** (what we're using now):
- ✅ Open source (Apache 2.0) - FREE
- ✅ Install via npm - no manual download
- ✅ Much lighter weight (~50KB vs several MB)
- ✅ Simpler API - direct data updates
- ✅ Perfect for candlestick charts

**Advanced Charts** (what we replaced):
- ❌ Requires license or manual download
- ❌ Much larger file size
- ❌ More complex datafeed API
- ✅ More features (but we don't need them)

## 🚀 Usage

The `TradingViewChart` component now:
- Uses Lightweight Charts from npm
- Connects directly to TopstepX API
- Updates in real-time via WebSocket
- No manual library download needed!

## 📝 Next Steps

1. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Install backend ML dependencies**:
   ```batch
   install_ml_dependencies.bat
   ```

3. **Restart services**:
   ```batch
   stop.bat
   start.bat
   ```

## ✅ Verification

After installation and restart:
- Frontend: Charts should load without any "library not found" errors
- Backend: `http://localhost:8000/api/ml/models` should work
- Charts: Should display candlesticks with real-time updates

All set! Lightweight Charts is much simpler and free to use.

