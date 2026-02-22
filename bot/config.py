from typing import Annotated

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings


def _parse_int_list(v):
    if isinstance(v, str):
        return [int(x.strip()) for x in v.split(",") if x.strip()]
    if isinstance(v, int):
        return [v]
    return v


AdminIds = Annotated[list[int], BeforeValidator(_parse_int_list)]


class Settings(BaseSettings):
    telegram_bot_token: str
    admin_user_ids: AdminIds = []
    replicate_api_token: str
    replicate_model: str = "anthropic/claude-4.5-sonnet"
    replicate_max_tokens: int = 4096
    digest_day: int = 6
    digest_hour: int = 20
    digest_timezone: str = "Europe/Moscow"
    database_path: str = "data/bot.db"
    max_messages_per_prompt: int = 2000
    max_message_length: int = 500
    auto_pin_digest: bool = True

    model_config = {"env_file": ".env", "enable_decoding": False}


settings = Settings()
