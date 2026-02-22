from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    admin_user_ids: list[int] = []
    replicate_api_token: str
    replicate_model: str = "anthropic/claude-4.5-sonnet"
    replicate_max_tokens: int = 4096
    digest_day: int = 6
    digest_hour: int = 20
    digest_timezone: str = "Europe/Moscow"
    database_path: str = "data/bot.db"
    max_messages_per_prompt: int = 2000
    max_message_length: int = 500

    model_config = {"env_file": ".env"}


settings = Settings()
