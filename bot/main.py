import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.db.database import init_db
from bot.handlers.messages import router as messages_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(messages_router)

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
