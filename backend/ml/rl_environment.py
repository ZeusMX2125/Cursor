"""Reinforcement Learning Environment for Trading."""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

from ml.feature_engineering import FeatureEngineer

class TradingEnvironment(gym.Env):
    """
    Custom Environment that follows gym interface.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, df: pd.DataFrame, initial_balance: float = 50000.0):
        super(TradingEnvironment, self).__init__()

        self.df = df
        self.initial_balance = initial_balance
        self.current_step = 0
        
        # Actions:
        # 0: Hold/Do Nothing
        # 1: Buy
        # 2: Sell (Close Position)
        # 3: Short
        # Alternatively, discrete action space for position sizing?
        # Let's start simple: [Action Type, Size Fraction]
        # But PPO handles continuous well or discrete.
        # Simple discrete: 0=Hold, 1=Buy (1 contract), 2=Sell (1 contract), 3=Close All
        self.action_space = spaces.Discrete(4)

        # Observation Space:
        # Market Features (Price, Indicators) + Account State (Balance, Position Size, Unrealized PnL)
        # Let's say we have 20 market features + 3 account features = 23
        # We need to determine feature count dynamically or fixed
        
        feature_cols = [c for c in df.columns if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        self.market_features_count = len(feature_cols)
        self.account_features_count = 3
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(self.market_features_count + self.account_features_count,), 
            dtype=np.float32
        )
        
        self.balance = initial_balance
        self.position = 0 # Number of contracts
        self.entry_price = 0.0
        self.total_pnl = 0.0
        self.feature_cols = feature_cols

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0.0
        self.total_pnl = 0.0
        self.current_step = 0 # Could start at random index for training
        
        return self._next_observation(), {}

    def _next_observation(self):
        # Get market features
        market_obs = self.df.iloc[self.current_step][self.feature_cols].values.astype(np.float32)
        
        # Account state
        unrealized_pnl = 0.0
        if self.position != 0:
            current_price = self.df.iloc[self.current_step]['close']
            unrealized_pnl = (current_price - self.entry_price) * self.position
            # Multiplier for futures? Assuming 1:1 for now or handled in reward
            
        account_obs = np.array([
            self.balance,
            self.position,
            unrealized_pnl
        ], dtype=np.float32)
        
        return np.concatenate((market_obs, account_obs))

    def step(self, action):
        # Execute one time step within the environment
        current_price = self.df.iloc[self.current_step]['close']
        
        reward = 0
        terminated = False
        truncated = False
        
        # Action logic
        if action == 1: # Buy
            if self.position <= 0: # Open Long or Reverse Short
                if self.position < 0:
                    # Close short
                    pnl = (self.entry_price - current_price) * abs(self.position)
                    self.balance += pnl
                    self.total_pnl += pnl
                    reward += pnl # Reward for closing profitable trade?
                
                self.position = 1
                self.entry_price = current_price
                
        elif action == 2: # Sell (Short or Close Long)
             if self.position >= 0:
                if self.position > 0:
                    # Close long
                    pnl = (current_price - self.entry_price) * self.position
                    self.balance += pnl
                    self.total_pnl += pnl
                    reward += pnl
                
                self.position = -1
                self.entry_price = current_price
                
        elif action == 3: # Close All
            if self.position != 0:
                pnl = 0
                if self.position > 0:
                    pnl = (current_price - self.entry_price) * self.position
                else:
                    pnl = (self.entry_price - current_price) * abs(self.position)
                
                self.balance += pnl
                self.total_pnl += pnl
                reward += pnl
                self.position = 0
                self.entry_price = 0
        
        # Calculate reward
        # Reward can be: Change in Portfolio Value (Realized + Unrealized)
        # Or Sharpe Ratio over window
        
        # Simple step reward: Change in Net Worth
        # net_worth = self.balance + unrealized_pnl
        # reward = net_worth - prev_net_worth
        
        self.current_step += 1
        
        if self.current_step >= len(self.df) - 1:
            terminated = True
            
        obs = self._next_observation()
        
        return obs, reward, terminated, truncated, {}

    def render(self, mode='human', close=False):
        print(f'Step: {self.current_step}, Balance: {self.balance}, Position: {self.position}')

