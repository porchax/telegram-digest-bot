import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.db.database import init_db
from bot.handlers.commands import router as commands_router
from bot.handlers.messages import router as messages_router
from bot.services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(commands_router)
    dp.include_router(messages_router)

    scheduler = setup_scheduler(bot)

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
