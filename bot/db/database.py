import logging
from pathlib import Path

import aiosqlite

from bot.config import settings

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('group', 'channel')),
    title TEXT,
    username TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    message_id INTEGER NOT NULL,
    user_id INTEGER,
    user_name TEXT,
    text TEXT,
    reply_to_message_id INTEGER,
    date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, message_id)
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    content TEXT NOT NULL,
    raw_response TEXT,
    message_count INTEGER,
    sent_message_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_source_date ON messages(source_id, date);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date);
"""

_connection: aiosqlite.Connection | None = None


async def get_connection() -> aiosqlite.Connection:
    """Return a shared persistent connection (created on first call)."""
    global _connection

    if _connection is not None:
        return _connection

    db_path = settings.database_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(db_path)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    db.row_factory = aiosqlite.Row

    _connection = db
    return _connection


async def close_connection() -> None:
    """Close the shared connection if open."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None


def reset_connection() -> None:
    """Reset the connection reference (for testing)."""
    global _connection
    _connection = None


async def init_db() -> None:
    db = await get_connection()
    await db.executescript(SCHEMA_SQL)
    await db.commit()
    logger.info("Database initialized successfully")
