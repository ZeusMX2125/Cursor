# Multi-Account Setup Guide

## Overview

The TopstepX trading bot now supports managing multiple Topstep accounts simultaneously, each with its own:
- Strategy configuration
- AI agent type (rule-based, ML confirmation, RL agent)
- Risk profile (account size: $50K, $100K, $150K)
- Paper trading or live trading mode

## Account Configuration

### 1. Create Accounts Configuration File

Copy the example file:
```bash
cp config/accounts.yaml.example config/accounts.yaml
```

### 2. Configure Your Accounts

Edit `config/accounts.yaml` with your account details:

```yaml
accounts:
  # Practice Account
  - account_id: practice_50k
    name: Practice $50K
    stage: practice
    size: 50k
    username: your_username
    api_key: your_api_key
    enabled_strategies:
      - ict_silver_bullet
      - vwap_mean_reversion
    ai_agent_type: rule_based
    paper_trading: true
    enabled: true

  # $50K Combine Account
  - account_id: combine_50k_1
    name: $50K Combine #1
    stage: combine
    size: 50k
    username: your_username
    api_key: your_api_key
    enabled_strategies:
      - ict_silver_bullet
      - trend_following
    ai_agent_type: ml_confirmation
    paper_trading: false
    enabled: true
```

### 3. Account Sizes and Profiles

The system automatically applies the correct risk profile based on account size:

#### $50K Account
- Profit Target: $3,000
- Daily Loss Limit: $1,000
- Max Drawdown: $2,000
- Scaling Plan: 2-5 contracts

#### $100K Account
- Profit Target: $6,000
- Daily Loss Limit: $2,000
- Max Drawdown: $3,000
- Scaling Plan: 3-6 contracts

#### $150K Account
- Profit Target: $9,000
- Daily Loss Limit: $3,000
- Max Drawdown: $4,500
- Scaling Plan: 4-7 contracts

### 4. AI Agent Types

- **rule_based**: Traditional rule-based strategies (default)
- **ml_confirmation**: ML model validates signals before execution
- **rl_agent**: Reinforcement learning agent controls position sizing and exits

### 5. Available Strategies

- `ict_silver_bullet`: ICT Silver Bullet (9-10 AM CT window)
- `vwap_mean_reversion`: VWAP mean reversion scalping
- `opening_range_breakout`: ORB (8:30-8:45 AM CT)
- `trend_following`: EMA-based trend following

## API Endpoints

### Get All Accounts
```bash
GET /api/accounts
```

### Get Account Status
```bash
GET /api/accounts/{account_id}
```

### Start Account
```bash
POST /api/accounts/{account_id}/start
```

### Stop Account
```bash
POST /api/accounts/{account_id}/stop
```

### Start All Accounts
```bash
POST /api/accounts/start-all
```

### Stop All Accounts
```bash
POST /api/accounts/stop-all
```

## Deep Backtesting

### Run Backtest via API

```bash
POST /api/backtest/run
{
  "account_ids": ["combine_50k_1"],
  "symbols": ["MNQ", "MES", "MGC"],
  "timeframe": "5m",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

### Backtest Features

- Fetches historical data directly from ProjectX API
- Respects rate limits (50 req/30s)
- Caches data locally for repeated runs
- Simulates Topstep rules (DLL, MLL, consistency)
- Generates comprehensive performance reports

## Frontend Usage

1. **Account Selection**: Use the account selector in Bot Config or Analytics pages
2. **Multi-Account Dashboard**: View status of all accounts
3. **Backtesting**: Run deep backtests from the Analytics page

## Best Practices

1. **Practice Accounts**: Use practice accounts to test new strategies
2. **Account Isolation**: Each account runs independently with its own risk manager
3. **Strategy Assignment**: Assign different strategies to different accounts for diversification
4. **AI Agent Testing**: Use practice accounts to test ML/RL agents before deploying to live accounts

## Troubleshooting

- **Account not starting**: Check API credentials in accounts.yaml
- **Backtest fails**: Verify date range and symbol availability
- **Rate limit errors**: The system automatically handles rate limiting, but large backtests may take time

