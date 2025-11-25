"""Training script for RL Agent."""

import os
import pandas as pd
import numpy as np
from loguru import logger

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
except ImportError:
    logger.error("stable-baselines3 not installed.")
    exit(1)

from ml.rl_environment import TradingEnvironment
from ml.feature_engineering import FeatureEngineer

class RLTrainer:
    """Trains the PPO agent."""

    def __init__(self, data_path: str = "data/historical/candles_1m.csv", model_output: str = "models/rl_agent_ppo"):
        self.data_path = data_path
        self.model_output = model_output

    def load_data(self) -> pd.DataFrame:
        """Load and preprocess market data."""
        if not os.path.exists(self.data_path):
            logger.warning("Data file not found. Creating dummy data.")
            return self._create_dummy_data()
            
        df = pd.read_csv(self.data_path)
        # Calculate indicators
        df = FeatureEngineer.calculate_indicators(pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df) # Polars vs Pandas mix? FeatureEngineer expects Polars
        
        # Let's assume FeatureEngineer can handle conversion or we convert here
        # Actually FeatureEngineer expects Polars DataFrame.
        import polars as pl
        df_pl = pl.from_pandas(df)
        df_pl = FeatureEngineer.calculate_indicators(df_pl)
        return df_pl.to_pandas() # Convert back for Gym

    def _create_dummy_data(self) -> pd.DataFrame:
        # Create dummy OHLCV
        dates = pd.date_range(start="2023-01-01", periods=1000, freq="1min")
        data = {
            "timestamp": dates,
            "open": np.random.uniform(4000, 4100, 1000),
            "high": np.random.uniform(4100, 4200, 1000),
            "low": np.random.uniform(3900, 4000, 1000),
            "close": np.random.uniform(4000, 4100, 1000),
            "volume": np.random.uniform(100, 1000, 1000)
        }
        # Calculate indicators
        import polars as pl
        df_pl = pl.DataFrame(data)
        df_pl = FeatureEngineer.calculate_indicators(df_pl)
        return df_pl.to_pandas()

    def train(self, total_timesteps=10000):
        df = self.load_data()
        
        # Create environment
        env = TradingEnvironment(df)
        env = DummyVecEnv([lambda: env]) # Vectorized env

        # Initialize Agent
        model = PPO("MlpPolicy", env, verbose=1)
        
        logger.info("Starting RL training...")
        model.learn(total_timesteps=total_timesteps)
        
        # Save
        os.makedirs(os.path.dirname(self.model_output), exist_ok=True)
        model.save(self.model_output)
        logger.info(f"RL model saved to {self.model_output}")

if __name__ == "__main__":
    trainer = RLTrainer()
    trainer.train()

