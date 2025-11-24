"""CLI script for running deep backtests."""

import asyncio
import argparse
from datetime import datetime, timedelta

from loguru import logger

from config.settings import Settings
from api.auth_manager import AuthManager
from backtesting.deep_backtester import DeepBacktester
from accounts.account_loader import load_accounts


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Run deep backtest using ProjectX API")
    parser.add_argument(
        "--account-id",
        type=str,
        help="Account ID to backtest (or 'all' for all accounts)",
        default="all",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        nargs="+",
        default=["MNQ", "MES", "MGC"],
        help="Symbols to backtest",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="5m",
        choices=["1m", "5m", "15m", "1h"],
        help="Bar timeframe",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD)",
        default=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD)",
        default=datetime.now().strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON)",
        default=None,
    )

    args = parser.parse_args()

    # Initialize
    settings = Settings()
    auth_manager = AuthManager(settings)
    await auth_manager.initialize()

    backtester = DeepBacktester(settings, auth_manager)
    await backtester.initialize()

    # Load accounts
    accounts = await load_accounts()

    if args.account_id == "all":
        account_configs = list(accounts.values())
    elif args.account_id in accounts:
        account_configs = [accounts[args.account_id]]
    else:
        logger.error(f"Account {args.account_id} not found")
        return

    # Parse dates
    start_date = datetime.fromisoformat(args.start_date)
    end_date = datetime.fromisoformat(args.end_date)

    logger.info(
        f"Running backtest for {len(account_configs)} account(s) "
        f"from {start_date} to {end_date}"
    )

    # Run backtest
    results = await backtester.run_multi_account_backtest(
        account_configs=account_configs,
        symbols=args.symbols,
        timeframe=args.timeframe,
        start_date=start_date,
        end_date=end_date,
    )

    # Print results
    from backtesting.reporter import BacktestReporter

    for account_id, result in results.items():
        if "error" in result:
            logger.error(f"{account_id}: {result['error']}")
            continue

        print(f"\n{'='*60}")
        print(f"Account: {account_id}")
        print(f"{'='*60}")
        BacktestReporter.print_report(
            type("BacktestResult", (), result)()
        )

    # Save to file if requested
    if args.output:
        import json

        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())

