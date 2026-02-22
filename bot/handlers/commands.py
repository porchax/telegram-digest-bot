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


@router.message(Command("digest"))
async def cmd_digest(message: Message, command: CommandObject) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    days = 7
    if command.args:
        try:
            days = int(command.args)
        except ValueError:
            await message.reply("Укажите число дней, например: /digest 7")
            return

    await message.reply(f"Генерирую дайджест за {days} дней…")
    await generate_and_send_digest(message.bot, message.chat.id, days=days)


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
        "/help — эта справка"
    )
    await message.reply(text, parse_mode="HTML")


@router.message(Command("sources"))
async def cmd_sources(message: Message) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
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
