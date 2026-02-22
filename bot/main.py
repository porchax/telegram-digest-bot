import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.config import settings
from bot.db.database import close_connection, init_db
from bot.handlers.callbacks import router as callbacks_router
from bot.handlers.commands import router as commands_router
from bot.handlers.messages import router as messages_router
from bot.services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _setup_bot_profile(bot: Bot) -> None:
    """Register bot commands menu, description and short description."""
    commands = [
        BotCommand(command="digest", description="Сгенерировать дайджест за неделю"),
        BotCommand(command="status", description="Статистика бота"),
        BotCommand(command="sources", description="Список отслеживаемых чатов"),
        BotCommand(command="help", description="Справка по командам"),
    ]
    await bot.set_my_commands(commands)
    await bot.set_my_description(
        description=(
            "Бот для автоматического формирования еженедельных дайджестов "
            "группового чата. Анализирует переписку и выделяет ключевые темы."
        )
    )
    await bot.set_my_short_description(
        short_description="Еженедельные дайджесты группового чата"
    )
    logger.info("Bot profile and commands menu configured")


async def main() -> None:
    await init_db()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(commands_router)
    dp.include_router(callbacks_router)
    dp.include_router(messages_router)

    await _setup_bot_profile(bot)
    scheduler = setup_scheduler(bot)

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await close_connection()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
