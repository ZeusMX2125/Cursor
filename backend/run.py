"""
Alternative entry point for running the trading bot.
"""

import asyncio
from main import TradingBot
from config.settings import Settings

if __name__ == "__main__":
    settings = Settings()
    bot = TradingBot(settings)

    try:
        asyncio.run(bot.initialize())
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\nShutting down...")
        asyncio.run(bot.stop())

