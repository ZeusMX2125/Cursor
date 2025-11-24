# How to See the New ALGOX Interface

## ✅ The New Interface is Ready!

I've created all the ALGOX components matching your reference screenshot. Here's how to see them:

## 🔍 Important: Check These Things

### 1. **Make Sure You're on the Correct Route**
   - ✅ **CORRECT**: http://localhost:3000/trading
   - ❌ **WRONG**: http://localhost:3000/ (this is the old dashboard)

### 2. **Restart the Frontend Server**

The frontend dev server needs to be restarted to pick up the new components:

```powershell
# Stop the current server (Ctrl+C if running)

# Then restart:
cd frontend
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
npm run dev
```

### 3. **Clear Browser Cache**

After restarting, hard refresh your browser:
- **Windows**: `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`
- Or: Open DevTools (F12) → Right-click refresh → "Empty Cache and Hard Reload"

## 📋 What You Should See (Matching Your Screenshot):

✅ **Top Bar:**
- ALGOX logo on the left
- Instrument name (e.g., "ESZ25 - E-mini S&P 500: December 2025")
- Connection indicators: WS, MD, ORD (green dots)
- SIM badge (yellow)
- Notification, Settings, User icons

✅ **Main Chart Area:**
- Large candlestick chart (NOT area chart)
- Timeframe buttons: 1m, 5m, 15m
- Price display in top-left corner
- Volume bars below chart

✅ **Right Sidebar:**
- **ACCOUNTS** section with:
  - Account cards showing balance, buying power, P&L
  - "Make Leader" and "Flatten" buttons
- **ORDER ENTRY** section with:
  - Account dropdown
  - Contract input
  - Order Type dropdown
  - Size input
  - TIF dropdown
  - Bracket Orders toggle (SL, TP, Trail)
  - Large BUY MKT and SELL MKT buttons
  - Close All Positions button
- **Quick Strategies:**
  - Scalp 2/4 button
  - Breakout button
  - Active Bots indicator

✅ **Bottom Panel:**
- Tabs: ACTIVE POSITIONS, PENDING ORDERS, PREVIOUS ORDERS
- Table with columns: TIME, SYMBOL, SIDE, SIZE, ENTRY, CURRENT, P&L, ACTIONS

## 🐛 If You Still See the Old Interface:

1. **Check the URL** - Must be `/trading` not `/`
2. **Restart frontend server** - The new components won't load until restart
3. **Clear browser cache** - Old JavaScript might be cached
4. **Check browser console** (F12) - Look for any errors

## 📁 Files Created:

All new ALGOX components are in `frontend/components/`:
- `TopBar.tsx` - Top navigation bar
- `CandlestickChart.tsx` - Candlestick chart (replaces area chart)
- `ALGOXAccountPanel.tsx` - Account management
- `ALGOXOrderEntry.tsx` - Order entry form
- `ALGOXQuickStrategies.tsx` - Quick strategy buttons
- `ALGOXPositionsTable.tsx` - Positions table with tabs

The trading page at `/trading` uses all these new components.

