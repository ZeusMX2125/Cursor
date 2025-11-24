# TopstepX Trading Bot - Setup Guide

## Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ with TimescaleDB extension
- Docker & Docker Compose (optional but recommended)
- TopstepX API credentials

## Quick Start

### 1. Multi-Account Setup (Recommended)

First, configure your accounts:
```bash
cp config/accounts.yaml.example config/accounts.yaml
# Edit config/accounts.yaml with your account details
```

See [MULTI_ACCOUNT_SETUP.md](MULTI_ACCOUNT_SETUP.md) for detailed instructions.

### 2. Clone and Setup

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

### 2. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp config/.env.example config/.env
```

Edit `config/.env` with your TopstepX API credentials:
```
TOPSTEPX_USERNAME=your_username
TOPSTEPX_API_KEY=your_api_key
```

### 3. Database Setup

#### Option A: Using Docker (Recommended)

```bash
docker-compose up -d postgres redis
```

#### Option B: Manual Setup

1. Install PostgreSQL and TimescaleDB extension
2. Create database:
```sql
CREATE DATABASE topstepx_bot;
\c topstepx_bot
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### 4. Run the Application

#### Development Mode

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

#### Using Docker Compose

```bash
docker-compose up
```

### 5. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
├── backend/              # Python FastAPI backend
│   ├── api/             # TopstepX API integration
│   ├── core/            # Core trading engine
│   ├── strategies/      # Trading strategies
│   ├── risk/            # Risk management
│   ├── ml/              # Machine learning components
│   ├── backtesting/     # Backtesting engine
│   ├── monitoring/       # Performance tracking
│   └── main.py          # Main entry point
│
├── frontend/            # Next.js React frontend
│   ├── app/            # Next.js App Router pages
│   ├── components/     # React components
│   └── lib/            # Utilities
│
└── config/             # Configuration files
```

## Key Features

### Backend
- ✅ TopstepX API integration with rate limiting
- ✅ WebSocket real-time data handling
- ✅ 4 trading strategies (ICT, VWAP, ORB, Trend Following)
- ✅ Comprehensive risk management (DLL, MLL, consistency)
- ✅ Backtesting framework
- ✅ ML components (feature engineering, signal validation)
- ✅ Paper trading mode

### Frontend
- ✅ Dashboard with real-time stats
- ✅ Price charts
- ✅ Order entry panel
- ✅ Active positions table
- ✅ Bot configuration UI
- ✅ Real-time WebSocket updates

## Trading Strategies

1. **ICT Silver Bullet** - 9-10 AM CT window, liquidity sweep + FVG detection
2. **VWAP Mean Reversion** - Pullback to VWAP with RSI confirmation
3. **Opening Range Breakout** - 8:30-8:45 AM CT range breakout
4. **Trend Following** - EMA alignment with pullback entries

## Risk Management

- Daily Loss Limit: $1,000 (hard stop at $950)
- Trailing Max Drawdown: $2,000
- Consistency Rule: Best day < 50% of total profit
- Position sizing: 1.5% risk per trade
- Hard close: 3:05 PM CT

## Paper Trading

The bot starts in paper trading mode by default. Set `PAPER_TRADING_MODE=false` in `.env` for live trading.

## Testing

```bash
cd backend
pytest
```

## Deployment

See the master plan document for detailed deployment instructions. Remember:
- Must run on personal device (TopstepX requirement)
- No VPS/VPN allowed
- Monitor continuously for rule compliance

## Support

Refer to the master plan document (`topstepx-trading-bot-master-plan.plan.md`) for detailed architecture and implementation details.

