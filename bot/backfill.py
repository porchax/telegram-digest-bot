"""Разовый backfill истории чата в БД бота через личный аккаунт (MTProto / Telethon).

Telegram Bot API не позволяет ботам читать прошлые сообщения, поэтому этот скрипт
логинится ТВОИМ аккаунтом, читает последние N дней чата и кладёт сообщения в ту же
SQLite-базу, что использует бот (DATABASE_PATH). Идемпотентно: INSERT OR IGNORE не
создаёт дублей с тем, что бот уже собрал (ключ — message_id в рамках источника).

Запускать ВНУТРИ контейнера Railway (там смонтирован volume /data):

    railway ssh
    pip install telethon
    python -m bot.backfill --chat -1001162904483 --days 7

Нужны переменные окружения TELEGRAM_API_ID и TELEGRAM_API_HASH (с https://my.telegram.org).
При первом запуске Telethon интерактивно спросит номер телефона и код подтверждения
(и пароль 2FA, если включён). Сессия сохраняется рядом с БД (backfill.session на /data),
поэтому повторные запуски не требуют повторного входа.

ВАЖНО: --chat должен быть в «бот-форме» id (как видит бот, обычно -100XXXXXXXXXX),
чтобы источник совпал с тем, что бот уже создал, иначе дайджест не увидит данные.
"""
import argparse
import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from bot.config import settings
from bot.db.database import close_connection, init_db
from bot.db.models import Message
from bot.db.repository import Repository
from bot.services.collector import get_display_name, normalize_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill")


async def _run(chat: str, days: int) -> None:
    # Лёгкий импорт здесь, чтобы бот никогда не зависел от telethon в рантайме.
    from telethon import TelegramClient

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        raise SystemExit(
            "Задай переменные TELEGRAM_API_ID и TELEGRAM_API_HASH "
            "(получить на https://my.telegram.org)."
        )

    # Сессия рядом с БД — переживает повторные запуски на volume.
    session_path = str(Path(settings.database_path).parent / "backfill.session")

    # Источник должен совпадать с тем, что использует бот → используем переданный id как есть.
    try:
        chat_id = int(chat)
    except ValueError:
        chat_id = chat  # @username тоже допустим

    cutoff = datetime.now(UTC) - timedelta(days=days)

    await init_db()
    repo = Repository()

    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.start()  # интерактивный вход при первом запуске
    try:
        entity = await client.get_entity(chat_id)
        title = getattr(entity, "title", None)
        username = getattr(entity, "username", None)

        source = await repo.get_or_create_source(
            telegram_id=chat_id if isinstance(chat_id, int) else entity.id,
            source_type="group",
            title=title,
            username=username,
        )

        stored = 0
        scanned = 0
        async for msg in client.iter_messages(entity):
            if msg.date < cutoff:
                break
            scanned += 1

            text = normalize_text(msg.message or "")
            if not text:
                continue

            sender = await msg.get_sender()
            if sender is not None and getattr(sender, "bot", False):
                continue

            user_id = msg.sender_id
            user_name = None
            if sender is not None:
                user_name = get_display_name(
                    getattr(sender, "first_name", None),
                    getattr(sender, "last_name", None),
                ) or getattr(sender, "title", None)

            await repo.save_message(
                Message(
                    id=None,
                    source_id=source.id,
                    message_id=msg.id,
                    user_id=user_id,
                    user_name=user_name,
                    text=text,
                    reply_to_message_id=msg.reply_to_msg_id,
                    date=msg.date.astimezone(UTC),
                )
            )
            stored += 1

        logger.info(
            "Backfill готов: просмотрено %d, сохранено %d сообщений для '%s' (source_id=%s)",
            scanned, stored, title, source.id,
        )
        print(f"✅ Backfill готов: сохранено {stored} сообщений для «{title}» за {days} дн.")
    finally:
        await client.disconnect()
        await close_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill chat history via Telethon")
    parser.add_argument(
        "--chat",
        required=True,
        help="ID чата в бот-форме (например -1001162904483) или @username",
    )
    parser.add_argument(
        "--days", type=int, default=7, help="За сколько последних дней (по умолчанию 7)",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.chat, args.days))


if __name__ == "__main__":
    main()
