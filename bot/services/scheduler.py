import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import settings
from bot.db.repository import Repository
from bot.services.digest import generate_and_send_digest

logger = logging.getLogger(__name__)

repo = Repository()


async def _scheduled_digest(bot: Bot) -> None:
    """Run digest for all active sources."""
    sources = await repo.get_active_sources()
    for source in sources:
        try:
            await generate_and_send_digest(bot, source.telegram_id)
        except Exception:
            logger.exception("Failed to generate digest for source %d", source.id)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Create and start the weekly digest scheduler."""
    scheduler = AsyncIOScheduler(timezone=settings.digest_timezone)
    scheduler.add_job(
        _scheduled_digest,
        CronTrigger(day_of_week=settings.digest_day, hour=settings.digest_hour),
        id="weekly_digest",
        kwargs={"bot": bot},
    )
    scheduler.start()
    logger.info(
        "Scheduler started: digest every %s at %02d:00 (%s)",
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][settings.digest_day],
        settings.digest_hour,
        settings.digest_timezone,
    )
    return scheduler
