"""Reinforcement Learning agent for adaptive trading."""

from typing import Dict, Optional
import os
import numpy as np
from loguru import logger

try:
    from stable_baselines3 import PPO
except ImportError:
    logger.warning("stable-baselines3 not installed. RL features will be disabled.")
    PPO = None

class RLAgent:
    """
    Reinforcement Learning agent using PPO.
    """

    def __init__(self, model_path: Optional[str] = "models/rl_agent_ppo.zip"):
        self.model = None
        self.model_path = model_path
        self.enabled = False

    def load_model(self) -> None:
        """Load trained PPO model."""
        if PPO is None:
            return

        if not self.model_path or not os.path.exists(self.model_path):
            logger.info("No RL model found. RL Agent disabled.")
            return

        try:
            self.model = PPO.load(self.model_path)
            self.enabled = True
            logger.info(f"RL Agent loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading RL model: {e}", exc_info=True)

    def get_action(self, observation: np.ndarray) -> Dict:
        """
        Get action from RL agent.
        
        Args:
            observation: Numpy array representing the state.
            
        Returns:
            Dictionary with action details.
        """
        if not self.enabled or self.model is None:
            return self._default_action()

        try:
            action, _states = self.model.predict(observation, deterministic=True)
            
            # Interpret discrete action
            # 0: Hold, 1: Buy, 2: Sell, 3: Close
            action_type = int(action)
            
            return {
                "action_type": action_type,
                "position_size": 1, # Fixed for discrete, could be continuous
                "raw_action": action
            }

        except Exception as e:
            logger.error(f"Error getting RL action: {e}", exc_info=True)
            return self._default_action()

    def _default_action(self) -> Dict:
        return {
            "action_type": 0, # Hold
            "position_size": 0,
            "raw_action": 0
        }
