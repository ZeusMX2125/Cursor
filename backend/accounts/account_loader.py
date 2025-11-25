"""Load account configurations from YAML file."""

import yaml
from pathlib import Path
from typing import Dict, Iterable

from loguru import logger

from accounts.models import (
    AccountConfig,
    AccountStage,
    AccountSize,
    get_account_profile,
)


def _resolve_config_file(config_path: str) -> Path:
    """Resolve the accounts config file across multiple possible locations."""
    candidate_paths: Iterable[Path] = []
    raw_path = Path(config_path)

    if raw_path.is_absolute():
        candidate_paths = [raw_path]
    else:
        project_root = Path(__file__).resolve().parents[2]
        candidate_paths = [
            raw_path,
            Path.cwd() / raw_path,
            project_root / raw_path,
        ]

    for candidate in candidate_paths:
        normalized = candidate.resolve()
        if normalized.exists():
            return normalized

    raise FileNotFoundError(
        f"Account configuration not found. Create {config_path} (e.g. copy config/accounts.yaml.example)."
    )


async def load_accounts(config_path: str = "config/accounts.yaml") -> Dict[str, AccountConfig]:
    """Load accounts from YAML configuration file."""
    try:
        config_file = _resolve_config_file(config_path)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        raise

    try:
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)

        accounts = {}
        for account_data in data.get("accounts", []):
            account_id = account_data["account_id"]
            stage = AccountStage(account_data["stage"])
            size = AccountSize(account_data["size"])

            # Get profile for account size
            profile = get_account_profile(size)

            # Override profile if custom values provided
            if "profile" in account_data:
                profile_dict = account_data["profile"]
                profile.account_size = profile_dict.get("account_size", profile.account_size)
                profile.profit_target = profile_dict.get("profit_target", profile.profit_target)
                profile.daily_loss_limit = profile_dict.get("daily_loss_limit", profile.daily_loss_limit)
                profile.max_drawdown_limit = profile_dict.get("max_drawdown_limit", profile.max_drawdown_limit)

            account_config = AccountConfig(
                account_id=account_id,
                name=account_data.get("name", account_id),
                stage=stage,
                size=size,
                username=account_data.get("username"),
                api_key=account_data.get("api_key"),
                profile=profile,
                enabled_strategies=account_data.get("enabled_strategies", []),
                ai_agent_type=account_data.get("ai_agent_type", "rule_based"),
                paper_trading=account_data.get("paper_trading", True),
                enabled=account_data.get("enabled", True),
            )

            accounts[account_id] = account_config

        logger.info(f"Loaded {len(accounts)} accounts from {config_path}")
        return accounts

    except Exception as e:
        logger.error(f"Error loading accounts: {e}", exc_info=True)
        return _create_default_accounts()


def _create_default_accounts() -> Dict[str, AccountConfig]:
    """Create default account configuration."""
    from accounts.models import AccountProfile

    # Default $50K Combine account
    default_profile = get_account_profile(AccountSize.SIZE_50K)

    default_account = AccountConfig(
        account_id="default_50k",
        name="Default $50K Combine",
        stage=AccountStage.COMBINE,
        size=AccountSize.SIZE_50K,
        profile=default_profile,
        enabled_strategies=["ict_silver_bullet", "vwap_mean_reversion"],
        ai_agent_type="rule_based",
        paper_trading=True,
        enabled=True,
    )

    return {"default_50k": default_account}


async def add_account_to_config(
    account_data: dict,
    config_path: str = "config/accounts.yaml"
) -> bool:
    """Add or update an account in the YAML configuration file."""
    import yaml
    from pathlib import Path
    
    try:
        config_file = _resolve_config_file(config_path)
    except FileNotFoundError:
        # File doesn't exist, create it
        project_root = Path(__file__).resolve().parents[2]
        config_file = project_root / config_path
        config_file.parent.mkdir(parents=True, exist_ok=True)
        # Create initial structure
        with open(config_file, "w") as f:
            yaml.dump({"accounts": []}, f, default_flow_style=False, sort_keys=False)
    
    # Read existing data
    with open(config_file, "r") as f:
        data = yaml.safe_load(f) or {}
    
    if "accounts" not in data:
        data["accounts"] = []
    
    # Check if account already exists
    account_id = account_data.get("account_id")
    existing_index = None
    for i, acc in enumerate(data["accounts"]):
        if acc.get("account_id") == account_id:
            existing_index = i
            break
    
    # Prepare account entry (only include username/api_key if provided)
    account_entry = {
        "account_id": account_data["account_id"],
        "name": account_data["name"],
        "stage": account_data["stage"],
        "size": account_data["size"],
        "enabled_strategies": account_data.get("enabled_strategies", ["ict_silver_bullet"]),
        "ai_agent_type": account_data.get("ai_agent_type", "rule_based"),
        "paper_trading": account_data.get("paper_trading", True),
        "enabled": account_data.get("enabled", True),
    }
    
    # Only add username/api_key if they're provided
    if account_data.get("username"):
        account_entry["username"] = account_data["username"]
    if account_data.get("api_key"):
        account_entry["api_key"] = account_data["api_key"]
    
    # Update or add account
    if existing_index is not None:
        data["accounts"][existing_index] = account_entry
        logger.info(f"Updated account {account_id} in {config_path}")
    else:
        data["accounts"].append(account_entry)
        logger.info(f"Added account {account_id} to {config_path}")
    
    # Write back to file
    with open(config_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    return True
