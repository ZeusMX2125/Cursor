"""
FastAPI application for TopstepX trading bot API.
"""

import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta
import pytz
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, Query
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
from api.topstepx_client_v2 import TopstepXClientV2
from api.projectx_service_v2 import ProjectXServiceV2
from api.websocket_handler import WebSocketHandler
from api.websocket_manager import websocket_manager
from api.ml_endpoints import router as ml_router

app = FastAPI(title="TopstepX Trading Bot API", version="1.0.0")

# Shared timeout for ProjectX API calls (configurable via env)
PROJECTX_API_TIMEOUT_SECONDS = float(os.getenv("PROJECTX_API_TIMEOUT_SECONDS", "12"))

# Include ML router
app.include_router(ml_router)

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
# Allow additional origins via env (comma-separated) to avoid common dev CORS issues
_default_origins = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
_env_origins = {
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
}
ALLOWED_ORIGINS = sorted(_default_origins | _env_origins)
logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,       # fine even if not used; origin cannot be "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)


def _resolve_request_origin(request: Request) -> Optional[str]:
    """Return the allowed origin for this request, if any."""
    origin = request.headers.get("origin")
    if origin and origin in ALLOWED_ORIGINS:
        return origin
    return None


def _attach_cors_headers(response: Response, origin: Optional[str]) -> Response:
    """Attach Access-Control-Allow-Origin when the request origin is allowed."""
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        vary_header = response.headers.get("Vary")
        if vary_header:
            if "Origin" not in vary_header:
                response.headers["Vary"] = f"{vary_header}, Origin"
        else:
            response.headers["Vary"] = "Origin"
    return response


@app.middleware("http")
async def ensure_cors_headers(request: Request, call_next):
    """Ensure every response (success or error) carries CORS headers when allowed."""
    origin = _resolve_request_origin(request)
    response = await call_next(request)
    return _attach_cors_headers(response, origin)

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
            "TOPSTEPX_API_KEY": settings.topstepx_api_key,
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
    # Validate credentials based on auth mode
    settings.validate_credentials()
except Exception as e:
    import sys
    print("\n" + "="*80)
    print("ERROR: Failed to load or validate settings")
    print("="*80)
    print(f"\nError details: {e}")
    print("\nPlease check your .env file in the backend/ directory.")
    print("It should contain lines like:")
    print("  TOPSTEPX_USERNAME=your_username")
    print("  TOPSTEPX_API_KEY=your_api_key")
    print("  TOPSTEPX_BASE_URL=https://api.topstepx.com/api")
    print("\nMake sure:")
    print("  1. Each variable is on its own line")
    print("  2. No spaces around the = sign")
    print("  3. No special characters or BOM at the start of the file")
    print("  4. The file is saved as UTF-8 encoding")
    print("\nSee backend/ENV_SETUP.md for detailed instructions.")
    print("="*80 + "\n")
    sys.exit(1)
account_manager: Optional[AccountManager] = None
deep_backtester: Optional[DeepBacktester] = None
shared_auth_manager: Optional[AuthManager] = None
shared_market_client: Optional[TopstepXClient] = None
projectx_service: Optional[ProjectXService] = None
# V2 client with Result-based error handling (migration in progress)
shared_market_client_v2: Optional[TopstepXClientV2] = None
projectx_service_v2: Optional[ProjectXServiceV2] = None
projectx_ws_handler: Optional[WebSocketHandler] = None
# Unified error handlers so even failures get JSON (CORS will be applied)
# Return JSON for *all* errors; CORSMiddleware will attach headers.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with CORS headers."""
    origin = _resolve_request_origin(request)
    response = JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )
    return _attach_cors_headers(response, origin)


