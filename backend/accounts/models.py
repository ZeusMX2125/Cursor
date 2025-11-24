"""Account models and configuration."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AccountStage(str, Enum):
    """Topstep account stage."""

    PRACTICE = "practice"
    COMBINE = "combine"
    EXPRESS_FUNDED = "express_funded"
    LIVE_FUNDED = "live_funded"


class AccountSize(str, Enum):
    """Topstep account size."""

    SIZE_50K = "50k"
    SIZE_100K = "100k"
    SIZE_150K = "150k"


class AccountProfile(BaseModel):
    """Account risk profile with Topstep rules."""

    account_size: int
    profit_target: float
    daily_loss_limit: float
    max_drawdown_limit: float
    consistency_threshold: float = 0.5
    scaling_plan: Dict[str, int] = Field(
        default_factory=dict,
        description="Balance thresholds to max contracts mapping",
    )


class AccountConfig(BaseModel):
    """Configuration for a Topstep account."""

    account_id: str
    name: str
    stage: AccountStage
    size: AccountSize
    username: Optional[str] = None
    api_key: Optional[str] = None
    profile: AccountProfile
    enabled_strategies: List[str] = Field(default_factory=list)
    ai_agent_type: str = "rule_based"  # rule_based, ml_confirmation, rl_agent
    paper_trading: bool = True
    enabled: bool = True


# Account size profiles
ACCOUNT_PROFILES: Dict[AccountSize, AccountProfile] = {
    AccountSize.SIZE_50K: AccountProfile(
        account_size=50000,
        profit_target=3000.0,
        daily_loss_limit=1000.0,
        max_drawdown_limit=2000.0,
        consistency_threshold=0.5,
        scaling_plan={
            "0-1500": 2,
            "1500-3000": 3,
            "3000-5000": 4,
            "5000+": 5,
        },
    ),
    AccountSize.SIZE_100K: AccountProfile(
        account_size=100000,
        profit_target=6000.0,
        daily_loss_limit=2000.0,
        max_drawdown_limit=3000.0,
        consistency_threshold=0.5,
        scaling_plan={
            "0-3000": 3,
            "3000-6000": 4,
            "6000-10000": 5,
            "10000+": 6,
        },
    ),
    AccountSize.SIZE_150K: AccountProfile(
        account_size=150000,
        profit_target=9000.0,
        daily_loss_limit=3000.0,
        max_drawdown_limit=4500.0,
        consistency_threshold=0.5,
        scaling_plan={
            "0-4500": 4,
            "4500-9000": 5,
            "9000-15000": 6,
            "15000+": 7,
        },
    ),
}


def get_account_profile(size: AccountSize) -> AccountProfile:
    """Get account profile for a given size."""
    return ACCOUNT_PROFILES.get(size, ACCOUNT_PROFILES[AccountSize.SIZE_50K])

