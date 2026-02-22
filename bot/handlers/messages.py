import logging

from aiogram import F, Router
from aiogram.filters import IS_NOT_MEMBER, IS_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated, Message as TgMessage

from bot.db.models import Message
from bot.db.repository import Repository
from bot.services.collector import get_display_name, normalize_text

logger = logging.getLogger(__name__)
router = Router(name="messages")
repo = Repository()


async def _save_group_message(message: TgMessage) -> None:
    """Common logic for saving a group/supergroup message."""
    # Ignore bots
    if message.from_user and message.from_user.is_bot:
        return

    text = normalize_text(message.text or message.caption or "")
    if not text:
        return

    chat = message.chat
    source_type = "channel" if chat.type == "channel" else "group"

    source = await repo.get_or_create_source(
        telegram_id=chat.id,
        source_type=source_type,
        title=chat.title,
        username=chat.username,
    )

    user_name = None
    user_id = None
    if message.from_user:
        user_name = get_display_name(
            message.from_user.first_name,
            message.from_user.last_name,
        )
        user_id = message.from_user.id

    reply_to = None
    if message.reply_to_message:
        reply_to = message.reply_to_message.message_id

    msg = Message(
        id=None,
        source_id=source.id,
        message_id=message.message_id,
        user_id=user_id,
        user_name=user_name,
        text=text,
        reply_to_message_id=reply_to,
        date=message.date,
    )

    await repo.save_message(msg)
    logger.debug("Saved message %d from chat %d", message.message_id, chat.id)


@router.message(F.text | F.caption)
async def on_message(message: TgMessage) -> None:
    await _save_group_message(message)


@router.edited_message(F.text | F.caption)
async def on_edited_message(message: TgMessage) -> None:
    """Update existing message text when user edits it."""
    if message.from_user and message.from_user.is_bot:
        return

    text = normalize_text(message.text or message.caption or "")
    if not text:
        return

    source = await repo.get_source_by_telegram_id(message.chat.id)
    if not source:
        return

    await repo.update_message_text(source.id, message.message_id, text)
    logger.debug("Updated edited message %d in chat %d", message.message_id, message.chat.id)


@router.channel_post(F.text | F.caption)
async def on_channel_post(message: TgMessage) -> None:
    """Save channel posts (text or captions on media)."""
    text = normalize_text(message.text or message.caption or "")
    if not text:
        return

    chat = message.chat
    source = await repo.get_or_create_source(
        telegram_id=chat.id,
        source_type="channel",
        title=chat.title,
        username=chat.username,
    )

    msg = Message(
        id=None,
        source_id=source.id,
        message_id=message.message_id,
        user_id=None,
        user_name=chat.title,  # channel name as author
        text=text,
        reply_to_message_id=None,
        date=message.date,
    )

    await repo.save_message(msg)
    logger.debug("Saved channel post %d from %s", message.message_id, chat.title)


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_bot_added_to_group(event: ChatMemberUpdated) -> None:
    """Send a welcome message when the bot is added to a group."""
    await event.answer(
        "👋 Привет! Я бот для еженедельных дайджестов.\n\n"
        "Я буду читать сообщения в этом чате и каждую неделю "
        "формировать структурированный отчёт с ключевыми темами.\n\n"
        "Команды:\n"
        "/digest — сгенерировать дайджест сейчас\n"
        "/status — статистика бота\n"
        "/help — справка",
    )
