# How to Access the Trading Bot Interface

## 🎯 Quick Access

Once the services are running, access the interface at:

### **Main Trading Interface** (Recommended)
**http://localhost:3000/trading**

This is the full trading interface matching the example you provided, with:
- Live candlestick chart
- Account management panel
- Order entry form
- Orders/Positions tabs
- Strategy management

### Other Pages:
- **Dashboard**: http://localhost:3000/
- **Bot Config**: http://localhost:3000/bot-config
- **Analytics**: http://localhost:3000/analytics
- **Settings**: http://localhost:3000/settings

## 🚀 Starting the Services

### Windows (Easiest):
Double-click `start.bat` or run:
```cmd
start.bat
```

### Mac/Linux:
```bash
chmod +x start.sh
./start.sh
```

### Manual Start:

**Terminal 1 - Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
uvicorn app:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Docker (Alternative):
```bash
docker-compose up
```

## 📊 What You'll See

### Trading Page (`/trading`):
1. **Top Bar**: Symbol name, Sign in button, SIM mode indicator
2. **Main Chart**: Candlestick chart with volume histogram
3. **Right Panel**:
   - **Account Panel**: Shows all your Topstep accounts with balances
   - **Order Entry**: Full order form with Buy/Sell buttons
   - **Strategy Panel**: Strategy management controls
4. **Bottom Tabs**: 
   - Active Positions
   - Pending Orders
   - Previous Orders (with full trade history)
   - Analytics tabs

## 🔧 Troubleshooting

**Port 3000 already in use:**
- Change port in `frontend/package.json`: `"dev": "next dev -p 3001"`
- Or stop the process using port 3000

**Port 8000 already in use:**
- Change port in backend: `uvicorn app:app --reload --port 8001`
- Update `frontend/lib/api.ts` with new port

**npm not found:**
- Install Node.js from https://nodejs.org/
- Restart terminal after installation

**Python not found:**
- Install Python 3.12+ from https://www.python.org/
- Make sure to check "Add to PATH" during installation

## ✅ Verification

Once running, you should see:
- Backend API docs: http://localhost:8000/docs
- Frontend interface: http://localhost:3000/trading
- No console errors in browser

The interface is ready to use! 🎉

