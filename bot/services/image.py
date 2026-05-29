import logging

from bot.services.analyzer import _call_replicate

logger = logging.getLogger(__name__)

# Промпт gpt-image ограничен ~1000 символами
_MAX_PROMPT_CHARS = 1000

# Безопасный дефолт, если LLM недоступен или тем нет
DEFAULT_IMAGE_PROMPT = (
    "A funny satirical infographic poster summarizing a week in a group chat. "
    "Caricature style, exaggerated cartoon characters, bold tabloid-style headlines, "
    "vibrant colors, playful absurd humor, friendly tone."
)

IMAGE_PROMPT_SYSTEM = """\
Ты — сатирический карикатурист и арт-директор политического плаката. По темам недели
из группового чата ты придумываешь концепцию забавного иллюстрированного
плаката-инфографики с выраженной сатирой и актуальным юмором.

Требования к стилю:
- гипербола и шарж: преувеличивай черты, доводи ситуации до абсурда;
- актуальные мемы и узнаваемые тропы интернет-культуры, ирония, лёгкий троллинг тем;
- визуальные гэги, контраст пафоса и бытовухи, тон «обложка таблоида / агитплакат»;
- доброжелательно, без оскорблений и токсичности — это дружеский подкол.

Выведи ТОЛЬКО готовый промпт для модели генерации изображений, на АНГЛИЙСКОМ языке,
одним абзацем, без markdown, без кавычек, без пояснений. Не длиннее 900 символов."""


def _collect_titles(data: dict) -> list[str]:
    """Собрать заголовки тем недели для подачи в промпт."""
    titles: list[str] = []
    for key in ("important_topics", "discussed_topics"):
        for topic in data.get(key, []):
            title = topic.get("title")
            if title:
                titles.append(title)
    return titles


async def build_image_prompt(data: dict, source_type: str = "group") -> str:
    """Сгенерировать англоязычный сатирический промпт плаката из тем недели.

    При отсутствии тем или сбое LLM возвращает DEFAULT_IMAGE_PROMPT.
    """
    titles = _collect_titles(data)
    if not titles:
        return DEFAULT_IMAGE_PROMPT

    bullet_list = "\n".join(f"- {t}" for t in titles)
    user_prompt = (
        f"Темы недели в {'канале' if source_type == 'channel' else 'чате'}:\n"
        f"{bullet_list}\n\n"
        "Придумай по этим темам концепцию плаката и выведи промпт."
    )

    try:
        response = await _call_replicate(IMAGE_PROMPT_SYSTEM, user_prompt)
    except Exception:
        logger.exception("Failed to build image prompt, using default")
        return DEFAULT_IMAGE_PROMPT

    prompt = response.strip()
    if not prompt:
        return DEFAULT_IMAGE_PROMPT
    return prompt[:_MAX_PROMPT_CHARS]


# Implemented in Task 3
async def generate_poster(prompt: str) -> bytes | None:
    raise NotImplementedError
