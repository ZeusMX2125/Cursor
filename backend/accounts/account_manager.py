"""Account manager for orchestrating multiple trading bots."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from accounts.models import AccountConfig, AccountProfile, get_account_profile
from accounts.account_loader import load_accounts
from main import TradingBot
from config.settings import Settings


class AccountManager:
    """Manages multiple Topstep accounts with separate trading bots."""

    def __init__(self, base_settings: Settings):
        self.base_settings = base_settings
        self.accounts: Dict[str, AccountConfig] = {}
        self.bots: Dict[str, TradingBot] = {}
        self.running = False
        self.manual_orders: Dict[str, List[Dict]] = defaultdict(list)
        self.active_strategies: Dict[str, Optional[str]] = {}
        self.bot_activity: Dict[str, List[Dict]] = defaultdict(list)  # Activity log per account
        self._manual_orders_lock = asyncio.Lock()
        self._activity_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize account manager and load accounts."""
        logger.info("Initializing account manager...")

        # Load accounts from configuration
        self.accounts = await load_accounts()

        logger.info(f"Loaded {len(self.accounts)} accounts")

    async def start_all(self) -> None:
        """Start all enabled accounts."""
        self.running = True

        for account_id, account_config in self.accounts.items():
            if not account_config.enabled:
                logger.info(f"Skipping disabled account: {account_id}")
                continue

            try:
                await self.start_account(account_id)
            except Exception as e:
                logger.error(
                    f"Error starting account {account_id}: {e}", exc_info=True
                )

    async def stop_all(self) -> None:
        """Stop all running accounts."""
        self.running = False

        for account_id in list(self.bots.keys()):
            try:
                await self.stop_account(account_id)
            except Exception as e:
                logger.error(
                    f"Error stopping account {account_id}: {e}", exc_info=True
            )

    async def start_account(self, account_id: str) -> None:
        """Start trading bot for a specific account."""
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")

        account_config = self.accounts[account_id]

        if account_id in self.bots:
            logger.warning(f"Account {account_id} already running")
            return

        logger.info(f"Starting account: {account_id} ({account_config.name})")

        # Create account-specific settings
        account_settings = self._create_account_settings(account_config)

        async def activity_logger(activity: Dict[str, Any]):
            await self._log_activity(account_id, activity)

        # Create bot (initialization happens in __init__)
        bot = TradingBot(account_settings, account_config, activity_logger=activity_logger)

        # Start bot in background with error handling
        async def start_bot_with_error_handling():
            """Start bot with proper error handling to ensure it persists."""
            try:
                await bot.start()
            except Exception as e:
                logger.error(
                    f"Bot for account {account_id} encountered an error: {e}",
                    exc_info=True
                )
                # Don't remove from bots dict - keep it so it can be restarted
                # The bot's running flag will be False, but it stays in memory
        
        # Create and store the task
        task = asyncio.create_task(start_bot_with_error_handling())
        bot._task = task  # Store task reference in bot for potential cleanup

        self.bots[account_id] = bot
        logger.info(f"Account {account_id} started (running in background)")
        
        # Log bot start activity
        asyncio.create_task(self._log_activity(account_id, {
            "type": "bot_started",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Bot started for account {account_id}",
            "strategies": account_config.enabled_strategies,
        }))

    async def stop_account(self, account_id: str) -> None:
        """Stop trading bot for a specific account."""
        if account_id not in self.bots:
            logger.warning(f"Account {account_id} not running")
            return

        logger.info(f"Stopping account: {account_id}")

        bot = self.bots[account_id]
        await bot.stop()

        del self.bots[account_id]
        logger.info(f"Account {account_id} stopped")
        
        # Log bot stop activity
        asyncio.create_task(self._log_activity(account_id, {
            "type": "bot_stopped",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Bot stopped for account {account_id}",
        }))

    def _create_account_settings(self, account_config: AccountConfig) -> Settings:
        """Create Settings instance for an account."""
        # Create a copy of base settings
        account_settings = Settings(
            topstepx_username=account_config.username
            or self.base_settings.topstepx_username,
            topstepx_api_key=account_config.api_key
            or self.base_settings.topstepx_api_key,
            topstepx_base_url=self.base_settings.topstepx_base_url,
            database_url=self.base_settings.database_url,
            redis_url=self.base_settings.redis_url,
            # Account-specific settings
            account_size=account_config.profile.account_size,
            profit_target=account_config.profile.profit_target,
            daily_loss_limit=account_config.profile.daily_loss_limit,
            max_drawdown_limit=account_config.profile.max_drawdown_limit,
            consistency_threshold=account_config.profile.consistency_threshold,
            symbols=self.base_settings.symbols,
            risk_per_trade_percent=self.base_settings.risk_per_trade_percent,
            max_position_size=self._get_max_position_size(account_config.profile),
            min_position_size=self.base_settings.min_position_size,
            default_strategy=account_config.enabled_strategies[0]
            if account_config.enabled_strategies
            else self.base_settings.default_strategy,
            enable_long_entries=self.base_settings.enable_long_entries,
            enable_short_entries=self.base_settings.enable_short_entries,
            timezone=self.base_settings.timezone,
            hard_close_time=self.base_settings.hard_close_time,
            trading_start_time=self.base_settings.trading_start_time,
            historical_data_rate_limit=self.base_settings.historical_data_rate_limit,
            general_rate_limit=self.base_settings.general_rate_limit,
            websocket_reconnect_delay=self.base_settings.websocket_reconnect_delay,
            websocket_max_reconnect_delay=self.base_settings.websocket_max_reconnect_delay,
            websocket_heartbeat_interval=self.base_settings.websocket_heartbeat_interval,
            log_level=self.base_settings.log_level,
            log_rotation=self.base_settings.log_rotation,
            log_retention=self.base_settings.log_retention,
            backtest_slippage_per_contract=self.base_settings.backtest_slippage_per_contract,
            backtest_commission_per_contract=self.base_settings.backtest_commission_per_contract,
            ml_enabled=(account_config.ai_agent_type != "rule_based"),
            ml_model_path=self.base_settings.ml_model_path,
            paper_trading_mode=account_config.paper_trading,
        )

        return account_settings

    def _get_max_position_size(self, profile: AccountProfile) -> int:
        """Get max position size from scaling plan."""
        max_contracts = max(profile.scaling_plan.values()) if profile.scaling_plan else 5
        return max_contracts

    def get_account_status(self, account_id: str) -> Optional[Dict]:
        """Get status for an account."""
        if account_id not in self.accounts:
            return None

        account_config = self.accounts[account_id]
        bot = self.bots.get(account_id)

        return {
            "account_id": account_id,
            "name": account_config.name,
            "stage": account_config.stage.value,
            "size": account_config.size.value,
            "running": bot is not None and bot.running if bot else False,
            "paper_trading": account_config.paper_trading,
            "enabled": account_config.enabled,
            "account_size": account_config.profile.account_size,
            "daily_loss_limit": account_config.profile.daily_loss_limit,
            "profit_target": account_config.profile.profit_target,
        }

    def get_all_accounts_status(self) -> List[Dict]:
        """Get status for all accounts."""
        statuses: List[Dict] = []
        for account_id in self.accounts.keys():
            status = self.get_account_status(account_id)
            if status:
                statuses.append(status)
        return statuses

    async def get_account_snapshot(self, account_id: str) -> Dict:
        """Get detailed snapshot for dashboard consumption."""
        status = self.get_account_status(account_id)
        if not status:
            raise ValueError(f"Account {account_id} not found")

        account_config = self.accounts[account_id]
        bot = self.bots.get(account_id)

        metrics = {
            "daily_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "trades_today": 0,
            "total_trades": 0,
        }

        if bot and bot.performance_tracker:
            tracker_metrics = bot.performance_tracker.get_metrics()
            metrics.update(
                {
                    "daily_pnl": tracker_metrics.get("daily_pnl", 0.0),
                    "win_rate": tracker_metrics.get("win_rate", 0.0),
                    "profit_factor": tracker_metrics.get("profit_factor", 0.0),
                    "trades_today": tracker_metrics.get("trades_today", 0),
                    "total_trades": tracker_metrics.get("total_trades", 0),
                }
            )

        positions: List[Dict] = []
        if bot and bot.position_tracker:
            positions = await bot.position_tracker.get_open_positions()

        pending_orders = self.get_pending_orders(account_id)
        manual_orders = await self.get_manual_orders(account_id)

        snapshot = {
            **status,
            "balance": account_config.profile.account_size + metrics["daily_pnl"],
            "buying_power": round(account_config.profile.account_size * 0.25, 2),
            "metrics": metrics,
            "positions": positions,
            "pending_orders": pending_orders,
            "manual_orders": manual_orders,
            "strategies": {
                "configured": account_config.enabled_strategies,
                "active": self.active_strategies.get(account_id),
                "agent": account_config.ai_agent_type,
            },
        }

        return snapshot

    async def get_all_snapshots(self) -> List[Dict]:
        """Get snapshot for all accounts concurrently."""
        tasks = [
            self.get_account_snapshot(account_id)
            for account_id in self.accounts.keys()
        ]
        if not tasks:
            return []
        return await asyncio.gather(*tasks)

    def _order_to_dict(self, order) -> Dict:
        """Convert internal Order object to serializable dict."""
        return {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "order_type": order.order_type,
            "quantity": order.quantity,
            "price": order.price,
            "stop_price": order.stop_price,
            "status": order.status,
            "filled_quantity": order.filled_quantity,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        }

    def get_pending_orders(self, account_id: str) -> List[Dict]:
        """Return pending orders for an account."""
        bot = self.bots.get(account_id)
        if not bot or not bot.order_manager:
            return []
        orders = bot.order_manager.get_all_orders()
        return [self._order_to_dict(order) for order in orders if order.status != "FILLED"]

    async def record_manual_order(self, account_id: str, order_data: Dict) -> None:
        """Persist manual order for auditing and UI."""
        async with self._manual_orders_lock:
            enriched = {
                **order_data,
                "timestamp": order_data.get("timestamp", datetime.utcnow().isoformat()),
            }
            self.manual_orders[account_id].insert(0, enriched)
            # trim history
            self.manual_orders[account_id] = self.manual_orders[account_id][:200]

    async def get_manual_orders(self, account_id: str) -> List[Dict]:
        """Return manual order history for account."""
        async with self._manual_orders_lock:
            return list(self.manual_orders.get(account_id, []))
    
    async def _log_activity(self, account_id: str, activity: Dict) -> None:
        """Log bot activity for an account."""
        async with self._activity_lock:
            activity = dict(activity)
            activity.setdefault("timestamp", datetime.utcnow().isoformat())
            self.bot_activity[account_id].insert(0, activity)
            # Keep only last 100 activities per account
            self.bot_activity[account_id] = self.bot_activity[account_id][:100]
    
    async def get_bot_activity(self, account_id: str, limit: int = 50) -> List[Dict]:
        """Get recent bot activity for an account."""
        async with self._activity_lock:
            activities = self.bot_activity.get(account_id, [])
            return activities[:limit]
    
    def get_bot_health(self, account_id: str) -> Dict:
        """Get bot health/verification info."""
        bot = self.bots.get(account_id)
        if not bot:
            return {
                "running": False,
                "verified": False,
                "message": "Bot not running",
            }
        
        # Check if bot is actually running
        is_running = bot.running if hasattr(bot, 'running') else False
        
        # Get recent activity count
        recent_activity = len(self.bot_activity.get(account_id, []))
        
        # Check if bot has active components
        has_components = {
            "api_client": hasattr(bot, 'api_client') and bot.api_client is not None,
            "order_manager": hasattr(bot, 'order_manager') and bot.order_manager is not None,
            "risk_manager": hasattr(bot, 'risk_manager') and bot.risk_manager is not None,
            "strategy_selector": hasattr(bot, 'strategy_selector') and bot.strategy_selector is not None,
        }
        
        return {
            "running": is_running,
            "verified": is_running and all(has_components.values()),
            "components": has_components,
            "recent_activity_count": recent_activity,
            "last_activity": self.bot_activity.get(account_id, [{}])[0] if self.bot_activity.get(account_id) else None,
            "message": "Bot is running and verified" if is_running and all(has_components.values()) else "Bot may not be fully operational",
        }

    def set_active_strategy(self, account_id: str, strategy_name: Optional[str]) -> None:
        """Track currently active quick strategy per account."""
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        self.active_strategies[account_id] = strategy_name