@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with CORS headers."""
    origin = _resolve_request_origin(request)
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)},
    )
    return _attach_cors_headers(response, origin)


@app.exception_handler(Exception)
async def internal_exc_handler(request: Request, exc: Exception):
    """Handle all other exceptions with CORS headers."""
    logger.error(f"Unhandled error for request {request.url}: {exc}", exc_info=True)
    origin = _resolve_request_origin(request)
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
    return _attach_cors_headers(response, origin)


SUPPORTED_TIMEFRAMES = {"1m", "5m", "15m", "30m", "60m", "1h", "4h", "1d"}
MAX_CHART_BARS = 2000


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global account_manager, deep_backtester, shared_auth_manager, shared_market_client, projectx_service, projectx_ws_handler, shared_market_client_v2, projectx_service_v2

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
    
    # Initialize V2 client + service with Result-based error handling
    shared_market_client_v2 = TopstepXClientV2(settings, shared_auth_manager)
    await shared_market_client_v2.initialize()
    projectx_service_v2 = ProjectXServiceV2(shared_market_client_v2)
    logger.info("V2 client initialized (Result-based error handling)")
    
    projectx_ws_handler = WebSocketHandler(
        settings, shared_auth_manager, shared_market_client
    )

    def _make_ws_forwarder(event_type: str):
        async def forward(payload: Dict):
            await websocket_manager.broadcast({"type": event_type, "payload": payload})
            # When trades update, trigger a refresh of realized P&L
            if event_type == "trade_update" and projectx_service:
                try:
                    # Trigger a quick refresh of positions with updated realized P&L
                    # This ensures P&L updates immediately when trades complete
                    asyncio.create_task(_refresh_positions_pnl())
                except Exception as e:
                    logger.debug(f"Error refreshing P&L on trade update: {e}")
            # When quotes update, trigger a position refresh to update unrealized P&L
            if event_type == "quote_update" and projectx_service:
                try:
                    # Trigger a quick refresh of positions with updated quotes for unrealized P&L
                    asyncio.create_task(_refresh_positions_with_quotes())
                except Exception as e:
                    logger.debug(f"Error refreshing positions with quotes: {e}")

        return forward
    
    async def _refresh_positions_with_quotes():
        """Refresh positions with updated quotes to recalculate unrealized P&L."""
        try:
            if not projectx_service:
                return
            # Get all accounts and their positions
            accounts = await projectx_service.get_accounts()
            for account in accounts:
                account_id = account.get("id")
                if account_id:
                    try:
                        # Get positions with latest quotes applied
                        positions = await projectx_service.get_positions(account_id=account_id)
                        # Broadcast updated positions with current prices from quotes
                        await websocket_manager.broadcast({
                            "type": "positions_refresh",
                            "account_id": account_id,
                            "positions": positions,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                    except Exception as e:
                        logger.debug(f"Error refreshing positions for account {account_id}: {e}")
        except Exception as e:
            logger.debug(f"Error in _refresh_positions_with_quotes: {e}")
    
    async def _refresh_positions_pnl():
        """Refresh positions with updated realized P&L after trade updates."""
        try:
            if not projectx_service:
                return
            # Get updated realized P&L from trades
            accounts = await projectx_service.get_accounts()
            for account in accounts:
                account_id = account.get("id")
                if account_id:
                    try:
                        realized_pnl_by_symbol = await projectx_service.get_realized_pnl_for_positions(account_id=account_id)
                        # Broadcast updated realized P&L
                        await websocket_manager.broadcast({
                            "type": "realized_pnl_update",
                            "account_id": account_id,
                            "realized_pnl_by_symbol": realized_pnl_by_symbol,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                    except Exception as e:
                        logger.debug(f"Error refreshing P&L for account {account_id}: {e}")
        except Exception as e:
            logger.debug(f"Error in _refresh_positions_pnl: {e}")

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
    global account_manager, shared_market_client, shared_market_client_v2, projectx_ws_handler

    if account_manager:
        await account_manager.stop_all()
    if shared_market_client:
        await shared_market_client.close()
    if shared_market_client_v2:
        await shared_market_client_v2.close()
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

# DEBUG/TEST ENDPOINTS - Commented out for production
# Uncomment these only for debugging CORS or contract issues

# @app.get("/api/test/cors")
# async def test_cors():
#     """Test endpoint to verify CORS is working."""
#     return {
#         "message": "CORS test successful",
#         "timestamp": datetime.utcnow().isoformat(),
#         "cors_configured": True
#     }

# @app.get("/api/cors-ok")
# async def cors_ok():
#     """Simple GET endpoint to test CORS headers."""
#     return {"ok": True}

# @app.post("/api/cors-ok")
# async def cors_ok_post(payload: dict):
#     """Simple POST endpoint to test CORS headers."""
#     return {"received": payload}

# @app.get("/api/debug/contracts-test")
# async def debug_contracts_test():
#     """Debug endpoint to test contracts endpoint without frontend."""
#     try:
#         if not projectx_service_v2:
#             return {
#                 "error": "V2 service not initialized",
#                 "projectx_service_v2": projectx_service_v2 is not None,
#                 "projectx_service": projectx_service is not None
#             }
#         
#         result = await projectx_service_v2.get_contracts(live=True)
#         
#         if result.is_error():
#             from api.result import Error
#             if isinstance(result, Error):
#                 return {
#                     "error": True,
#                     "message": result.message,
#                     "status_code": result.status_code,
#                     "error_code": result.error_code,
#                     "details": result.details
#                 }
#             return {"error": True, "message": str(result)}
#         
#         contracts = result.unwrap()
#         return {
#             "success": True,
#             "contracts_count": len(contracts) if isinstance(contracts, list) else 0,
#             "sample": contracts[:3] if isinstance(contracts, list) and len(contracts) > 0 else None
#         }
#     except Exception as e:
#         logger.error(f"Debug endpoint error: {e}", exc_info=True)
#         return {"error": True, "exception": str(e), "type": type(e).__name__}


def _is_trading_hours() -> bool:
    """Check if current time is within TopstepX trading hours (futures market hours).
    
    Trading hours: 5:00 PM CT (previous day) to 3:10 PM CT (current day)
    This covers the overnight session and regular trading hours.
    """
    try:
        ct = pytz.timezone("America/Chicago")
        now = datetime.now(ct)
        hour = now.hour
        minute = now.minute

        # Trading hours: 5:00 PM CT (17:00) to 3:10 PM CT (15:10) next day
        if hour >= 17 or hour < 15:
            return True
        if hour == 15 and minute <= 10:
            return True
        return False
    except Exception as e:
        logger.warning(f"Error checking trading hours: {e}")
        # Default to allowing orders if we can't determine hours
        return True


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
    # Allow connections from frontend origins or if origin is missing (direct connections)
    if origin and origin not in ALLOWED_ORIGINS:
        logger.warning(f"WebSocket connection rejected from origin: {origin}")
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    # If no origin header, allow connection (for direct WebSocket connections)
    
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
    
    # Send initial connection confirmation
    try:
        await websocket_manager.send_personal_message(
            {"type": "connected", "timestamp": datetime.utcnow().isoformat()},
            websocket
        )
    except Exception as e:
        logger.debug(f"Could not send initial connection message: {e}")
    
    try:
        # Use asyncio.wait_for to handle timeouts gracefully
        while True:
            try:
                # Wait for message with timeout to allow periodic health checks
                # This prevents the connection from hanging indefinitely
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60 second timeout
                )
                try:
                    message = json.loads(data)
                    # Handle client messages if needed (e.g., subscriptions)
                    if message.get("type") == "ping":
                        await websocket_manager.send_personal_message(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                            websocket
                        )
                        logger.debug("Received ping, sent pong")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from WebSocket client: {data}")
            except asyncio.TimeoutError:
                # Timeout is normal - just continue the loop to keep connection alive
                # The frontend will send pings periodically
                # Check if connection is still alive
                try:
                    # Send a keepalive ping to check connection health
                    await websocket.send_text(json.dumps({
                        "type": "keepalive",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except Exception:
                    # Connection is dead, break out of loop
                    logger.debug("WebSocket connection appears dead, closing")
                    break
                continue
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
        await websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket_manager.disconnect(websocket)
        except:
            pass


# DEPRECATED ENDPOINTS - Replaced by more specific endpoints
# These are kept commented for reference but should not be used

# @app.get("/api/account/balance")
# async def get_account_balance(account_id: Optional[int] = None):
#     """DEPRECATED: Use /api/dashboard/state or /api/accounts/{account_id} instead."""
#     if not projectx_service:
#         logger.warning("ProjectX service not initialized when balance requested")
#         raise HTTPException(status_code=503, detail="ProjectX service not initialized. Please wait for startup to complete.")
#     try:
#         balance = await projectx_service.get_account_balance(account_id=account_id)
#         return {"balance": balance}
#     except Exception as e:
#         logger.error(f"Error fetching account balance: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to fetch balance: {str(e)}")

# @app.get("/api/positions")
# async def get_positions(account_id: Optional[int] = None):
#     """DEPRECATED: Use /api/trading/positions/{account_id} instead."""
#     if not projectx_service:
#         logger.warning("ProjectX service not initialized when positions requested")
#         raise HTTPException(status_code=503, detail="ProjectX service not initialized. Please wait for startup to complete.")
#     try:
#         positions = await projectx_service.get_positions(account_id=account_id)
#         return {"positions": positions}
#     except Exception as e:
#         logger.error(f"Error fetching positions: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to fetch positions: {str(e)}")

# @app.get("/api/stats")
# async def get_stats():
#     """DEPRECATED: Use /api/dashboard/state instead."""
#     if not projectx_service:
#         raise HTTPException(status_code=503, detail="ProjectX service not initialized")
#     try:
#         summary = await projectx_service.get_trades_summary()
#         return summary["metrics"]
#     except Exception as e:
#         logger.error(f"Error fetching stats: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


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


# DEPRECATED ENDPOINTS - Use account-specific endpoints instead
# These old single-engine endpoints are replaced by /api/accounts/{id}/start and /api/accounts/{id}/stop

# @app.post("/api/engine/start")
# async def start_engine():
#     """DEPRECATED: Use /api/accounts/start-all or /api/accounts/{id}/start instead."""
#     if not account_manager:
#         raise HTTPException(status_code=503, detail="Account manager not initialized")
#     try:
#         await account_manager.start_all()
#         logger.info("Trading engine started for all enabled accounts")
#         return {"status": "started", "message": "All enabled accounts started"}
#     except Exception as e:
#         logger.error(f"Error starting engine: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to start engine: {str(e)}")

# @app.post("/api/engine/stop")
# async def stop_engine():
#     """DEPRECATED: Use /api/accounts/stop-all or /api/accounts/{id}/stop instead."""
#     if not account_manager:
#         raise HTTPException(status_code=503, detail="Account manager not initialized")
#     try:
#         await account_manager.stop_all()
#         logger.info("Trading engine stopped for all accounts")
#         return {"status": "stopped", "message": "All accounts stopped"}
#     except Exception as e:
#         logger.error(f"Error stopping engine: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to stop engine: {str(e)}")


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


@app.get("/api/accounts/{account_id}/status")
async def get_account_status(account_id: str):
    """Get bot running status for an account."""
    # First check if account is in account_manager (bot-managed)
    if account_manager:
        try:
            account_status = account_manager.get_account_status(account_id)
            if account_status:
                is_running = account_id in account_manager.bots
                active_strategy = account_manager.active_strategies.get(account_id)
                bot_health = account_manager.get_bot_health(account_id)
                
                return {
                    "account_id": account_id,
                    "running": is_running,
                    "active_strategy": active_strategy,
                    "status": "running" if is_running else "stopped",
                    "name": account_status.get("name"),
                    "enabled": account_status.get("enabled", False),
                    "bot_managed": True,
                    "bot_health": bot_health,
                }
        except Exception as e:
            logger.error(f"Error getting account status from account_manager: {e}", exc_info=True)
    
    # If not in account_manager, check if it's a ProjectX account
    if projectx_service:
        try:
            accounts = await asyncio.wait_for(
                projectx_service.get_accounts(),
                timeout=PROJECTX_API_TIMEOUT_SECONDS
            )
            for account in accounts:
                if str(account.get("id")) == str(account_id):
                    # This is a ProjectX account but not bot-managed
                    return {
                        "account_id": account_id,
                        "running": False,
                        "active_strategy": None,
                        "status": "not_managed",
                        "name": account.get("name") or f"Account {account_id}",
                        "enabled": False,
                        "bot_managed": False,
                    }
        except Exception as e:
            logger.error(f"Error checking ProjectX accounts: {e}", exc_info=True)
    
    # Account not found in either system
    raise HTTPException(status_code=404, detail=f"Account {account_id} not found")


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


@app.get("/api/accounts/{account_id}/activity")
async def get_bot_activity(account_id: str, limit: int = 50):
    """Get bot activity log for an account."""
    if not account_manager:
        raise HTTPException(status_code=503, detail="Account manager not initialized")
    
    try:
        activities = await account_manager.get_bot_activity(account_id, limit)
        return {"account_id": account_id, "activities": activities}
    except Exception as e:
        logger.error(f"Error getting bot activity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/add")
async def add_account(account_data: dict):
    """Add an account to the bot manager configuration."""
    from accounts.account_loader import add_account_to_config
    
    try:
        # Validate required fields
        if not account_data.get("account_id"):
            raise HTTPException(status_code=400, detail="account_id is required")
        if not account_data.get("name"):
            raise HTTPException(status_code=400, detail="name is required")
        if not account_data.get("stage"):
            raise HTTPException(status_code=400, detail="stage is required")
        if not account_data.get("size"):
            raise HTTPException(status_code=400, detail="size is required")
        
        # Add account to config file
        await add_account_to_config(account_data)
        
        # Reload accounts in account manager if it exists
        if account_manager:
            try:
                account_manager.accounts = await load_accounts()
                logger.info(f"Reloaded accounts after adding {account_data['account_id']}")
            except Exception as e:
                logger.warning(f"Could not reload accounts in manager: {e}")
        
        return {
            "status": "added",
            "account_id": account_data["account_id"],
            "message": f"Account {account_data['account_id']} added successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add account: {str(e)}")


# Dashboard data for UI
async def _build_dashboard_state() -> Dict:
    """Aggregate dashboard stats for UI."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    try:
        # Add timeout to prevent hanging - configurable (defaults to 12s)
        projectx_accounts, positions, orders_summary, trades_summary = await asyncio.wait_for(
            asyncio.gather(
                projectx_service.get_accounts(),
                projectx_service.get_positions(timeout=PROJECTX_API_TIMEOUT_SECONDS, allow_stale=True),
                projectx_service.get_orders(timeout=PROJECTX_API_TIMEOUT_SECONDS, allow_stale=True),
                projectx_service.get_trades_summary(timeout=PROJECTX_API_TIMEOUT_SECONDS, allow_stale=True),
                return_exceptions=True  # Don't fail if one call fails
            ),
            timeout=PROJECTX_API_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.error(
            f"Timeout building dashboard state - API calls exceeded {PROJECTX_API_TIMEOUT_SECONDS:.1f}s"
        )
        # Return empty data instead of failing
        projectx_accounts = []
        positions = []
        orders_summary = {"open": [], "recent": []}
        trades_summary = {"metrics": {}, "trades": []}
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        # Return empty data instead of failing
        projectx_accounts = []
        positions = []
        orders_summary = {"open": [], "recent": []}
        trades_summary = {"metrics": {}, "trades": []}
    
    # Handle exceptions from gather
    if isinstance(projectx_accounts, Exception):
        logger.error(f"Error fetching accounts: {projectx_accounts}")
        projectx_accounts = []
    if isinstance(positions, Exception):
        logger.error(f"Error fetching positions: {positions}")
        positions = []
    if isinstance(orders_summary, Exception):
        logger.error(f"Error fetching orders: {orders_summary}")
        orders_summary = {"open": [], "recent": []}
    if isinstance(trades_summary, Exception):
        logger.error(f"Error fetching trades: {trades_summary}")
        trades_summary = {"metrics": {}, "trades": []}

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
            logger.warning(f"Unable to load bot snapshots: {exc}", exc_info=True)
            bot_snapshots = []

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
    if not symbol:
        raise HTTPException(
            status_code=400,
            detail="Symbol parameter is required and cannot be empty"
        )
    
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

    def _symbol_variants(value: str) -> List[str]:
        upper = value.upper()
        variants = [upper, upper.rstrip("0123456789"), "".join(ch for ch in upper if ch.isalpha())]
        return [v for v in variants if v]

    contract_match: Optional[Dict[str, Any]] = None
    try:
        contracts = await projectx_service.get_contracts()
        target = symbol.upper()
        stripped = target.rstrip("0123456789")
        for contract in contracts:
            candidates = _symbol_variants(contract.get("symbol") or "")
            candidates += _symbol_variants(contract.get("name") or "")
            candidates += _symbol_variants(contract.get("baseSymbol") or "")
            candidates += _symbol_variants(contract.get("id") or "")
            for candidate in candidates:
                if candidate and (candidate == target or candidate == stripped or target.startswith(candidate)):
                    contract_match = contract
                    break
            if contract_match:
                break
    except Exception as exc:
        logger.debug(f"Unable to pre-select contract for {symbol}: {exc}")

    symbol_attempts: List[str] = []
    if contract_match:
        preferred = contract_match.get("symbol") or contract_match.get("name")
        if preferred:
            symbol_attempts.append(str(preferred).upper())
        base = contract_match.get("baseSymbol")
        if base:
            symbol_attempts.append(str(base).upper())
    symbol_attempts.append(symbol.upper())

    if symbol.endswith(("FUT", "F")):
        symbol_attempts.append(symbol[:-3].upper())

    unique_attempts: List[str] = []
    seen_attempts = set()
    for attempt in symbol_attempts:
        trimmed = attempt.strip().upper()
        if trimmed and trimmed not in seen_attempts:
            unique_attempts.append(trimmed)
            seen_attempts.add(trimmed)
        stripped_attempt = trimmed.rstrip("0123456789")
        if stripped_attempt and stripped_attempt not in seen_attempts:
            unique_attempts.append(stripped_attempt)
            seen_attempts.add(stripped_attempt)

    candles: Optional[List[Dict[str, Any]]] = None
    last_error: Optional[Exception] = None
    resolved_symbol = symbol.upper()
    for candidate in unique_attempts:
        try:
            candles = await projectx_service.get_candles(
                symbol=candidate,
                timeframe=timeframe,
                start=start_dt,
                end=end_dt,
            )
            resolved_symbol = candidate
            break
        except Exception as exc:
            last_error = exc
            continue

    if candles is None:
        error_msg = str(last_error) if last_error else "Unknown error"
        logger.error(f"Error fetching candles for {symbol}: {error_msg}", exc_info=bool(last_error))
        if last_error and "Unable to find instrument" in error_msg:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol} not found. Try: ES, NQ, MNQ, MES, RTY, etc."
            ) from last_error
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve candles: {error_msg}"
        ) from last_error or Exception(error_msg)

    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No candle data returned for {symbol}. Market may be closed or symbol invalid."
        )

    return {
        "symbol": resolved_symbol,
        "timeframe": timeframe,
        "candles": candles,
        "source": "projectx",
    }


