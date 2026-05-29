"""Двухфазный вход в Telegram для backfill (когда код вводится не интерактивно).

Нужен, чтобы залогиниться через `railway ssh -- ...` без интерактивного TTY:
код подтверждения приходит на телефон уже ПОСЛЕ запроса, поэтому вход разбит на 2 шага.

Фаза 1 — запросить код:
    python -m bot.tg_auth --step request --phone +79991234567
  → печатает CODE_SENT (код придёт в Telegram на телефон)

Фаза 2 — войти с кодом:
    python -m bot.tg_auth --step signin --phone +79991234567 --code 12345
  → печатает AUTHORIZED ... (или 2FA_REQUIRED, тогда повторить с --password ...)

Сессия (backfill.session) и временный phone_code_hash хранятся рядом с БД на /data,
поэтому состояние переживает разрыв между двумя ssh-вызовами.
Требует env TELEGRAM_API_ID / TELEGRAM_API_HASH.
"""
import argparse
import asyncio
import os
from pathlib import Path

from bot.config import settings

_DATA_DIR = Path(settings.database_path).parent
_SESSION = str(_DATA_DIR / "backfill.session")
_CODE_HASH_FILE = _DATA_DIR / ".tg_code_hash"


def _creds() -> tuple[int, str]:
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        raise SystemExit("Не заданы TELEGRAM_API_ID / TELEGRAM_API_HASH.")
    return int(api_id), api_hash


async def _request(phone: str) -> None:
    from telethon import TelegramClient

    api_id, api_hash = _creds()
    client = TelegramClient(_SESSION, api_id, api_hash)
    await client.connect()
    try:
        if await client.is_user_authorized():
            print("ALREADY_AUTHORIZED")
            return
        sent = await client.send_code_request(phone)
        _CODE_HASH_FILE.write_text(sent.phone_code_hash)
        print("CODE_SENT")
    finally:
        await client.disconnect()


async def _signin(phone: str, code: str, password: str | None) -> None:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError

    api_id, api_hash = _creds()
    client = TelegramClient(_SESSION, api_id, api_hash)
    await client.connect()
    try:
        if await client.is_user_authorized():
            print("ALREADY_AUTHORIZED")
            return
        phone_code_hash = _CODE_HASH_FILE.read_text().strip()
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            if not password:
                print("2FA_REQUIRED")
                return
            await client.sign_in(password=password)
        me = await client.get_me()
        print(f"AUTHORIZED as {me.first_name or ''} (id={me.id})")
    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-step Telegram login for backfill")
    parser.add_argument("--step", required=True, choices=["request", "signin"])
    parser.add_argument("--phone", required=True, help="Телефон с +кодом страны")
    parser.add_argument("--code", help="Код из Telegram (для step=signin)")
    parser.add_argument("--password", help="Пароль 2FA, если включён")
    args = parser.parse_args()

    if args.step == "request":
        asyncio.run(_request(args.phone))
    else:
        if not args.code:
            raise SystemExit("Для --step signin нужен --code.")
        asyncio.run(_signin(args.phone, args.code, args.password))


if __name__ == "__main__":
    main()
