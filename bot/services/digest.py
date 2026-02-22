import json
import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import settings
from bot.db.models import Digest
from bot.db.repository import Repository
from bot.services.analyzer import analyze_messages
from bot.utils.message_links import make_message_link

logger = logging.getLogger(__name__)

repo = Repository()

# Telegram message length limit
_TG_MAX_LENGTH = 4096

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


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _format_header(data: dict, week_start: datetime, week_end: datetime) -> str:
    """Format the header section (title + stats)."""
    stats = data.get("week_stats", {})
    total = stats.get("total_messages", 0)
    active = stats.get("active_users", 0)
    date_range = _format_date_range(week_start, week_end)
    return (
        f"📋 <b>Дайджест недели: {date_range}</b>\n"
        f"📊 Сообщений: {total} | Активных участников: {active}"
    )


def _format_topics_section(
    topics: list[dict],
    chat_id: int,
    username: str | None,
    show_message_count: bool = False,
) -> list[str]:
    """Format a list of topics with expandable blockquotes."""
    lines: list[str] = []
    for i, topic in enumerate(topics, 1):
        count_str = ""
        if show_message_count:
            count = topic.get("message_count")
            if count:
                count_str = f" ({count} сообщений)"

        lines.append(f"{i}️⃣ <b>{_escape(topic.get('title', ''))}</b>{count_str}")

        # Summary + link inside expandable blockquote
        bq_lines: list[str] = []
        summary = topic.get("summary", "")
        if summary:
            bq_lines.append(_escape(summary))
        msg_id = topic.get("first_message_id")
        if msg_id:
            link = make_message_link(chat_id, msg_id, username)
            bq_lines.append(f'🔗 <a href="{link}">Начало обсуждения</a>')

        if bq_lines:
            inner = "\n".join(bq_lines)
            lines.append(f"<blockquote expandable>{inner}</blockquote>")
        lines.append("")
    return lines


def format_digest_html(
    data: dict,
    week_start: datetime,
    week_end: datetime,
    chat_id: int,
    username: str | None,
) -> str:
    """Convert analyzer JSON into a Telegram HTML message."""
    lines: list[str] = [_format_header(data, week_start, week_end), ""]

    important = data.get("important_topics", [])
    if important:
        lines.append("🔴 <b>Важные темы:</b>")
        lines.append("")
        lines.extend(_format_topics_section(important, chat_id, username))

    discussed = data.get("discussed_topics", [])
    if discussed:
        lines.append("💬 <b>Обсуждаемые темы:</b>")
        lines.append("")
        lines.extend(
            _format_topics_section(discussed, chat_id, username, show_message_count=True)
        )

    return "\n".join(lines).strip()


def format_important_html(
    data: dict,
    week_start: datetime,
    week_end: datetime,
    chat_id: int,
    username: str | None,
) -> str:
    """Format only the important topics section."""
    lines: list[str] = [_format_header(data, week_start, week_end), ""]
    important = data.get("important_topics", [])
    if important:
        lines.append("🔴 <b>Важные темы:</b>")
        lines.append("")
        lines.extend(_format_topics_section(important, chat_id, username))
    else:
        lines.append("Важных тем за эту неделю не выявлено.")
    return "\n".join(lines).strip()


def format_discussed_html(
    data: dict,
    week_start: datetime,
    week_end: datetime,
    chat_id: int,
    username: str | None,
) -> str:
    """Format only the discussed topics section."""
    lines: list[str] = [_format_header(data, week_start, week_end), ""]
    discussed = data.get("discussed_topics", [])
    if discussed:
        lines.append("💬 <b>Обсуждаемые темы:</b>")
        lines.append("")
        lines.extend(
            _format_topics_section(discussed, chat_id, username, show_message_count=True)
        )
    else:
        lines.append("Обсуждаемых тем за эту неделю не выявлено.")
    return "\n".join(lines).strip()


