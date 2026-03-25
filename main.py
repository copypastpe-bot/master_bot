#!/usr/bin/env python3
"""Main entry point - runs master_bot, client_bot, oauth_server, and api_server concurrently."""

import asyncio
import logging

import uvicorn

from src.config import LOG_LEVEL, API_PORT

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_master_bot():
    """Run master bot (oauth_server is started separately by main.py)."""
    from src.master_bot import main as master_main
    await master_main(with_oauth=False)


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


async def run_api_server():
    """Run FastAPI server for Mini App."""
    from aiogram import Bot
    from src.config import MASTER_BOT_TOKEN
    from src.api.app import app as fastapi_app
    from src.api.routers.orders import set_master_bot

    # Create bot instance for order request notifications
    bot = Bot(token=MASTER_BOT_TOKEN)
    set_master_bot(bot)

    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Run all components concurrently."""
    logger.info("Starting Master CRM Bot (all components)...")

    await asyncio.gather(
        run_master_bot(),
        run_client_bot(),
        run_oauth_server(),
        run_api_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())
