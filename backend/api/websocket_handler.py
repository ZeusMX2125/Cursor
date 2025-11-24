"""WebSocket handler for ProjectX real-time SignalR feeds."""

import asyncio
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from api.auth_manager import AuthManager
from api.topstepx_client import TopstepXClient
from config.settings import Settings

try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
except ImportError:  # pragma: no cover - dependency guaranteed via requirements
    HubConnectionBuilder = None  # type: ignore[assignment]


USER_HUB_URL = "https://rtc.topstepx.com/hubs/user"
MARKET_HUB_URL = "https://rtc.topstepx.com/hubs/market"


class WebSocketHandler:
    """Connects to ProjectX SignalR hubs and forwards updates to callbacks."""

    def __init__(
        self,
        settings: Settings,
        auth_manager: AuthManager,
        api_client: Optional[TopstepXClient] = None,
    ):
        if HubConnectionBuilder is None:
            raise ImportError(
                "signalrcore is required for realtime streaming. "
                "Install backend requirements to enable WebSocket handling."
            )

        self.settings = settings
        self.auth_manager = auth_manager
        self.api_client = api_client
        self.user_connection = None
        self.market_connection = None
        self.running = False
        self._account_id: Optional[int] = None
        self._lock = asyncio.Lock()
        self._reconnect_event: Optional[asyncio.Event] = None
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.callbacks: Dict[str, List[Callable]] = {
            "quote_update": [],
            "trade_update": [],
            "order_update": [],
            "position_update": [],
            "account_update": [],
        }
        self._latest_quotes: Dict[str, float] = {}

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback for a specific event type."""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    async def _emit_event(self, event_type: str, data: Dict) -> None:
        """Emit an event to all registered callbacks."""
        payload = self._prepare_event_payload(event_type, data)
        for callback in self.callbacks.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(payload)
                else:
                    callback(payload)
            except Exception as exc:  # pragma: no cover
                logger.error(f"Error in {event_type} callback: {exc}", exc_info=True)

    def _prepare_event_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event payloads before broadcasting."""
        try:
            if event_type == "quote_update":
                return self._normalize_quote_payload(payload)
            if event_type == "position_update":
                return self._normalize_position_payload(payload)
        except Exception as exc:  # pragma: no cover
            logger.debug(f"Unable to normalize {event_type}: {exc}")
        return payload

    def _extract_symbol(self, payload: Dict[str, Any]) -> Optional[str]:
        symbol = payload.get("symbol") or payload.get("symbolId")
        if not symbol:
            contract_id = payload.get("contractId") or payload.get("id")
            if isinstance(contract_id, str) and "." in contract_id:
                parts = contract_id.split(".")
                if len(parts) >= 4:
                    symbol = parts[3]
        if isinstance(symbol, str):
            return symbol.upper()
        return None

    def _normalize_quote_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(payload or {})
        symbol = self._extract_symbol(payload)
        price = (
            payload.get("price")
            or payload.get("lastPrice")
            or payload.get("close")
            or payload.get("bidPrice")
            or payload.get("askPrice")
        )
        if symbol and isinstance(price, (int, float)):
            self._latest_quotes[symbol] = float(price)

        normalized.update(
            {
                "symbol": symbol,
                "price": float(price) if isinstance(price, (int, float)) else price,
                "bid": payload.get("bidPrice") or payload.get("bid"),
                "ask": payload.get("askPrice") or payload.get("ask"),
                "lastPrice": payload.get("lastPrice") or price,
            }
        )
        return normalized

    def _normalize_position_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(payload or {})
        symbol = self._extract_symbol(payload)
        side_code = payload.get("type") or payload.get("side") or 1
        side = "LONG" if int(side_code) == 1 else "SHORT"
        quantity = float(payload.get("size") or payload.get("quantity") or 0)
        entry_price = float(payload.get("averagePrice") or payload.get("entryPrice") or payload.get("price") or 0.0)
        current_price = float(
            payload.get("marketPrice")
            or payload.get("markPrice")
            or payload.get("lastPrice")
            or (self._latest_quotes.get(symbol) if symbol else entry_price)
            or entry_price
        )

        entry_value = entry_price * abs(quantity)
        direction = 1 if side == "LONG" else -1

        unrealized = payload.get("floatingProfitLoss") or payload.get("profitAndLoss") or payload.get("unrealizedPnL")
        if isinstance(unrealized, (int, float)):
            unrealized_value = float(unrealized)
        else:
            unrealized_value = (current_price - entry_price) * abs(quantity) * direction

        pnl_percent = (unrealized_value / entry_value * 100) if entry_value else 0.0

        normalized.update(
            {
                "position_id": payload.get("id") or payload.get("positionId"),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
                "current_price": current_price,
                "entry_value": entry_value,
                "current_value": current_price * abs(quantity),
                "unrealized_pnl": unrealized_value,
                "pnl_percent": pnl_percent,
                "account_id": payload.get("accountId") or payload.get("account_id"),
                "entry_time": payload.get("creationTimestamp") or payload.get("openTimestamp") or payload.get("timestamp"),
            }
        )

        realized = payload.get("realizedProfitLoss") or payload.get("realizedPnL")
        if isinstance(realized, (int, float)):
            normalized["realized_pnl"] = float(realized)

        return normalized

    async def connect(self, account_id: Optional[int] = None) -> None:
        """Begin the background connection loop."""
        async with self._lock:
            if account_id is not None:
                self._account_id = int(account_id)
            elif self._account_id is None:
                self._account_id = await self._resolve_default_account_id()

            if self.running:
                return

            self.running = True
            self._loop = asyncio.get_running_loop()
            self._reconnect_event = asyncio.Event()
            self._task = asyncio.create_task(self._connect_loop())

    async def disconnect(self) -> None:
        """Stop streaming and close all hubs."""
        async with self._lock:
            if not self.running:
                return
            self.running = False
            if self._reconnect_event:
                self._reconnect_event.set()
            if self._task:
                await self._task
                self._task = None
            await self._stop_connections()
            self._loop = None

    async def _connect_loop(self) -> None:
        """Main reconnect loop with exponential backoff."""
        backoff = self.settings.websocket_reconnect_delay

        while self.running:
            try:
                token = await self.auth_manager.get_token()
                await self._start_connections(token)
                await self._subscribe()
                logger.info("ProjectX realtime stream started")
                backoff = self.settings.websocket_reconnect_delay

                if self._reconnect_event:
                    await self._reconnect_event.wait()
                    self._reconnect_event.clear()
            except Exception as exc:  # pragma: no cover
                logger.error(f"Realtime connection error: {exc}", exc_info=True)
            finally:
                await self._stop_connections()

            if self.running:
                sleep_time = min(backoff, self.settings.websocket_max_reconnect_delay)
                logger.info(f"Reconnecting to ProjectX SignalR in {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
                backoff = min(backoff * 2, self.settings.websocket_max_reconnect_delay)

    async def _start_connections(self, token: str) -> None:
        """Start both user and market hub connections."""
        loop = asyncio.get_running_loop()

        self.user_connection = (
            HubConnectionBuilder()
            .with_url(f"{USER_HUB_URL}?access_token={token}")
            .with_automatic_reconnect(
                {
                    "type": "interval",
                    "keep_alive_interval": 10,
                    "intervals": [1, 3, 5, 5, 5, 5],
                }
            )
            .build()
        )

        self.market_connection = (
            HubConnectionBuilder()
            .with_url(f"{MARKET_HUB_URL}?access_token={token}")
            .with_automatic_reconnect(
                {
                    "type": "interval",
                    "keep_alive_interval": 10,
                    "intervals": [1, 3, 5, 5, 5, 5],
                }
            )
            .build()
        )

        self._register_handlers()

        await asyncio.gather(
            loop.run_in_executor(None, self.user_connection.start),
            loop.run_in_executor(None, self.market_connection.start),
        )

    def _register_handlers(self) -> None:
        """Attach event handlers for hub events."""
        assert self.user_connection is not None
        assert self.market_connection is not None
        loop = self._loop

        def make_handler(event_type: str):
            def handler(args):
                payload = args[0] if args else {}
                if loop:
                    asyncio.run_coroutine_threadsafe(
                        self._emit_event(event_type, payload), loop
                    )

            return handler

        def make_close_handler():
            def handler():
                if self._reconnect_event:
                    if loop:
                        loop.call_soon_threadsafe(self._reconnect_event.set)
                    else:
                        self._reconnect_event.set()

            return handler

        for event_name, callback_key in [
            ("GatewayUserAccount", "account_update"),
            ("GatewayUserOrder", "order_update"),
            ("GatewayUserPosition", "position_update"),
            ("GatewayUserTrade", "trade_update"),
        ]:
            self.user_connection.on(event_name, make_handler(callback_key))

        for event_name, callback_key in [
            ("GatewayQuote", "quote_update"),
            ("GatewayTrade", "trade_update"),
        ]:
            self.market_connection.on(event_name, make_handler(callback_key))

        self.user_connection.on_close(make_close_handler())
        self.market_connection.on_close(make_close_handler())

    async def _subscribe(self) -> None:
        """Subscribe to realtime channels after connection is open."""
        if not self.user_connection:
            return

        self.user_connection.send("SubscribeAccounts", [])

        account_id = self._account_id
        if account_id:
            for method in ("SubscribeOrders", "SubscribePositions", "SubscribeTrades"):
                self.user_connection.send(method, [account_id])

    async def _stop_connections(self) -> None:
        """Tear down hub connections."""
        loop = asyncio.get_running_loop()
        tasks = []

        if self.user_connection:
            tasks.append(loop.run_in_executor(None, self.user_connection.stop))
            self.user_connection = None

        if self.market_connection:
            tasks.append(loop.run_in_executor(None, self.market_connection.stop))
            self.market_connection = None

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _resolve_default_account_id(self) -> Optional[int]:
        """Resolve the default ProjectX account ID for subscriptions."""
        if not self.api_client:
            return None

        try:
            account = await self.api_client.get_account_info()
            resolved = account.get("id") or account.get("accountId")
            return int(resolved) if resolved is not None else None
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Unable to resolve default account id: {exc}")
            return None

