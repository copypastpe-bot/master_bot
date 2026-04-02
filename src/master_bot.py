"""Master bot - for service providers to manage clients, orders, and marketing."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import MASTER_BOT_TOKEN, LOG_LEVEL
from src.database import init_db
from src.handlers import common  # registration, orders, clients, marketing, reports, settings — disabled

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_dispatcher() -> Dispatcher:
    """Create and configure dispatcher with all routers."""
    dp = Dispatcher(storage=MemoryStorage())

    # HomeButtonMiddleware disabled — bot is entry point only, no navigation
    # dp.message.outer_middleware(common.HomeButtonMiddleware())

    dp.include_router(common.router)

    # Navigation routers disabled — all functionality moved to Mini App
    # dp.include_router(registration.router)
    # dp.include_router(orders.router)
    # dp.include_router(clients.router)
    # dp.include_router(marketing.router)
    # dp.include_router(reports.router)
    # dp.include_router(settings.router)

    return dp


async def main(with_oauth: bool = True) -> None:
    """Main entry point.

    Args:
        with_oauth: If True, also starts the OAuth server (standalone mode).
                    Set to False when oauth_server is managed externally (e.g. main.py).
    """
    from src.oauth_server import set_master_bot

    await init_db()
    logger.info("Database initialized")

    bot = Bot(token=MASTER_BOT_TOKEN)
    dp = setup_dispatcher()

    # Set bot instance for OAuth server notifications
    set_master_bot(bot)

    logger.info("Starting master bot...")

    if with_oauth:
        from src.oauth_server import run_oauth_server
        await asyncio.gather(
            dp.start_polling(bot),
            run_oauth_server(),
        )
    else:
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main(with_oauth=True))
