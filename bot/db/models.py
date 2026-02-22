from dataclasses import dataclass
from datetime import datetime


@dataclass
class Source:
    id: int | None
    telegram_id: int
    type: str  # 'group' | 'channel'
    title: str | None = None
    username: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


@dataclass
class Message:
    id: int | None
    source_id: int
    message_id: int
    user_id: int | None
    user_name: str | None
    text: str | None
    reply_to_message_id: int | None
    date: datetime
    created_at: datetime | None = None


@dataclass
class Digest:
    id: int | None
    source_id: int
    week_start: datetime
    week_end: datetime
    content: str
    raw_response: str | None = None
    message_count: int | None = None
    sent_message_id: int | None = None
    created_at: datetime | None = None
