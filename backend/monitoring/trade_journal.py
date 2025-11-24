"""Trade journal for logging all trades to database."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Column, Float, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from loguru import logger

from config.settings import Settings

Base = declarative_base()


class TradeRecord(Base):
    """Database model for trade records."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    trade_id = Column(String, unique=True, index=True)
    symbol = Column(String)
    side = Column(String)  # BUY/SELL
    entry_price = Column(Float)
    exit_price = Column(Float)
    quantity = Column(Integer)
    pnl = Column(Float)
    strategy_name = Column(String)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class TradeJournal:
    """Manages trade journaling to database."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self.Session = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database connection."""
        try:
            # Remove asyncpg from URL for SQLAlchemy
            db_url = self.settings.database_url.replace("+asyncpg", "")
            self.engine = create_engine(db_url)
            self.Session = sessionmaker(bind=self.engine)

            # Create tables
            Base.metadata.create_all(self.engine)

            self._initialized = True
            logger.info("Trade journal initialized")

        except Exception as e:
            logger.error(f"Error initializing trade journal: {e}", exc_info=True)

    async def log_trade(self, trade_data: Dict) -> None:
        """Log a trade to the database."""
        if not self._initialized:
            await self.initialize()

        try:
            session = self.Session()

            trade = TradeRecord(
                trade_id=trade_data.get("trade_id"),
                symbol=trade_data.get("symbol"),
                side=trade_data.get("side"),
                entry_price=trade_data.get("entry_price"),
                exit_price=trade_data.get("exit_price"),
                quantity=trade_data.get("quantity"),
                pnl=trade_data.get("pnl"),
                strategy_name=trade_data.get("strategy_name"),
                entry_time=trade_data.get("entry_time"),
                exit_time=trade_data.get("exit_time"),
            )

            session.add(trade)
            session.commit()
            session.close()

        except Exception as e:
            logger.error(f"Error logging trade: {e}", exc_info=True)

    async def get_trades(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get trades from database."""
        if not self._initialized:
            await self.initialize()

        try:
            session = self.Session()
            query = session.query(TradeRecord)

            if start_date:
                query = query.filter(TradeRecord.entry_time >= start_date)
            if end_date:
                query = query.filter(TradeRecord.entry_time <= end_date)

            trades = query.all()

            return [
                {
                    "trade_id": t.trade_id,
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "quantity": t.quantity,
                    "pnl": t.pnl,
                    "strategy_name": t.strategy_name,
                    "entry_time": t.entry_time,
                    "exit_time": t.exit_time,
                }
                for t in trades
            ]

        except Exception as e:
            logger.error(f"Error getting trades: {e}", exc_info=True)
            return []

