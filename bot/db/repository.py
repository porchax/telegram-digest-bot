import logging
from datetime import datetime

from bot.db.database import get_connection
from bot.db.models import Digest, Message, Source

logger = logging.getLogger(__name__)


class Repository:
    # ── Sources ──

    async def get_or_create_source(
        self,
        telegram_id: int,
        source_type: str,
        title: str | None = None,
        username: str | None = None,
    ) -> Source:
        db = await get_connection()
        try:
            cursor = await db.execute(
                "SELECT * FROM sources WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cursor.fetchone()

            if row:
                source = self._row_to_source(row)
                # Update title/username if changed
                if title != source.title or username != source.username:
                    await db.execute(
                        "UPDATE sources SET title = ?, username = ? WHERE id = ?",
                        (title, username, source.id),
                    )
                    await db.commit()
                    source.title = title
                    source.username = username
                return source

            await db.execute(
                "INSERT INTO sources (telegram_id, type, title, username) VALUES (?, ?, ?, ?)",
                (telegram_id, source_type, title, username),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM sources WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cursor.fetchone()
            logger.info("Created new source: %s (id=%d)", title, telegram_id)
            return self._row_to_source(row)
        finally:
            await db.close()

    async def get_source_by_telegram_id(self, telegram_id: int) -> Source | None:
        db = await get_connection()
        try:
            cursor = await db.execute(
                "SELECT * FROM sources WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_source(row) if row else None
        finally:
            await db.close()

    async def get_active_sources(self) -> list[Source]:
        db = await get_connection()
        try:
            cursor = await db.execute(
                "SELECT * FROM sources WHERE is_active = 1"
            )
            rows = await cursor.fetchall()
            return [self._row_to_source(r) for r in rows]
        finally:
            await db.close()

    async def set_source_active(self, telegram_id: int, is_active: bool) -> bool:
        """Activate or deactivate a source. Returns True if source was found."""
        db = await get_connection()
        try:
            cursor = await db.execute(
                "UPDATE sources SET is_active = ? WHERE telegram_id = ?",
                (int(is_active), telegram_id),
            )
            await db.commit()
            return cursor.rowcount > 0
        finally:
            await db.close()

    # ── Messages ──

    async def save_message(self, message: Message) -> None:
        db = await get_connection()
        try:
            await db.execute(
                """INSERT OR IGNORE INTO messages
                   (source_id, message_id, user_id, user_name, text, reply_to_message_id, date)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    message.source_id,
                    message.message_id,
                    message.user_id,
                    message.user_name,
                    message.text,
                    message.reply_to_message_id,
                    message.date.isoformat(),
                ),
            )
            await db.commit()
        finally:
            await db.close()

    async def get_messages(
        self,
        source_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> list[Message]:
        db = await get_connection()
        try:
            cursor = await db.execute(
                """SELECT * FROM messages
                   WHERE source_id = ? AND date >= ? AND date <= ?
                   ORDER BY date ASC""",
                (source_id, date_from.isoformat(), date_to.isoformat()),
            )
            rows = await cursor.fetchall()
            return [self._row_to_message(r) for r in rows]
        finally:
            await db.close()

    async def get_message_count(
        self,
        source_id: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        db = await get_connection()
        try:
            if date_from and date_to:
                cursor = await db.execute(
                    """SELECT COUNT(*) FROM messages
                       WHERE source_id = ? AND date >= ? AND date <= ?""",
                    (source_id, date_from.isoformat(), date_to.isoformat()),
                )
            else:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM messages WHERE source_id = ?",
                    (source_id,),
                )
            row = await cursor.fetchone()
            return row[0]
        finally:
            await db.close()

    # ── Digests ──

    async def save_digest(self, digest: Digest) -> int:
        db = await get_connection()
        try:
            cursor = await db.execute(
                """INSERT INTO digests
                   (source_id, week_start, week_end, content, raw_response, message_count, sent_message_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    digest.source_id,
                    digest.week_start.isoformat(),
                    digest.week_end.isoformat(),
                    digest.content,
                    digest.raw_response,
                    digest.message_count,
                    digest.sent_message_id,
                ),
            )
            await db.commit()
            return cursor.lastrowid
        finally:
            await db.close()

    async def get_last_digest(self, source_id: int) -> Digest | None:
        db = await get_connection()
        try:
            cursor = await db.execute(
                """SELECT * FROM digests
                   WHERE source_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (source_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_digest(row) if row else None
        finally:
            await db.close()

    # ── Row mappers ──

    @staticmethod
    def _row_to_source(row) -> Source:
        return Source(
            id=row["id"],
            telegram_id=row["telegram_id"],
            type=row["type"],
            title=row["title"],
            username=row["username"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_message(row) -> Message:
        return Message(
            id=row["id"],
            source_id=row["source_id"],
            message_id=row["message_id"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            text=row["text"],
            reply_to_message_id=row["reply_to_message_id"],
            date=datetime.fromisoformat(row["date"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_digest(row) -> Digest:
        return Digest(
            id=row["id"],
            source_id=row["source_id"],
            week_start=datetime.fromisoformat(row["week_start"]),
            week_end=datetime.fromisoformat(row["week_end"]),
            content=row["content"],
            raw_response=row["raw_response"],
            message_count=row["message_count"],
            sent_message_id=row["sent_message_id"],
            created_at=row["created_at"],
        )