# Trading Data Endpoints

@app.get("/api/market/search")
async def search_symbols(query: str = Query(..., min_length=1)):
    """Search for symbols (ProjectX contracts) - TradingView compatible."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")
    
    try:
        service = projectx_service_v2 or projectx_service
        if not service:
            raise HTTPException(status_code=503, detail="ProjectX service not initialized")
            
        if projectx_service_v2:
            result = await projectx_service_v2.search_contracts(search_text=query, live=True)
            if result.is_error():
                logger.error(f"Error searching symbols: {result.message}")
                return []
            contracts = result.unwrap()
        else:
            contracts = await projectx_service.search_contracts(search_text=query, live=True)
        
        # Format for TradingView or generic frontend use
        results = []
        for c in contracts:
            results.append({
                "symbol": c.get("symbol"),
                "full_name": c.get("symbol"),
                "description": c.get("name") or c.get("description") or c.get("symbol"),
                "exchange": "TopstepX",
                "ticker": c.get("symbol"),
                "type": "futures",
                "contract_id": c.get("id")
            })
        return results
    except Exception as e:
        logger.error(f"Error searching symbols: {e}")
        return []

@app.get("/api/market/contracts")
async def list_market_contracts(
    live: bool = Query(default=True),
    search: Optional[str] = None
):
    """Return tradable contracts for instrument selection (V2 - Result-based)."""
    logger.info(f"Fetching contracts: live={live}, search={search}")
    try:
        # Use V2 service if available, fallback to V1
        service = projectx_service_v2 or projectx_service
        
        if not service:
            logger.warning("ProjectX service not initialized when contracts requested")
            raise HTTPException(
                status_code=503,
                detail="ProjectX service not initialized. Please wait for startup to complete."
            )

        # Call service (V2 returns Result, V1 raises exceptions)
        if projectx_service_v2:
            try:
                if search:
                    result = await projectx_service_v2.search_contracts(search_text=search, live=live)
                else:
                    # get_contracts now handles fallback internally
                    result = await projectx_service_v2.get_contracts(live=live)
                
                # Handle Result type - check if it's an Error
                if result.is_error():
                    # Type narrowing: if is_error() is True, result must be Error
                    from api.result import Error
                    if isinstance(result, Error):
                        error_msg = result.message
                        error_status = result.status_code
                    else:
                        # Fallback if type checking fails
                        error_msg = getattr(result, 'message', f"Unknown error: {type(result)}")
                        error_status = getattr(result, 'status_code', 500)
                    
                    logger.error(f"ProjectX API error when fetching contracts: {error_msg} (status: {error_status})")
                    raise HTTPException(
                        status_code=error_status,
                        detail=error_msg
                    )
                
                # If not error, result is Success[T], safe to unwrap
                contracts = result.unwrap()
            except HTTPException:
                raise
            except Exception as v2_exc:
                logger.error(f"Unexpected error in V2 service: {v2_exc}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal error: {str(v2_exc)[:200]}"
                )
        else:
            # V1 fallback (exception-based)
            try:
                if search:
                    contracts = await projectx_service.search_contracts(search_text=search, live=live)
                else:
                    contracts = await projectx_service.get_contracts(live=live)
                    
                    # If live contracts return empty, try non-live contracts as fallback
                    if isinstance(contracts, list) and len(contracts) == 0 and live:
                        logger.warning("No live contracts found, trying non-live contracts as fallback")
                        contracts = await projectx_service.get_contracts(live=False)
            except Exception as api_exc:
                logger.error(f"ProjectX API error (V1): {api_exc}", exc_info=True)
                error_msg = str(api_exc)[:200]
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch contracts: {error_msg}"
                ) from api_exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in list_market_contracts: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)[:200]}"
        )
    
    if not contracts:
        contracts = []
    
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
    logger.info(f"Returning {len(mapped)} mapped contracts (from {len(contracts)} raw contracts)")
    return {"contracts": mapped}


@app.get("/api/trading/positions/{account_id}")
async def get_positions(account_id: int):
    """Get active positions for an account."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    try:
        positions = await asyncio.wait_for(
            projectx_service.get_positions(
                account_id=account_id,
                timeout=PROJECTX_API_TIMEOUT_SECONDS,
                allow_stale=True
            ),
            timeout=PROJECTX_API_TIMEOUT_SECONDS
        )
        return {"positions": positions}
    except asyncio.TimeoutError:
        logger.error(
            f"Timeout fetching positions for account {account_id} after {PROJECTX_API_TIMEOUT_SECONDS}s"
        )
        return {
            "positions": [],
            "stale": True,
            "message": "Positions request timed out - showing empty results",
        }
    except Exception as e:
        logger.error(f"Error fetching positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch positions: {str(e)}")


