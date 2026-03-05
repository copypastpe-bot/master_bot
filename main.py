#!/usr/bin/env python3
"""Main entry point - runs master_bot, client_bot, and oauth_server concurrently."""

import asyncio
import logging

from src.config import LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_master_bot():
    """Run master bot."""
    from src.master_bot import main as master_main
    await master_main()


async def run_client_bot():
    """Run client bot."""
    from src.client_bot import main as client_main
    await client_main()


async def run_oauth_server():
    """Run OAuth callback server."""
    from aiogram import Bot
    from src.config import MASTER_BOT_TOKEN
    from src.oauth_server import run_oauth_server as oauth_main, set_master_bot

    # Create bot instance for sending notifications
    bot = Bot(token=MASTER_BOT_TOKEN)
    set_master_bot(bot)

    await oauth_main()


async def main():
    """Run all components concurrently."""
    logger.info("Starting Master CRM Bot (all components)...")

    await asyncio.gather(
        run_master_bot(),
        run_client_bot(),
        run_oauth_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())
