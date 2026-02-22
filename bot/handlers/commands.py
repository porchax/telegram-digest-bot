import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.config import settings
from bot.db.repository import Repository
from bot.services.digest import generate_and_send_digest

logger = logging.getLogger(__name__)
router = Router(name="commands")
repo = Repository()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


async def _check_admin(message: Message) -> bool:
    """Check if user is admin, reply with denial if not. Returns True if admin."""
    if not message.from_user or not _is_admin(message.from_user.id):
        await message.reply("⛔ У вас нет прав для этой команды.")
        return False
    return True


@router.message(Command("digest"))
async def cmd_digest(message: Message, command: CommandObject) -> None:
    if not await _check_admin(message):
        return

    days = 7
    if command.args:
        try:
            days = int(command.args)
        except ValueError:
            await message.reply("Укажите число дней, например: /digest 7")
            return
        if days < 1 or days > 365:
            await message.reply("Укажите число дней от 1 до 365.")
            return

    progress = await message.reply(f"⏳ Генерирую дайджест за {days} дней…")
    await generate_and_send_digest(
        message.bot, message.chat.id, days=days, progress_message=progress,
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    source = await repo.get_source_by_telegram_id(message.chat.id)
    if not source:
        await message.reply("Этот чат ещё не отслеживается.")
        return

    total = await repo.get_message_count(source.id)
    last_digest = await repo.get_last_digest(source.id)

    lines = [
        f"📊 <b>Статус бота</b>",
        f"Сообщений собрано: {total}",
    ]

    if last_digest:
        lines.append(f"Последний дайджест: {last_digest.created_at}")
        lines.append(f"Сообщений в нём: {last_digest.message_count}")
    else:
        lines.append("Дайджестов пока не было")

    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "📋 <b>Команды бота</b>\n\n"
        "/digest — сгенерировать дайджест за 7 дней\n"
        "/digest N — дайджест за N дней\n"
        "/status — статистика бота\n"
        "/sources — список отслеживаемых чатов\n"
        "/add_channel — добавить канал для отслеживания\n"
        "/remove_channel — убрать канал из отслеживания\n"
        "/help — эта справка"
    )
    await message.reply(text, parse_mode="HTML")


@router.message(Command("sources"))
async def cmd_sources(message: Message) -> None:
    if not await _check_admin(message):
        return

    sources = await repo.get_active_sources()
    if not sources:
        await message.reply("Нет отслеживаемых чатов.")
        return

    lines = ["📋 <b>Отслеживаемые чаты:</b>", ""]
    for s in sources:
        title = s.title or "Без названия"
        lines.append(f"• {title} ({s.type}, id: {s.telegram_id})")

    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message, command: CommandObject) -> None:
    if not await _check_admin(message):
        return

    if not command.args:
        await message.reply(
            "Укажите ID канала, например: /add_channel -1001234567890\n"
            "Бот должен быть администратором канала."
        )
        return

    try:
        channel_id = int(command.args.strip())
    except ValueError:
        await message.reply("Неверный формат ID. Укажите числовой ID канала.")
        return

    # Try to get channel info via bot
    try:
        chat = await message.bot.get_chat(channel_id)
    except Exception:
        await message.reply(
            "Не удалось получить информацию о канале. "
            "Убедитесь, что бот добавлен как администратор канала."
        )
        return

    source = await repo.get_or_create_source(
        telegram_id=chat.id,
        source_type="channel",
        title=chat.title,
        username=chat.username,
    )
    # Ensure it's active
    await repo.set_source_active(chat.id, True)

    await message.reply(
        f"Канал <b>{chat.title or chat.id}</b> добавлен для отслеживания.",
        parse_mode="HTML",
    )


@router.message(Command("remove_channel"))
async def cmd_remove_channel(message: Message, command: CommandObject) -> None:
    if not await _check_admin(message):
        return

    if not command.args:
        await message.reply("Укажите ID канала, например: /remove_channel -1001234567890")
        return

    try:
        channel_id = int(command.args.strip())
    except ValueError:
        await message.reply("Неверный формат ID. Укажите числовой ID канала.")
        return

    found = await repo.set_source_active(channel_id, False)
    if found:
        await message.reply("Канал отключён от отслеживания.")
    else:
        await message.reply("Канал с таким ID не найден.")
