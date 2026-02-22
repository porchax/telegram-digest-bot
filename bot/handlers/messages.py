import logging

from aiogram import F, Router
from aiogram.types import Message as TgMessage

from bot.db.models import Message
from bot.db.repository import Repository
from bot.services.collector import get_display_name, normalize_text

logger = logging.getLogger(__name__)
router = Router(name="messages")
repo = Repository()


@router.message(F.text | F.caption)
async def on_message(message: TgMessage) -> None:
    # Ignore bots
    if message.from_user and message.from_user.is_bot:
        return

    text = normalize_text(message.text or message.caption or "")
    if not text:
        return

    chat = message.chat

    # Determine source type
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
