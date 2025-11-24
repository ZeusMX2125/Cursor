"""
FastAPI application for TopstepX trading bot API.
"""

import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from loguru import logger

from config.settings import Settings
from accounts.account_manager import AccountManager
from accounts.account_loader import load_accounts
from backtesting.deep_backtester import DeepBacktester
from api.auth_manager import AuthManager
from api.projectx_service import ProjectXService
from api.topstepx_client import TopstepXClient
from api.websocket_handler import WebSocketHandler
from api.websocket_manager import websocket_manager

app = FastAPI(title="TopstepX Trading Bot API", version="1.0.0")

# Configure file logging so backend logs are saved for troubleshooting
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger.add(
    LOG_DIR / "backend_{time}.log",
    rotation="1 day",        # new file each day
    retention="7 days",      # keep last 7 days
    level="DEBUG",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

# CORS configuration - use only CORSMiddleware (no custom middleware)
ALLOWED_ORIGINS = ["http://localhost:3000"]  # explicit when credentials may be used

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,       # fine even if not used; origin cannot be "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

def _resolve_existing_path(candidates: List[str]) -> Optional[Path]:
    """Return the first existing path from the provided candidate list."""
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return None


def _require_config_files(settings: Settings) -> None:
    """Ensure required configuration files or environment variables are present."""
    missing: List[str] = []

    env_path = _resolve_existing_path(
        [".env", "../.env", "backend/.env"]
    )
    env_vars_present = os.getenv("TOPSTEPX_USERNAME") and os.getenv("TOPSTEPX_API_KEY")
    if not env_path and not env_vars_present:
        missing.append("backend/.env (or export TOPSTEPX_* environment variables)")

    # Credential validation based on auth mode
    auth_mode = settings.topstepx_auth_mode.lower()
    if auth_mode == "login_app":
        required_fields = {
            "TOPSTEPX_APP_USERNAME": settings.topstepx_app_username,
            "TOPSTEPX_APP_PASSWORD": settings.topstepx_app_password,
            "TOPSTEPX_APP_ID": settings.topstepx_app_id,
            "TOPSTEPX_APP_VERIFY_KEY": settings.topstepx_app_verify_key,
            "TOPSTEPX_APP_DEVICE_ID": settings.topstepx_app_device_id,
        }
    else:
        required_fields = {
            "TOPSTEPX_USERNAME": settings.topstepx_username,
            "TOPSTEPX_API_": settings.topstepx_api_key,
        }

    missing_creds = [name for name, value in required_fields.items() if not value]
    if missing_creds:
        missing.append(
            "Missing ProjectX credentials: "
            + ", ".join(missing_creds)
            + f" (auth mode: {auth_mode})"
        )

    accounts_path = _resolve_existing_path(
        ["config/accounts.yaml", "../config/accounts.yaml", "backend/../config/accounts.yaml"]
    )
    if not accounts_path:
        missing.append("config/accounts.yaml (copy from config/accounts.yaml.example)")

    if missing:
        raise RuntimeError(
            "Missing required configuration. Please create the following before starting the API: "
            + ", ".join(missing)
        )


try:
    settings = Settings()
except Exception as e:
    import sys
    print("\n" + "="*80)
    print("ERROR: Failed to load settings from .env file")
    print("="*80)
    print(f"\nError details: {e}")
    print("\nPlease check your .env file in the backend/ directory.")
    print("It should contain lines like:")
    print("  TOPSTEPX_USERNAME=your_username")
    print("  TOPSTEPX_API_KEY=your_api_key")
    print("\nMake sure:")
    print("  1. Each variable is on its own line")
    print("  2. No spaces around the = sign")
    print("  3. No special characters or BOM at the start of the file")
    print("  4. The file is saved as UTF-8 encoding")
    print("="*80 + "\n")
    sys.exit(1)
account_manager: Optional[AccountManager] = None
deep_backtester: Optional[DeepBacktester] = None
shared_auth_manager: Optional[AuthManager] = None
shared_market_client: Optional[TopstepXClient] = None
projectx_service: Optional[ProjectXService] = None
projectx_ws_handler: Optional[WebSocketHandler] = None
# Unified error handlers so even failures get JSON (CORS will be applied)
# Return JSON for *all* errors; CORSMiddleware will attach headers.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with CORS headers."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with CORS headers."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )

@app.exception_handler(Exception)
async def internal_exc_handler(request: Request, exc: Exception):
    """Handle all other exceptions with CORS headers."""
    logger.error(f"Unhandled error for request {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )


SUPPORTED_TIMEFRAMES = {"1m", "5m", "15m", "30m", "60m"}
MAX_CHART_BARS = 2000


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global account_manager, deep_backtester, shared_auth_manager, shared_market_client, projectx_service, projectx_ws_handler

    _require_config_files(settings)

    # Initialize account manager
    account_manager = AccountManager(settings)
    await account_manager.initialize()

    # Initialize backtester
    shared_auth_manager = AuthManager(settings)
    
    # Initialize authentication in background with timeout to avoid blocking startup
    async def initialize_auth():
        """Initialize authentication in background."""
        try:
            await shared_auth_manager.initialize()
            logger.info("Authentication manager initialized successfully")
        except Exception as exc:
            logger.error(
                f"Failed to initialize authentication during startup: {exc}",
                exc_info=True
            )
            logger.warning(
                "Server will start but API calls will fail until authentication is fixed. "
                f"Check your .env file and ensure TOPSTEPX_BASE_URL is set to: https://api.topstepx.com/api"
            )
    
    # Start authentication in background (non-blocking)
    asyncio.create_task(initialize_auth())
    
    deep_backtester = DeepBacktester(settings, shared_auth_manager)
    try:
        await deep_backtester.initialize()
    except Exception as exc:
        logger.warning(f"Backtester initialization failed (non-critical): {exc}")

    # Shared market data client for UI endpoints
    shared_market_client = TopstepXClient(settings, shared_auth_manager)
    
    # Initialize market client in background (non-blocking)
    async def initialize_market_client():
        """Initialize market client and verify authentication in background."""
        try:
            await shared_market_client.initialize()
            try:
                accounts = await shared_market_client.list_accounts()
                logger.info(
                    f"Authenticated with ProjectX API "
                    f"(accounts={len(accounts)}, base_url={settings.topstepx_base_url})"
                )
            except Exception as exc:
                logger.error(
                    "Unable to verify ProjectX credentials during startup. "
                    "API calls will fail until this is resolved.",
                    exc_info=True
                )
                logger.error(
                    f"Current TOPSTEPX_BASE_URL: {settings.topstepx_base_url}\n"
                    "Expected: https://api.topstepx.com/api\n"
                    "Please check your .env file in the backend/ directory."
                )
        except Exception as exc:
            logger.error(f"Failed to initialize market client: {exc}", exc_info=True)
    
    # Start market client initialization in background
    asyncio.create_task(initialize_market_client())
    
    # Create service immediately (it will wait for auth when needed)
    projectx_service = ProjectXService(shared_market_client)
    projectx_ws_handler = WebSocketHandler(
        settings, shared_auth_manager, shared_market_client
    )

    def _make_ws_forwarder(event_type: str):
        async def forward(payload: Dict):
            await websocket_manager.broadcast({"type": event_type, "payload": payload})

        return forward

    for event_name in (
        "account_update",
        "position_update",
        "order_update",
        "trade_update",
        "quote_update",
    ):
        projectx_ws_handler.register_callback(
            event_name, _make_ws_forwarder(event_name)
        )

    # Connect WebSocket handler in background (non-blocking)
    async def connect_ws_handler():
        """Connect WebSocket handler in background."""
        try:
            await projectx_ws_handler.connect()
            logger.info("ProjectX WebSocket handler connected")
        except Exception as exc:
            logger.warning(
                f"Failed to connect WebSocket handler (non-critical): {exc}",
                exc_info=True
            )
    
    # Start WebSocket connection in background to avoid blocking startup
    asyncio.create_task(connect_ws_handler())

    # Start background task for WebSocket broadcasting with proper error handling
    async def safe_broadcast_wrapper():
        """Wrapper that restarts broadcast task if it crashes."""
        while True:
            try:
                await broadcast_realtime_data()
            except Exception as e:
                logger.error(f"Background broadcast task crashed: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before restarting
                logger.info("Restarting background broadcast task...")
    
    # Start the safe wrapper task
    asyncio.create_task(safe_broadcast_wrapper())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global account_manager, shared_market_client, projectx_ws_handler

    if account_manager:
        await account_manager.stop_all()
    if shared_market_client:
        await shared_market_client.close()
    if projectx_ws_handler:
        await projectx_ws_handler.disconnect()



@app.get("/")
async def root():
    """Root endpoint."""
    logger.debug("Root endpoint accessed")
    return {
        "message": "TopstepX Trading Bot API",
        "status": "running",
        "services": {
            "projectx_service": projectx_service is not None,
            "auth_manager": shared_auth_manager is not None,
            "market_client": shared_market_client is not None,
        }
    }

@app.get("/api/test/cors")
async def test_cors():
    """Test endpoint to verify CORS is working."""
    return {
        "message": "CORS test successful",
        "timestamp": datetime.utcnow().isoformat(),
        "cors_configured": True
    }

# Canary routes to prove CORS is working (bypass ProjectX client)
@app.get("/api/cors-ok")
async def cors_ok():
    """Simple GET endpoint to test CORS headers."""
    return {"ok": True}

@app.post("/api/cors-ok")
async def cors_ok_post(payload: dict):
    """Simple POST endpoint to test CORS headers."""
    return {"received": payload}


@app.get("/health")
async def health():
    """Health check endpoint with diagnostic information."""
    auth_status = "unknown"
    auth_error = None
    if shared_auth_manager:
        try:
            token = await shared_auth_manager.get_token()
            auth_status = "authenticated" if token else "no_token"
        except Exception as e:
            auth_status = "failed"
            auth_error = str(e)
    else:
        auth_status = "not_initialized"
    
    return {
        "status": "healthy" if auth_status == "authenticated" else "degraded",
        "auth": {
            "status": auth_status,
            "error": auth_error,
            "base_url": settings.topstepx_base_url,
            "auth_mode": settings.topstepx_auth_mode,
        },
        "services": {
            "account_manager": account_manager is not None,
            "market_client": shared_market_client is not None,
            "projectx_service": projectx_service is not None,
            "websocket_handler": projectx_ws_handler is not None,
        }
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming to frontend."""
    origin = websocket.headers.get("origin")
    # Allow connections from frontend origins
    if origin and origin not in ALLOWED_ORIGINS:
        logger.warning(f"WebSocket connection rejected from origin: {origin}")
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    
    try:
        await websocket_manager.connect(websocket)
        logger.info(f"WebSocket client connected from {origin or 'unknown origin'}")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
        return
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Handle client messages if needed (e.g., subscriptions)
                if message.get("type") == "ping":
                    await websocket_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                        websocket
                    )
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from WebSocket client: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
        await websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket_manager.disconnect(websocket)
        except:
            pass


@app.get("/api/account/balance")
async def get_account_balance(account_id: Optional[int] = None):
    """Get account balance."""
    if not projectx_service:
        logger.warning("ProjectX service not initialized when balance requested")
        raise HTTPException(status_code=503, detail="ProjectX service not initialized. Please wait for startup to complete.")

    try:
        balance = await projectx_service.get_account_balance(account_id=account_id)
        return {"balance": balance}
    except Exception as e:
        logger.error(f"Error fetching account balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch balance: {str(e)}")


@app.get("/api/positions")
async def get_positions(account_id: Optional[int] = None):
    """Get open positions."""
    if not projectx_service:
        logger.warning("ProjectX service not initialized when positions requested")
        raise HTTPException(status_code=503, detail="ProjectX service not initialized. Please wait for startup to complete.")

    try:
        positions = await projectx_service.get_positions(account_id=account_id)
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Error fetching positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch positions: {str(e)}")


@app.get("/api/stats")
async def get_stats():
    """Get trading statistics."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    try:
        summary = await projectx_service.get_trades_summary()
        return summary["metrics"]
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@app.post("/api/config/save")
async def save_config(config: dict):
    """Save bot configuration."""
    try:
        account_id = config.get("account_id")
        if not account_id:
            raise HTTPException(status_code=400, detail="account_id required")
        
        if not account_manager:
            raise HTTPException(status_code=503, detail="Account manager not initialized")
        
        if account_id not in account_manager.accounts:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
        
        # Update account configuration
        account_config = account_manager.accounts[account_id]
        
        # Update strategy settings if provided
        if "enabled_strategies" in config:
            # This would require updating the account config file
            # For now, just log it
            logger.info(f"Config update requested for {account_id}: {config}")
        
        # Update risk settings if provided
        if "risk_settings" in config:
            logger.info(f"Risk settings update requested for {account_id}: {config['risk_settings']}")
        
        logger.info(f"Config saved for account {account_id}")
        return {"status": "saved", "config": config, "account_id": account_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")


@app.post("/api/engine/start")
async def start_engine():
    """Start trading engine."""
    if not account_manager:
        raise HTTPException(status_code=503, detail="Account manager not initialized")
    
    try:
        await account_manager.start_all()
        logger.info("Trading engine started for all enabled accounts")
        return {"status": "started", "message": "All enabled accounts started"}
    except Exception as e:
        logger.error(f"Error starting engine: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start engine: {str(e)}")


@app.post("/api/engine/stop")
async def stop_engine():
    """Stop trading engine."""
    if not account_manager:
        raise HTTPException(status_code=503, detail="Account manager not initialized")
    
    try:
        await account_manager.stop_all()
        logger.info("Trading engine stopped for all accounts")
        return {"status": "stopped", "message": "All accounts stopped"}
    except Exception as e:
        logger.error(f"Error stopping engine: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop engine: {str(e)}")


# Multi-Account Endpoints

@app.get("/api/accounts")
async def get_accounts():
    """Get all accounts."""
    if projectx_service:
        accounts = await projectx_service.get_accounts()
        return {"accounts": accounts}

    if account_manager:
        accounts = account_manager.get_all_accounts_status()
        return {"accounts": accounts}

    raise HTTPException(status_code=503, detail="No account source available")


@app.get("/api/accounts/{account_id}")
async def get_account(account_id: str):
    """Get account status."""
    if projectx_service:
        accounts = await projectx_service.get_accounts()
        for account in accounts:
            if str(account.get("id")) == str(account_id):
                return account
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    if account_manager:
        status = account_manager.get_account_status(account_id)
        if status:
            return status

    raise HTTPException(status_code=503, detail="Account manager not initialized")


@app.post("/api/accounts/{account_id}/start")
async def start_account(account_id: str):
    """Start trading for an account."""
    if not account_manager:
        raise HTTPException(status_code=503, detail="Account manager not initialized")

    try:
        await account_manager.start_account(account_id)
        return {"status": "started", "account_id": account_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/{account_id}/stop")
async def stop_account(account_id: str):
    """Stop trading for an account."""
    if not account_manager:
        raise HTTPException(status_code=503, detail="Account manager not initialized")

    try:
        await account_manager.stop_account(account_id)
        return {"status": "stopped", "account_id": account_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/start-all")
async def start_all_accounts():
    """Start all enabled accounts."""
    if not account_manager:
        raise HTTPException(status_code=503, detail="Account manager not initialized")

    try:
        await account_manager.start_all()
        return {"status": "started_all"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/stop-all")
async def stop_all_accounts():
    """Stop all accounts."""
    if not account_manager:
        raise HTTPException(status_code=503, detail="Account manager not initialized")

    try:
        await account_manager.stop_all()
        return {"status": "stopped_all"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Dashboard data for UI
async def _build_dashboard_state() -> Dict:
    """Aggregate dashboard stats for UI."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    projectx_accounts, positions, orders_summary, trades_summary = await asyncio.gather(
        projectx_service.get_accounts(),
        projectx_service.get_positions(),
        projectx_service.get_orders(),
        projectx_service.get_trades_summary(),
    )

    formatted_accounts = [
        {
            "id": account.get("id"),
            "name": account.get("name"),
            "balance": account.get("balance"),
            "canTrade": account.get("canTrade"),
            "isVisible": account.get("isVisible"),
            "simulated": account.get("simulated"),
        }
        for account in projectx_accounts
    ]

    metrics = {
        **trades_summary["metrics"],
        "openPositions": len(positions),
        "pendingOrders": len(orders_summary.get("open", [])),
        "runningAccounts": sum(1 for account in projectx_accounts if account.get("canTrade")),
    }

    bot_snapshots: List[Dict] = []
    if account_manager:
        try:
            bot_snapshots = await account_manager.get_all_snapshots()
        except Exception as exc:
            logger.debug(f"Unable to load bot snapshots: {exc}")

    return {
        "accounts": bot_snapshots,
        "projectx": {
            "accounts": formatted_accounts,
            "positions": positions,
            "orders": orders_summary,
            "trades": trades_summary.get("trades", []),
        },
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/dashboard/state")
async def dashboard_state():
    """Primary data feed for trading UI."""
    if not projectx_service:
        logger.warning("ProjectX service not initialized when dashboard state requested")
        # Return minimal state instead of error to allow UI to load
        return {
            "accounts": [],
            "projectx": {
                "accounts": [],
                "positions": [],
                "orders": {"open": [], "recent": []},
                "trades": [],
            },
            "metrics": {
                "dailyPnl": 0.0,
                "winRate": 0.0,
                "drawdown": 0.0,
                "tradesToday": 0,
                "openPositions": 0,
                "pendingOrders": 0,
                "runningAccounts": 0,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    return await _build_dashboard_state()


# Backtesting Endpoints

class BacktestRequest(BaseModel):
    """Backtest request model."""

    account_ids: List[str]
    symbols: List[str]
    timeframe: str = "5m"
    start_date: str
    end_date: str


class ManualOrderRequest(BaseModel):
    """Manual order placement request."""

    account_id: Optional[int] = None
    symbol: str
    side: str  # BUY/SELL
    order_type: str = "MARKET"
    quantity: int = 1
    time_in_force: str = "DAY"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class StrategyActivationRequest(BaseModel):
    """Quick strategy activation payload."""

    strategy: str
    action: str = "activate"


def _timeframe_to_minutes(timeframe: str) -> int:
    """Convert timeframe strings to minutes."""
    tf = timeframe.lower().strip()
    if tf.endswith("m"):
        return int(tf[:-1])
    if tf.endswith("h"):
        return int(tf[:-1]) * 60
    if tf.endswith("d"):
        return int(tf[:-1]) * 60 * 24
    return 1


@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRequest):
    """Run a deep backtest."""
    if not deep_backtester:
        raise HTTPException(status_code=503, detail="Backtester not initialized")

    try:
        # Parse dates
        start_date = datetime.fromisoformat(request.start_date)
        end_date = datetime.fromisoformat(request.end_date)

        # Load account configs
        accounts = await load_accounts()
        account_configs = [
            accounts[account_id]
            for account_id in request.account_ids
            if account_id in accounts
        ]

        if not account_configs:
            raise HTTPException(
                status_code=400, detail="No valid account IDs provided"
            )

        # Run backtest
        results = await deep_backtester.run_multi_account_backtest(
            account_configs=account_configs,
            symbols=request.symbols,
            timeframe=request.timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        return {"results": results}

    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/results/{account_id}")
async def get_backtest_results(account_id: str):
    """Get backtest results for an account."""
    # TODO: Implement result storage and retrieval
    return {"message": "Not implemented yet", "account_id": account_id}



# Market Data Endpoints


@app.get("/api/market/candles")
async def get_candles(
    symbol: str,
    timeframe: str = "1m",
    bars: int = 200,
):
    """Return candlestick data for charts."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    symbol = symbol.strip().upper()
    timeframe = timeframe.strip().lower()
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe {timeframe}. Allowed: {', '.join(sorted(SUPPORTED_TIMEFRAMES))}",
        )

    bars = max(50, min(bars, MAX_CHART_BARS))

    end_dt = datetime.utcnow()
    minutes = _timeframe_to_minutes(timeframe) * bars
    start_dt = end_dt - timedelta(minutes=minutes or bars)

    try:
        # Extract base symbol (e.g., "ES" from "ESZ25" or "ESZ5")
        base_symbol = symbol
        # Remove month/year suffixes if present (e.g., Z25, Z5, U25, etc.)
        if len(symbol) > 2 and symbol[-1].isdigit():
            # Try to extract just the base (ES, NQ, etc.)
            for i in range(len(symbol) - 1, 0, -1):
                if symbol[i].isalpha():
                    base_symbol = symbol[:i+1]
                    break
        
        candles = await projectx_service.get_candles(
            symbol=base_symbol,
            timeframe=timeframe,
            start=start_dt,
            end=end_dt,
        )
    except Exception as exc:
        logger.error(f"Error fetching candles for {symbol} (base: {base_symbol}): {exc}", exc_info=True)
        error_msg = str(exc)
        if "Unable to find instrument" in error_msg:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol} not found. Try: ES, NQ, MNQ, MES, RTY, etc."
            )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve candles: {error_msg}"
        ) from exc

    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No candle data returned for {symbol}. Market may be closed or symbol invalid."
        )

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles,
        "source": "projectx",
    }


# Trading Data Endpoints

@app.get("/api/market/contracts")
async def list_market_contracts(
    live: bool = Query(default=True),
    search: Optional[str] = None
):
    """Return tradable contracts for instrument selection."""
    try:
        if not projectx_service:
            logger.warning("ProjectX service not initialized when contracts requested")
            raise HTTPException(
                status_code=503,
                detail="ProjectX service not initialized. Please wait for startup to complete."
            )

        try:
            if search:
                contracts = await projectx_service.search_contracts(search_text=search, live=live)
            else:
                contracts = await projectx_service.get_contracts(live=live)
        except Exception as api_exc:
            logger.error(f"ProjectX API error when fetching contracts: {api_exc}", exc_info=True)
            # Surface upstream error with sanitized message
            error_msg = str(api_exc)
            # Limit error message length to prevent huge responses
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch contracts from ProjectX API: {error_msg}"
            ) from api_exc
        
        if not contracts:
            contracts = []  # Ensure it's always a list
        
        def _map_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
            try:
                if not isinstance(contract, dict):
                    return {}
                symbol = contract.get("symbol") or contract.get("name") or contract.get("contractName") or ""
                description = contract.get("description") or contract.get("displayName") or contract.get("name") or ""
                base_symbol = ""
                if symbol:
                    for char in symbol:
                        if char.isalpha():
                            base_symbol += char
                        else:
                            break
                return {
                    "id": contract.get("id") or contract.get("contractId") or "",
                    "symbol": symbol,
                    "name": contract.get("name") or "",
                    "description": description,
                    "baseSymbol": base_symbol or symbol,
                    "tickSize": contract.get("tickSize"),
                    "tickValue": contract.get("tickValue"),
                    "exchange": contract.get("exchange") or "",
                    "live": contract.get("live", live),
                }
            except Exception as map_err:
                logger.warning(f"Error mapping contract: {map_err}")
                return {}

        mapped = [_map_contract(c) for c in contracts if c]
        return {"contracts": mapped}
        
    except HTTPException:
        # Re-raise HTTP exceptions - they'll be handled by exception handler with CORS
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in contracts endpoint: {exc}", exc_info=True)
        error_msg = str(exc)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch contracts: {error_msg}"
        ) from exc


@app.get("/api/trading/positions/{account_id}")
async def get_positions(account_id: int):
    """Get active positions for an account."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    positions = await projectx_service.get_positions(account_id=account_id)
    return {"positions": positions}


@app.get("/api/trading/pending-orders/{account_id}")
async def get_pending_orders(account_id: int):
    """Get pending orders for an account."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    orders = await projectx_service.get_orders(account_id=account_id)
    return {"orders": orders.get("open", [])}


@app.get("/api/trading/previous-orders/{account_id}")
async def get_previous_orders(account_id: int, limit: int = 50):
    """Get previous manual orders for an account."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    orders = await projectx_service.get_orders(account_id=account_id)
    recent = orders.get("recent", [])
    return {"orders": recent[:limit]}


@app.post("/api/trading/place-order")
async def place_order(order: ManualOrderRequest):
    """Place a manual order from UI."""
    if not projectx_service:
        logger.warning("ProjectX service not initialized when place_order requested")
        raise HTTPException(
            status_code=503,
            detail="ProjectX service not initialized. Please wait for startup to complete."
        )

    logger.info(f"Manual order received: {order.model_dump()}")

    stop_loss_ticks = int(order.stop_loss) if order.stop_loss is not None else None
    take_profit_ticks = int(order.take_profit) if order.take_profit is not None else None
    order_type = order.order_type.upper()
    limit_price = order.price if order_type == "LIMIT" else None
    stop_price = order.price if order_type == "STOP" else None

    try:
        response = await projectx_service.place_order(
            account_id=order.account_id,
            symbol=order.symbol,
            side=order.side.upper(),
            order_type=order_type,
            quantity=order.quantity,
            price=limit_price,
            stop_price=stop_price,
            stop_loss_ticks=stop_loss_ticks,
            take_profit_ticks=take_profit_ticks,
        )
        return response
    except Exception as exc:
        logger.error(f"ProjectX order placement failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Order placement failed: {str(exc)}"
        ) from exc


@app.post("/api/trading/accounts/{account_id}/flatten")
async def flatten_account_positions(account_id: int):
    """Close all open positions for an account."""
    if not projectx_service:
        logger.warning(f"ProjectX service not initialized when flatten requested for account {account_id}")
        raise HTTPException(
            status_code=503,
            detail="ProjectX service not initialized. Please wait for startup to complete."
        )

    try:
        result = await projectx_service.flatten_account(account_id=account_id)
        return {"status": "ok", "result": result}
    except ValueError as e:
        # Known user errors (e.g., invalid account_id)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Error flattening account {account_id}: {e}", exc_info=True)
        # Surface upstream errors with sanitized message
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        raise HTTPException(
            status_code=500,
            detail=f"Flatten failed: {error_msg}"
        ) from e


@app.post("/api/strategies/{account_id}/activate")
async def activate_strategy(account_id: str, request: StrategyActivationRequest):
    """Activate or deactivate a quick strategy for UI."""
    if not account_manager:
        raise HTTPException(status_code=503, detail="Account manager not initialized")

    try:
        strategy_name = request.strategy if request.action == "activate" else None
        account_manager.set_active_strategy(account_id, strategy_name)
        logger.info(f"Strategy {request.strategy} -> {request.action} for {account_id}")
        return {"status": "ok", "account_id": account_id, "strategy": strategy_name}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


async def broadcast_realtime_data():
    """Background task to broadcast real-time data to WebSocket clients."""
    # This function should run forever, but if it exits, the wrapper will restart it
    while True:
        await asyncio.sleep(1)  # Broadcast every second
        
        if websocket_manager.get_connection_count() == 0:
            continue
        
        # Collect real-time data
        data = {}
        
        # Get account balance
        try:
            if projectx_service:
                data["accountBalance"] = await projectx_service.get_account_balance()
        except Exception as e:
            logger.debug(f"Error fetching balance for broadcast: {e}")
        
        # Get positions with live P&L
        try:
            if projectx_service:
                positions = await projectx_service.get_positions()
                # Calculate live P&L for each position using current quotes
                for pos in positions:
                    if pos.get("symbol") and pos.get("entry_price") and pos.get("quantity"):
                        # P&L is already calculated in get_open_positions, but ensure it's included
                        if pos.get("unrealized_pnl") is None:
                            # Fallback calculation if not provided
                            entry_price = pos.get("entry_price", 0)
                            current_price = pos.get("current_price", entry_price)
                            quantity = pos.get("quantity", 0)
                            direction = 1 if pos.get("side") == "LONG" else -1
                            pos["unrealized_pnl"] = (current_price - entry_price) * abs(quantity) * direction
                data["positions"] = positions
        except Exception as e:
            logger.debug(f"Error fetching positions for broadcast: {e}")
        
        # Get stats from ProjectX
        try:
            if projectx_service:
                summary = await projectx_service.get_trades_summary()
                data.update(summary["metrics"])
        except Exception as e:
            logger.debug(f"Error fetching stats for broadcast: {e}")
        
        # Only broadcast if we have data
        if data:
            data["type"] = "realtime_snapshot"
            data["timestamp"] = datetime.utcnow().isoformat()
            await websocket_manager.broadcast(data)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