@app.get("/api/trading/pending-orders/{account_id}")
async def get_pending_orders(account_id: int):
    """Get pending orders for an account."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    try:
        orders = await asyncio.wait_for(
            projectx_service.get_orders(
                account_id=account_id,
                timeout=PROJECTX_API_TIMEOUT_SECONDS,
                allow_stale=True
            ),
            timeout=PROJECTX_API_TIMEOUT_SECONDS
        )
        return {"orders": orders.get("open", [])}
    except asyncio.TimeoutError:
        logger.error(
            f"Timeout fetching pending orders for account {account_id} after {PROJECTX_API_TIMEOUT_SECONDS}s"
        )
        return {
            "orders": [],
            "stale": True,
            "message": "Pending orders request timed out - showing empty results",
        }
    except Exception as e:
        logger.error(f"Error fetching pending orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")


@app.get("/api/trading/previous-orders/{account_id}")
async def get_previous_orders(account_id: int, limit: int = 50):
    """Get previous manual orders for an account."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")

    try:
        orders = await asyncio.wait_for(
            projectx_service.get_orders(
                account_id=account_id,
                timeout=PROJECTX_API_TIMEOUT_SECONDS,
                allow_stale=True
            ),
            timeout=PROJECTX_API_TIMEOUT_SECONDS
        )
        recent = orders.get("recent", [])
        return {"orders": recent[:limit]}
    except asyncio.TimeoutError:
        logger.error(
            f"Timeout fetching previous orders for account {account_id} after {PROJECTX_API_TIMEOUT_SECONDS}s"
        )
        return {
            "orders": [],
            "stale": True,
            "message": "Previous orders request timed out - showing empty results",
        }
    except Exception as e:
        logger.error(f"Error fetching previous orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")


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

    # Check if markets are open
    is_market_open = _is_trading_hours()
    market_warning = None
    if not is_market_open:
        ct = pytz.timezone("America/Chicago")
        now = datetime.now(ct)
        market_warning = (
            f"Warning: Markets are currently closed. "
            f"Trading hours are 5:00 PM CT to 3:10 PM CT. "
            f"Current time: {now.strftime('%I:%M %p CT')}. "
            f"Order submitted - check TopstepX for order status."
        )
        logger.warning(f"Order placed during closed hours: {market_warning}")

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
        
        # Add market hours warning to response if applicable
        if market_warning:
            if isinstance(response, dict):
                response["market_warning"] = market_warning
                response["market_open"] = False
            else:
                # If response is not a dict, wrap it
                response = {
                    "order_response": response,
                    "market_warning": market_warning,
                    "market_open": False
                }
        else:
            if isinstance(response, dict):
                response["market_open"] = True
        
        return response
    except Exception as exc:
        logger.error(f"ProjectX order placement failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Order placement failed: {str(exc)}"
        ) from exc


