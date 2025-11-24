# Restart Frontend to See New ALGOX Interface

## ⚠️ Important: You Need to Restart the Frontend Server

The new ALGOX components are created, but you need to **restart the frontend dev server** to see them.

## Steps:

1. **Stop the current frontend server** (if running):
   - Press `Ctrl+C` in the PowerShell window running `npm run dev`

2. **Clear Next.js cache**:
   ```powershell
   cd frontend
   Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
   ```

3. **Restart the frontend**:
   ```powershell
   $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
   npm run dev
   ```

4. **Hard refresh your browser**:
   - Press `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
   - Or open DevTools (F12) → Right-click refresh button → "Empty Cache and Hard Reload"

5. **Navigate to the correct route**:
   - Make sure you're visiting: **http://localhost:3000/trading**
   - NOT: http://localhost:3000/ (that's the old dashboard)

## What You Should See:

✅ ALGOX logo in top bar
✅ Connection status indicators (WS, MD, ORD)
✅ SIM mode badge
✅ Large candlestick chart
✅ Right sidebar with accounts, order entry, strategies
✅ Bottom panel with positions table

If you still see the old interface, make sure:
- You're on `/trading` route (not `/`)
- Browser cache is cleared
- Frontend server was restarted

