from datetime import datetime
from itertools import groupby

from bot.db.models import Message


def format_message(msg: Message) -> str:
    """Format a single message for the LLM prompt."""
    date_str = msg.date.strftime("%Y-%m-%d %H:%M")
    name = msg.user_name or "Unknown"
    reply = f" [→{msg.reply_to_message_id}]" if msg.reply_to_message_id else ""
    return f"[{date_str}] {name} (#msg:{msg.message_id}){reply}: {msg.text}"


def format_messages(messages: list[Message]) -> str:
    """Format a list of messages into a prompt string."""
    return "\n".join(format_message(m) for m in messages)


def chunk_by_day(messages: list[Message]) -> list[list[Message]]:
    """Split messages into per-day chunks."""
    def day_key(msg: Message) -> str:
        return msg.date.strftime("%Y-%m-%d")

    return [list(group) for _, group in groupby(messages, key=day_key)]
