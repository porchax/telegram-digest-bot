import json
import logging
import re

import replicate

from bot.config import settings
from bot.db.models import Message
from bot.utils.text import chunk_by_day, format_messages

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Ты — аналитик групповых чатов. Твоя задача — проанализировать переписку за неделю и выделить ключевые темы.

Правила:
1. Выдели 3-6 "Важных тем" — решения, договорённости, значимые новости, важные вопросы
2. Выдели 3-6 "Обсуждаемых тем" — что вызвало активную дискуссию, споры, длинные треды
3. Для каждой темы укажи:
   - Краткий заголовок (3-7 слов)
   - Описание (1-3 предложения, суть обсуждения и итог если есть)
   - message_id первого сообщения, с которого началась тема
4. Если тем меньше 3 в какой-то категории — это нормально, не выдумывай
5. Отвечай строго в JSON формате

Формат ответа:
{
  "important_topics": [
    {"title": "...", "summary": "...", "first_message_id": 12345, "participants": ["Имя1"]}
  ],
  "discussed_topics": [
    {"title": "...", "summary": "...", "first_message_id": 12346, "participants": ["Имя1"], "message_count": 15}
  ],
  "week_stats": {
    "total_messages": 230,
    "active_users": 8,
    "most_active_user": "Имя1"
  }
}"""

DAY_SUMMARY_SYSTEM_PROMPT = """\
Ты — аналитик групповых чатов. Кратко суммаризируй переписку за день.
Выдели основные темы, решения и дискуссии. Укажи message_id ключевых сообщений.
Формат: свободный текст, 3-10 предложений."""

MAX_RETRIES = 3


async def _call_replicate(system_prompt: str, user_prompt: str) -> str:
    """Call Replicate API and return the text response."""
    prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"

    output = replicate.run(
        settings.replicate_model,
        input={
            "prompt": prompt,
            "max_tokens": settings.replicate_max_tokens,
        },
    )

    # Replicate returns an iterator of string chunks
    return "".join(output)


def _parse_json(text: str) -> dict | None:
    """Try to extract JSON from LLM response."""
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON block from markdown
    match = re.search(r"```(?:json)?\s*(\{.*?})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } pair
    match = re.search(r"\{.*}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


async def analyze_messages(messages: list[Message]) -> dict:
    """Analyze messages and return structured digest data.

    Uses two-stage analysis if messages exceed MAX_MESSAGES_PER_PROMPT.
    """
    if not messages:
        return {
            "important_topics": [],
            "discussed_topics": [],
            "week_stats": {
                "total_messages": 0,
                "active_users": 0,
                "most_active_user": None,
            },
        }

    if len(messages) <= settings.max_messages_per_prompt:
        return await _single_pass(messages)

    return await _chunked_pass(messages)


async def _single_pass(messages: list[Message]) -> dict:
    """Analyze all messages in a single LLM call."""
    prompt = format_messages(messages)

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("Analyzing %d messages (attempt %d)", len(messages), attempt)
        response = await _call_replicate(SYSTEM_PROMPT, prompt)

        result = _parse_json(response)
        if result:
            return result

        logger.warning("Failed to parse JSON on attempt %d", attempt)

    logger.error("All %d attempts to parse JSON failed, returning raw", MAX_RETRIES)
    return {
        "important_topics": [],
        "discussed_topics": [],
        "week_stats": {
            "total_messages": len(messages),
            "active_users": len({m.user_id for m in messages if m.user_id}),
            "most_active_user": None,
        },
        "_raw_response": response,
    }


async def _chunked_pass(messages: list[Message]) -> dict:
    """Two-stage analysis: summarize each day, then combine."""
    days = chunk_by_day(messages)
    summaries: list[str] = []

    for day_messages in days:
        date_label = day_messages[0].date.strftime("%Y-%m-%d")
        logger.info("Summarizing day %s (%d messages)", date_label, len(day_messages))

        prompt = format_messages(day_messages)
        summary = await _call_replicate(DAY_SUMMARY_SYSTEM_PROMPT, prompt)
        summaries.append(f"## {date_label}\n{summary}")

    combined = "\n\n".join(summaries)
    final_prompt = (
        f"Ниже — краткие суммари переписки по дням за неделю. "
        f"Сформируй из них единый недельный дайджест.\n\n{combined}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("Final digest synthesis (attempt %d)", attempt)
        response = await _call_replicate(SYSTEM_PROMPT, final_prompt)

        result = _parse_json(response)
        if result:
            return result

        logger.warning("Failed to parse final JSON on attempt %d", attempt)

    logger.error("Chunked analysis failed to produce valid JSON")
    return {
        "important_topics": [],
        "discussed_topics": [],
        "week_stats": {
            "total_messages": len(messages),
            "active_users": len({m.user_id for m in messages if m.user_id}),
            "most_active_user": None,
        },
        "_raw_response": response,
    }
