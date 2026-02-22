import logging
from datetime import datetime, timedelta

from aiogram import Bot

from bot.db.models import Digest
from bot.db.repository import Repository
from bot.services.analyzer import analyze_messages
from bot.utils.message_links import make_message_link

logger = logging.getLogger(__name__)

repo = Repository()

# Month names in Russian (1-indexed)
_MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def _format_date_range(start: datetime, end: datetime) -> str:
    """Format date range in Russian, e.g. '13–19 января 2025'."""
    if start.month == end.month:
        return f"{start.day}–{end.day} {_MONTHS_RU[end.month]} {end.year}"
    return (
        f"{start.day} {_MONTHS_RU[start.month]} – "
        f"{end.day} {_MONTHS_RU[end.month]} {end.year}"
    )


def format_digest_html(
    data: dict,
    week_start: datetime,
    week_end: datetime,
    chat_id: int,
    username: str | None,
) -> str:
    """Convert analyzer JSON into a Telegram HTML message."""
    stats = data.get("week_stats", {})
    total = stats.get("total_messages", 0)
    active = stats.get("active_users", 0)
    date_range = _format_date_range(week_start, week_end)

    lines: list[str] = [
        f"📋 <b>Дайджест недели: {date_range}</b>",
        f"📊 Сообщений: {total} | Активных участников: {active}",
        "",
    ]

    # Important topics
    important = data.get("important_topics", [])
    if important:
        lines.append("🔴 <b>Важные темы:</b>")
        lines.append("")
        for i, topic in enumerate(important, 1):
            lines.append(f"{i}️⃣ <b>{_escape(topic['title'])}</b>")
            lines.append(_escape(topic.get("summary", "")))
            msg_id = topic.get("first_message_id")
            if msg_id:
                link = make_message_link(chat_id, msg_id, username)
                lines.append(f'🔗 <a href="{link}">Начало обсуждения</a>')
            lines.append("")

    # Discussed topics
    discussed = data.get("discussed_topics", [])
    if discussed:
        lines.append("💬 <b>Обсуждаемые темы:</b>")
        lines.append("")
        for i, topic in enumerate(discussed, 1):
            count = topic.get("message_count")
            count_str = f" ({count} сообщений)" if count else ""
            lines.append(f"{i}️⃣ <b>{_escape(topic['title'])}</b>{count_str}")
            lines.append(_escape(topic.get("summary", "")))
            msg_id = topic.get("first_message_id")
            if msg_id:
                link = make_message_link(chat_id, msg_id, username)
                lines.append(f'🔗 <a href="{link}">Начало обсуждения</a>')
            lines.append("")

    return "\n".join(lines).strip()


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def generate_and_send_digest(
    bot: Bot,
    chat_id: int,
    days: int = 7,
) -> None:
    """Generate a digest for the given chat and send it."""
    source = await repo.get_source_by_telegram_id(chat_id)
    if not source:
        logger.warning("No source found for chat %d", chat_id)
        return

    now = datetime.utcnow()
    week_end = now
    week_start = now - timedelta(days=days)

    messages = await repo.get_messages(source.id, week_start, week_end)
    if not messages:
        logger.info("No messages for chat %d in the last %d days", chat_id, days)
        return

    logger.info("Generating digest for %d messages from chat %d", len(messages), chat_id)
    data = await analyze_messages(messages)

    # Fill in actual stats if LLM didn't provide them
    stats = data.setdefault("week_stats", {})
    stats.setdefault("total_messages", len(messages))
    stats.setdefault(
        "active_users",
        len({m.user_id for m in messages if m.user_id}),
    )

    content = format_digest_html(data, week_start, week_end, chat_id, source.username)

    sent = await bot.send_message(chat_id, content, parse_mode="HTML")

    digest = Digest(
        id=None,
        source_id=source.id,
        week_start=week_start,
        week_end=week_end,
        content=content,
        raw_response=str(data),
        message_count=len(messages),
        sent_message_id=sent.message_id,
    )
    await repo.save_digest(digest)
    logger.info("Digest sent to chat %d (message_id=%d)", chat_id, sent.message_id)
