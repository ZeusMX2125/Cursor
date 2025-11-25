"""Application settings and configuration."""

import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Literal, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",  # Handle BOM characters (utf-8-sig strips BOM)
        case_sensitive=False,
        env_ignore_empty=True,  # Ignore empty values
    )

    # TopstepX API Credentials (ProjectX Gateway API)
    # Required for login_key mode (standard auth)
    topstepx_username: Optional[str] = None
    topstepx_api_key: Optional[str] = None
    topstepx_base_url: str = "https://api.topstepx.com/api"
    
    @field_validator("topstepx_base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that the base URL is correct."""
        if "gateway.projectx.com" in v.lower():
            raise ValueError(
                f"Invalid TOPSTEPX_BASE_URL: {v}\n"
                "The correct URL should be: https://api.topstepx.com/api\n"
                "Please check your .env file and update TOPSTEPX_BASE_URL."
            )
        if not v.startswith("https://api.topstepx.com"):
            import warnings
            warnings.warn(
                f"TOPSTEPX_BASE_URL is set to {v}, "
                "but the correct URL should be: https://api.topstepx.com/api"
            )
        return v
    topstepx_auth_mode: Literal["login_key", "login_app"] = "login_key"
    
    # Optional: loginApp mode credentials (rarely needed - most users use login_key)
    topstepx_app_username: Optional[str] = None
    topstepx_app_password: Optional[str] = None
    topstepx_app_id: Optional[str] = None
    topstepx_app_verify_key: Optional[str] = None
    topstepx_app_device_id: Optional[str] = "algox-client"
    
    topstepx_validate_tokens: bool = True
    
    def validate_credentials(self) -> None:
        """Validate that required credentials are present based on auth mode."""
        auth_mode = self.topstepx_auth_mode.lower()
        
        if auth_mode == "login_app":
            missing = []
            if not self.topstepx_app_username:
                missing.append("TOPSTEPX_APP_USERNAME")
            if not self.topstepx_app_password:
                missing.append("TOPSTEPX_APP_PASSWORD")
            if not self.topstepx_app_id:
                missing.append("TOPSTEPX_APP_ID")
            if not self.topstepx_app_verify_key:
                missing.append("TOPSTEPX_APP_VERIFY_KEY")
            
            if missing:
                raise ValueError(
                    f"Auth mode 'login_app' requires: {', '.join(missing)}. "
                    "Check your backend/.env file."
                )
        else:  # login_key (default)
            missing = []
            if not self.topstepx_username:
                missing.append("TOPSTEPX_USERNAME")
            if not self.topstepx_api_key:
                missing.append("TOPSTEPX_API_KEY")
            
            if missing:
                raise ValueError(
                    f"Auth mode 'login_key' requires: {', '.join(missing)}. "
                    "Get your API key from https://app.topstepx.com (Settings → API Access). "
                    "Then add to backend/.env file."
                )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/topstepx_bot"
    redis_url: str = "redis://localhost:6379/0"

    # Trading Configuration
    account_size: int = 50000  # $50K Combine
    profit_target: float = 3000.0  # $3K profit target
    daily_loss_limit: float = 1000.0  # $1K daily loss limit
    max_drawdown_limit: float = 2000.0  # $2K trailing max drawdown
    consistency_threshold: float = 0.5  # Best day < 50% of total profit

    # Trading Symbols
    symbols: List[str] = ["MNQ", "MES", "MGC"]

    # Risk Management
    risk_per_trade_percent: float = 1.5  # 1.5% risk per trade
    max_position_size: int = 5  # Max contracts per position
    min_position_size: int = 1

    # Strategy Configuration
    default_strategy: str = "ict_silver_bullet"
    enable_long_entries: bool = True
    enable_short_entries: bool = True

    # Time Management
    timezone: str = "America/Chicago"
    hard_close_time: str = "15:05"  # 3:05 PM CT
    trading_start_time: str = "17:00"  # 5:00 PM CT (previous day)

    # API Rate Limits
    historical_data_rate_limit: int = 50  # requests per 30 seconds
    general_rate_limit: int = 200  # requests per 60 seconds

    # WebSocket
    websocket_reconnect_delay: int = 1  # Initial delay in seconds
    websocket_max_reconnect_delay: int = 60  # Max delay in seconds
    websocket_heartbeat_interval: int = 30  # Heartbeat every 30 seconds

    # Logging
    log_level: str = "INFO"
    log_rotation: str = "10 MB"
    log_retention: str = "30 days"

    # Backtesting
    backtest_slippage_per_contract: float = 0.50  # $0.50 slippage
    backtest_commission_per_contract: float = 0.85  # $0.85 commission

    # ML/AI
    ml_enabled: bool = False  # Start with rule-based, enable ML later
    ml_model_path: str = "models/"

    # Paper Trading
    paper_trading_mode: bool = True  # Start in paper trading mode
    
    # Alerting
    alert_email_enabled: bool = False
    alert_email_smtp_host: str = "smtp.gmail.com"
    alert_email_smtp_port: int = 587
    alert_email_username: str = ""
    alert_email_password: str = ""
    alert_email_to: str = ""
    alert_sms_enabled: bool = False  # SMS requires external service (Twilio, etc.)