def format_stats_html(data: dict, week_start: datetime, week_end: datetime) -> str:
    """Format only the statistics section."""
    stats = data.get("week_stats", {})
    date_range = _format_date_range(week_start, week_end)
    total = stats.get("total_messages", 0)
    active = stats.get("active_users", 0)
    most_active = stats.get("most_active_user", "—")

    lines = [
        f"📊 <b>Статистика недели: {date_range}</b>",
        "",
        f"Всего сообщений: <b>{total}</b>",
        f"Активных участников: <b>{active}</b>",
        f"Самый активный: <b>{_escape(most_active or '—')}</b>",
    ]

    important_count = len(data.get("important_topics", []))
    discussed_count = len(data.get("discussed_topics", []))
    lines.append("")
    lines.append(f"Важных тем: {important_count}")
    lines.append(f"Обсуждаемых тем: {discussed_count}")

    return "\n".join(lines).strip()


def build_digest_keyboard(digest_id: int, active: str = "full") -> InlineKeyboardMarkup:
    """Build inline keyboard for digest navigation."""
    buttons = [
        ("🔴 Важные", "important"),
        ("💬 Обсуждаемые", "discussed"),
        ("📊 Статистика", "stats"),
        ("📋 Полный", "full"),
    ]
    row = []
    for label, action in buttons:
        if action == active:
            label = f"• {label} •"
        row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"dg:{action}:{digest_id}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[row])


def _truncate_html(text: str, limit: int = _TG_MAX_LENGTH) -> str:
    """Truncate HTML text to fit Telegram limit, appending '...' if cut."""
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n\n<i>…обрезано</i>"


async def generate_and_send_digest(
    bot: Bot,
    chat_id: int,
    days: int = 7,
    progress_message=None,
) -> None:
    """Generate a digest for the given chat and send it."""
    source = await repo.get_source_by_telegram_id(chat_id)
    if not source:
        logger.warning("No source found for chat %d", chat_id)
        return

    now = datetime.now(UTC)
    week_end = now
    week_start = now - timedelta(days=days)

    messages = await repo.get_messages(source.id, week_start, week_end)
    if not messages:
        logger.info("No messages for chat %d in the last %d days", chat_id, days)
        if progress_message:
            await progress_message.edit_text("📭 Нет сообщений за период.")
        return

    if progress_message:
        await progress_message.edit_text(
            f"📨 Найдено {len(messages)} сообщений, анализирую…"
        )

    logger.info("Generating digest for %d messages from chat %d", len(messages), chat_id)
    data = await analyze_messages(messages, source_type=source.type)

    # Fill in actual stats if LLM didn't provide them
    stats = data.setdefault("week_stats", {})
    stats.setdefault("total_messages", len(messages))
    stats.setdefault(
        "active_users",
        len({m.user_id for m in messages if m.user_id}),
    )

    content = format_digest_html(data, week_start, week_end, chat_id, source.username)
    content = _truncate_html(content)

    # Send message first, then save to DB (avoids orphaned records)
    keyboard_placeholder = build_digest_keyboard(0)
    try:
        sent = await bot.send_message(
            chat_id, content, parse_mode="HTML", reply_markup=keyboard_placeholder,
        )
    except Exception:
        logger.exception("Failed to send digest to chat %d", chat_id)
        if progress_message:
            await progress_message.edit_text("❌ Не удалось отправить дайджест.")
        return

    # Save digest after successful send
    digest = Digest(
        id=None,
        source_id=source.id,
        week_start=week_start,
        week_end=week_end,
        content=content,
        raw_response=json.dumps(data, ensure_ascii=False),
        message_count=len(messages),
        sent_message_id=sent.message_id,
    )
    digest_id = await repo.save_digest(digest)

    # Update keyboard with real digest_id
    keyboard = build_digest_keyboard(digest_id)
    try:
        await bot.edit_message_reply_markup(
            chat_id, sent.message_id, reply_markup=keyboard,
        )
    except Exception:
        logger.warning("Could not update keyboard for digest %d", digest_id)

    # Auto-pin
    if settings.auto_pin_digest:
        try:
            await bot.pin_chat_message(
                chat_id, sent.message_id, disable_notification=True,
            )
        except Exception:
            logger.warning("Could not pin digest in chat %d (no admin rights?)", chat_id)

    if progress_message:
        await progress_message.edit_text("✅ Дайджест отправлен!")

    logger.info("Digest sent to chat %d (message_id=%d)", chat_id, sent.message_id)
