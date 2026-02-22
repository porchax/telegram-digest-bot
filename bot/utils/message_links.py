def make_message_link(chat_id: int, message_id: int, username: str | None = None) -> str:
    """Generate a Telegram deep link to a specific message."""
    if username:
        return f"https://t.me/{username}/{message_id}"
    # Private group: strip the -100 prefix
    clean_id = str(chat_id).replace("-100", "")
    return f"https://t.me/c/{clean_id}/{message_id}"