@app.post("/api/trading/accounts/{account_id}/flatten")
async def flatten_account_positions(account_id: int):
    """Close all open positions for an account (V2 - Result-based)."""
    service = projectx_service_v2 or projectx_service
    
    if not service:
        logger.warning(f"ProjectX service not initialized when flatten requested for account {account_id}")
        raise HTTPException(
            status_code=503,
            detail="ProjectX service not initialized. Please wait for startup to complete."
        )

    # Use V2 service if available
    if projectx_service_v2:
        result = await projectx_service_v2.flatten_account(account_id=account_id)
        
        if result.is_error():
            logger.error(f"Error flattening account {account_id}: {result.message}")
            raise HTTPException(
                status_code=result.status_code,
                detail=result.message
            )
        
        data = result.unwrap()
        return {"status": "ok", "result": data}
    else:
        # V1 fallback
        try:
            result = await projectx_service.flatten_account(account_id=account_id)
            return {"status": "ok", "result": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Error flattening account {account_id}: {e}", exc_info=True)
            error_msg = str(e)[:200]
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
    """Background task to broadcast real-time data to WebSocket clients.
    
    This runs forever and is wrapped in safe_broadcast_wrapper which restarts it on crashes.
    All operations are defensive - exceptions are caught and logged without crashing the loop.
    """
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while True:
        try:
            await asyncio.sleep(1)  # Broadcast every second
            
            if websocket_manager.get_connection_count() == 0:
                consecutive_errors = 0  # Reset on idle
                continue
            
            # Collect real-time data - all operations defensive
            data = {}
            
            # Get account balance
            try:
                if projectx_service:
                    data["accountBalance"] = await projectx_service.get_account_balance()
            except Exception as e:
                logger.debug(f"Error fetching balance for broadcast: {e}")
            
            # Get positions with live P&L - fetch for all accounts
            try:
                if projectx_service:
                    # Get all accounts first
                    accounts = await projectx_service.get_accounts()
                    all_positions = []
                    
                    # Fetch positions for each account
                    for account in accounts:
                        account_id = account.get("id")
                        if account_id:
                            try:
                                # Get realized P&L from trades for this specific account (includes commissions)
                                realized_pnl_by_symbol = await projectx_service.get_realized_pnl_for_positions(account_id=account_id)
                                
                                # Get positions with correct P&L calculations (includes tick/point multipliers)
                                # projectx_service.get_positions() already calculates P&L correctly with contract metadata
                                positions = await projectx_service.get_positions(account_id=account_id)
                                
                                # Debug logging for position fetch
                                if positions:
                                    logger.debug(f"[Broadcast] Fetched {len(positions)} positions for account {account_id}")
                                
                                # Only update current_price from cached quotes and add realized P&L
                                # Do NOT recalculate unrealized P&L here - projectx_service already did it correctly
                                for pos in positions:
                                    pos["account_id"] = account_id
                                    
                                    # Add realized P&L from trades if available for this symbol
                                    symbol = pos.get("symbol", "").upper()
                                    if symbol in realized_pnl_by_symbol:
                                        pos["realized_pnl"] = realized_pnl_by_symbol[symbol]
                                    
                                    # Update current_price from cached quotes if available (for live updates)
                                    # projectx_service will recalculate P&L with correct multipliers on next call
                                    cached_price = shared_market_client.get_cached_quote(symbol) if shared_market_client else None
                                    if cached_price is not None and cached_price != pos.get("current_price"):
                                        # Price changed - need to recalculate P&L with correct multipliers
                                        pos["current_price"] = cached_price
                                        
                                        # Recalculate P&L using the multipliers that projectx_service provided
                                        entry_price = pos.get("entry_price", 0)
                                        quantity = pos.get("quantity", 0)
                                        side = pos.get("side", "LONG").upper()
                                        direction = 1 if side == "LONG" else -1
                                        
                                        # Use the price multiplier from contract metadata (already in position from projectx_service)
                                        point_value = pos.get("point_value")
                                        tick_value = pos.get("tick_value")
                                        tick_size = pos.get("tick_size")
                                        
                                        if entry_price > 0 and quantity != 0:
                                            price_diff = cached_price - entry_price
                                            # Calculate with proper multipliers (same logic as projectx_service)
                                            if point_value:
                                                unrealized = price_diff * point_value * abs(quantity) * direction
                                            elif tick_value and tick_size and tick_size != 0:
                                                ticks = price_diff / tick_size
                                                unrealized = ticks * tick_value * abs(quantity) * direction
                                            else:
                                                # Fallback if no multipliers available
                                                unrealized = price_diff * abs(quantity) * direction
                                            
                                            pos["unrealized_pnl"] = unrealized
                                            
                                            # Recalculate current_value and pnl_percent
                                            price_multiplier = point_value or (tick_value / tick_size if tick_value and tick_size and tick_size != 0 else 1.0)
                                            pos["current_value"] = cached_price * abs(quantity) * price_multiplier
                                            
                                            entry_value = pos.get("entry_value", 0)
                                            if entry_value > 0:
                                                pos["pnl_percent"] = (unrealized / entry_value) * 100
                                            
                                            # Debug logging for P&L recalculation
                                            logger.debug(
                                                f"[Broadcast] Updated {symbol}: price={cached_price:.2f}, "
                                                f"unrealized_pnl={unrealized:.2f}, multiplier={price_multiplier}"
                                            )
                                    
                                all_positions.extend(positions)
                            except Exception as e:
                                logger.debug(f"Error fetching positions for account {account_id}: {e}")
                    
                    data["positions"] = all_positions
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
                consecutive_errors = 0  # Reset on success
                
        except Exception as outer_exc:
            consecutive_errors += 1
            logger.error(
                f"Error in broadcast loop (consecutive: {consecutive_errors}): {outer_exc}",
                exc_info=True
            )
            
            # If too many consecutive errors, back off longer
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many consecutive broadcast errors ({consecutive_errors}), backing off 30s")
                await asyncio.sleep(30)
                consecutive_errors = 0  # Reset after backoff
            else:
                await asyncio.sleep(2)  # Brief pause before retry


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

