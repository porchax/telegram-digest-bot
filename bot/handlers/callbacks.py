import json
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.db.repository import Repository
from bot.services.digest import (
    build_digest_keyboard,
    format_digest_html,
    format_discussed_html,
    format_important_html,
    format_stats_html,
)

logger = logging.getLogger(__name__)
router = Router(name="callbacks")
repo = Repository()

_VALID_ACTIONS = {"full", "important", "discussed", "stats"}

_SECTION_FORMATTERS = {
    "full": format_digest_html,
    "important": format_important_html,
    "discussed": format_discussed_html,
}


@router.callback_query(F.data.startswith("dg:"))
async def on_digest_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неизвестная команда")
        return

    action, digest_id_str = parts[1], parts[2]

    if action not in _VALID_ACTIONS:
        await callback.answer("Неизвестная команда")
        return

    try:
        digest_id = int(digest_id_str)
    except ValueError:
        await callback.answer("Неизвестная команда")
        return

    digest = await repo.get_digest_by_id(digest_id)
    if not digest:
        await callback.answer("Дайджест не найден")
        return

    source = await repo.get_source_by_id(digest.source_id)
    if not source:
        await callback.answer("Источник не найден")
        return

    if not digest.raw_response:
        await callback.answer("Данные дайджеста недоступны")
        return

    try:
        data = json.loads(digest.raw_response)
    except (json.JSONDecodeError, TypeError):
        await callback.answer("Не удалось загрузить данные дайджеста")
        return

    if action == "stats":
        text = format_stats_html(data, digest.week_start, digest.week_end)
    else:
        text = _SECTION_FORMATTERS[action](
            data, digest.week_start, digest.week_end,
            source.telegram_id, source.username,
        )

    keyboard = build_digest_keyboard(digest_id, active=action)

    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=keyboard,
        )
    except Exception as e:
        logger.warning("Could not edit digest message: %s", e)
        await callback.answer("Не удалось обновить сообщение")
        return

    await callback.answer()
