#!/usr/bin/env python3
"""Entry point for master bot + API server."""

import asyncio

import uvicorn

from src.config import API_PORT


async def run_master_bot():
    """Run master bot."""
    from src.master_bot import main as master_main
    await master_main()


async def run_api_server():
    """Run FastAPI server for Mini App."""
    from aiogram import Bot
    from src.config import MASTER_BOT_TOKEN, CLIENT_BOT_TOKEN
    from src.api.app import app as fastapi_app
    from src.api.routers.orders import set_master_bot as orders_set_bot
    from src.api.routers.requests import set_master_bot as requests_set_bot
    from src.api.routers.master.requests import set_master_bot as master_requests_set_bot
    from src.api.routers.master.settings import set_master_bot as master_settings_set_bot

    # Create bot instance for order request notifications (master_bot)
    bot = Bot(token=MASTER_BOT_TOKEN)
    orders_set_bot(bot)
    requests_set_bot(bot)
    master_requests_set_bot(bot)
    master_settings_set_bot(bot)

    # Pass client_bot into app.state for order action notifications
    client_bot = Bot(token=CLIENT_BOT_TOKEN)
    fastapi_app.state.client_bot = client_bot

    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Run master bot and API server concurrently."""
    await asyncio.gather(
        run_master_bot(),
        run_api_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())
