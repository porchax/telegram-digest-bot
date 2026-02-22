import re

from bot.config import settings


def normalize_text(text: str) -> str | None:
    """Clean and truncate message text."""
    if not text:
        return None
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    # Truncate to configured max length
    if len(text) > settings.max_message_length:
        text = text[: settings.max_message_length] + "…"
    return text


def get_display_name(first_name: str | None, last_name: str | None) -> str | None:
    """Build a display name from first/last name."""
    parts = [p for p in (first_name, last_name) if p]
    return " ".join(parts) if parts else None
