# Quick Start Guide - TopstepX Trading Bot

## 🚀 Getting the Interface Running

### Step 1: Install Dependencies

**Backend (Python):**
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

**Frontend (Node.js):**
```bash
cd frontend
npm install
```

### Step 2: Configure Environment

1. Copy environment file:
```bash
cp config/.env.example config/.env
```

2. Edit `config/.env` with your TopstepX credentials:
```
TOPSTEPX_USERNAME=your_username
TOPSTEPX_API_KEY=your_api_key
```

3. (Optional) Configure accounts:
```bash
cp config/accounts.yaml.example config/accounts.yaml
# Edit with your account details
```

### Step 3: Start the Services

**Terminal 1 - Backend:**
```bash
cd backend
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Mac/Linux
uvicorn app:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Step 4: Access the Interface

Open your browser to:
- **Main Dashboard**: http://localhost:3000
- **Trading Interface**: http://localhost:3000/trading
- **Bot Configuration**: http://localhost:3000/bot-config
- **Analytics**: http://localhost:3000/analytics

## 📊 Available Pages

1. **Dashboard** (`/`) - Overview with stats cards and active positions
2. **Trading** (`/trading`) - Full trading interface with:
   - Live candlestick chart
   - Account management panel
   - Order entry form
   - Orders/Positions tabs
   - Strategy management
3. **Bot Config** (`/bot-config`) - Configure strategies and risk parameters
4. **Analytics** (`/analytics`) - Backtesting and performance analysis

## 🎯 Features Implemented

✅ Multi-account support
✅ Live trading chart
✅ Account management panel
✅ Order entry with stop loss/take profit
✅ Previous orders table
✅ Active positions tracking
✅ Strategy management panel
✅ Deep backtesting interface

## 🔧 Troubleshooting

**Frontend won't start:**
- Make sure Node.js 18+ is installed
- Run `npm install` in the frontend directory

**Backend won't start:**
- Check Python 3.12+ is installed
- Verify virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`

**API connection errors:**
- Ensure backend is running on port 8000
- Check CORS settings in `backend/app.py`
- Verify API credentials in `config/.env`

## 📝 Next Steps

1. Configure your TopstepX accounts in `config/accounts.yaml`
2. Start trading in paper mode first
3. Run backtests to validate strategies
4. Monitor performance in the Analytics page


