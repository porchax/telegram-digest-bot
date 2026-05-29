# «Плакат недели» — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Раз в неделю публиковать вместе с дайджестом сатирический плакат-инфографику, сгенерированный `openai/gpt-image-2` через Replicate, помещая картинку над текстом дайджеста.

**Architecture:** Новый модуль `bot/services/image.py` с двумя функциями: `build_image_prompt` (отдельный LLM-вызов, превращает темы недели в англоязычный сатирический промпт) и `generate_poster` (вызов gpt-image-2, возвращает байты или `None`). Интеграция в `generate_and_send_digest`: при включённом флаге картинка генерируется после анализа и отправляется `send_photo` перед текстовым сообщением дайджеста. Любой сбой генерации картинки не блокирует публикацию дайджеста (graceful degradation).

**Tech Stack:** Python 3.11+, aiogram 3.x, replicate>=1.0 (`async_run`, `FileOutput.aread()`), pydantic-settings, pytest (asyncio_mode=auto).

**Спецификация:** `docs/superpowers/specs/2026-05-29-digest-poster-design.md`

---

## File Structure

- **Modify** `bot/config.py` — 4 новых поля настроек.
- **Modify** `.env.example` — задокументировать новые переменные.
- **Create** `bot/services/image.py` — генерация промпта и плаката.
- **Modify** `bot/services/digest.py` — интеграция в поток отправки.
- **Modify** `CLAUDE.md` — отразить новые настройки и UX-фичу.
- **Create** `tests/test_config.py` — дефолты новых настроек.
- **Create** `tests/test_image.py` — тесты `build_image_prompt` / `generate_poster`.
- **Modify** `tests/test_digest.py` — интеграционные тесты потока отправки.

---

## Task 1: Настройки конфигурации

**Files:**
- Modify: `bot/config.py:30-32`
- Modify: `.env.example`
- Test: `tests/test_config.py`

- [ ] **Step 1: Написать падающий тест**

Создать `tests/test_config.py`:

```python
from bot.config import Settings


def test_image_settings_defaults():
    # _env_file=None изолирует тест от локального .env, os.environ всё равно читается
    s = Settings(_env_file=None)
    assert s.generate_digest_image is False
    assert s.image_model == "openai/gpt-image-2"
    assert s.image_quality == "medium"
    assert s.image_output_format == "jpeg"
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'generate_digest_image'`

- [ ] **Step 3: Добавить поля в `Settings`**

В `bot/config.py` заменить блок:

```python
    auto_pin_digest: bool = True

    model_config = {"env_file": ".env", "enable_decoding": False}
```

на:

```python
    auto_pin_digest: bool = True
    generate_digest_image: bool = False
    image_model: str = "openai/gpt-image-2"
    image_quality: str = "medium"        # low | medium | high
    image_output_format: str = "jpeg"    # jpeg | png | webp

    model_config = {"env_file": ".env", "enable_decoding": False}
```

- [ ] **Step 4: Запустить тест — убедиться, что проходит**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Дополнить `.env.example`**

Добавить в `.env.example` после строки `AUTO_PIN_DIGEST=true` блок:

```env

# Генерация плаката недели (gpt-image-2 через Replicate, ~2 мин на картинку)
GENERATE_DIGEST_IMAGE=false
IMAGE_MODEL=openai/gpt-image-2
IMAGE_QUALITY=medium
IMAGE_OUTPUT_FORMAT=jpeg
```

- [ ] **Step 6: Коммит**

```bash
git add bot/config.py .env.example tests/test_config.py
git commit -m "feat: add config settings for weekly digest poster"
```

---

## Task 2: `build_image_prompt` в новом модуле `image.py`

**Files:**
- Create: `bot/services/image.py`
- Test: `tests/test_image.py`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_image.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.image import (
    DEFAULT_IMAGE_PROMPT,
    build_image_prompt,
    generate_poster,
)


@patch("bot.services.image._call_replicate", new_callable=AsyncMock)
async def test_build_image_prompt_returns_string(mock_call):
    mock_call.return_value = "A satirical infographic poster about a big code merge"
    data = {"important_topics": [{"title": "Большой мёрж"}], "discussed_topics": []}

    result = await build_image_prompt(data)

    assert isinstance(result, str)
    assert result.strip() != ""
    mock_call.assert_awaited_once()


@patch("bot.services.image._call_replicate", new_callable=AsyncMock)
async def test_build_image_prompt_truncates_to_limit(mock_call):
    mock_call.return_value = "x" * 5000
    data = {"important_topics": [{"title": "Тема"}], "discussed_topics": []}

    result = await build_image_prompt(data)

    assert len(result) <= 1000


@patch("bot.services.image._call_replicate", new_callable=AsyncMock)
async def test_build_image_prompt_default_on_error(mock_call):
    mock_call.side_effect = RuntimeError("LLM down")
    data = {"important_topics": [{"title": "Тема"}], "discussed_topics": []}

    result = await build_image_prompt(data)

    assert result == DEFAULT_IMAGE_PROMPT


async def test_build_image_prompt_default_when_no_topics():
    result = await build_image_prompt({"important_topics": [], "discussed_topics": []})
    assert result == DEFAULT_IMAGE_PROMPT
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `pytest tests/test_image.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.services.image'`

- [ ] **Step 3: Создать `bot/services/image.py` с `build_image_prompt`**

```python
import asyncio
import logging

import replicate

from bot.config import settings
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
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `pytest tests/test_image.py -v`
Expected: PASS (4 теста `build_image_prompt`); тесты `generate_poster` пока не добавлены.

- [ ] **Step 5: Коммит**

```bash
git add bot/services/image.py tests/test_image.py
git commit -m "feat: add build_image_prompt for satirical poster generation"
```

---

## Task 3: `generate_poster` в `image.py`

**Files:**
- Modify: `bot/services/image.py`
- Test: `tests/test_image.py`

- [ ] **Step 1: Дописать падающие тесты в `tests/test_image.py`**

Добавить в конец файла:

```python
@patch("bot.services.image.replicate.async_run", new_callable=AsyncMock)
async def test_generate_poster_success(mock_run):
    fake = MagicMock()
    fake.aread = AsyncMock(return_value=b"image-bytes")
    mock_run.return_value = fake

    result = await generate_poster("a funny poster")

    assert result == b"image-bytes"
    mock_run.assert_awaited_once()


@patch("bot.services.image.replicate.async_run", new_callable=AsyncMock)
async def test_generate_poster_list_output(mock_run):
    fake = MagicMock()
    fake.aread = AsyncMock(return_value=b"img")
    mock_run.return_value = [fake]

    result = await generate_poster("a funny poster")

    assert result == b"img"


@patch("bot.services.image.replicate.async_run", new_callable=AsyncMock)
@patch("bot.services.image.asyncio.sleep", new_callable=AsyncMock)
async def test_generate_poster_failure_returns_none(mock_sleep, mock_run):
    mock_run.side_effect = RuntimeError("api down")

    result = await generate_poster("a funny poster")

    assert result is None
    assert mock_run.await_count == 2  # _IMAGE_RETRIES
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `pytest tests/test_image.py -v`
Expected: FAIL — `ImportError: cannot import name 'generate_poster'` уже импортируется, но функция не определена → `AttributeError`/`TypeError` при вызове (функция отсутствует).

- [ ] **Step 3: Добавить `generate_poster` в `bot/services/image.py`**

Добавить в конец файла:

```python
# Картинка дорогая и долгая — мягкий retry без агрессивного backoff
_IMAGE_RETRIES = 2
_IMAGE_RETRY_DELAY = 5  # seconds


async def generate_poster(prompt: str) -> bytes | None:
    """Сгенерировать плакат через gpt-image-2. Вернуть байты или None при сбое."""
    last_error: Exception | None = None
    for attempt in range(_IMAGE_RETRIES):
        try:
            output = await replicate.async_run(
                settings.image_model,
                input={
                    "prompt": prompt,
                    "quality": settings.image_quality,
                    "output_format": settings.image_output_format,
                },
            )
            # gpt-image-2 может вернуть один FileOutput или список
            file_output = output[0] if isinstance(output, list) else output
            return await file_output.aread()
        except Exception as e:
            last_error = e
            logger.warning(
                "Poster generation failed (attempt %d/%d): %s",
                attempt + 1, _IMAGE_RETRIES, e,
            )
            if attempt < _IMAGE_RETRIES - 1:
                await asyncio.sleep(_IMAGE_RETRY_DELAY)

    logger.error("Poster generation failed after %d attempts: %s", _IMAGE_RETRIES, last_error)
    return None
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `pytest tests/test_image.py -v`
Expected: PASS (7 тестов)

- [ ] **Step 5: Коммит**

```bash
git add bot/services/image.py tests/test_image.py
git commit -m "feat: add generate_poster via gpt-image-2"
```

---

## Task 4: Интеграция в `generate_and_send_digest`

**Files:**
- Modify: `bot/services/digest.py:1-12` (импорты)
- Modify: `bot/services/digest.py:240-256` (поток отправки)
- Test: `tests/test_digest.py`

- [ ] **Step 1: Дописать падающие интеграционные тесты в `tests/test_digest.py`**

Добавить в конец файла:

```python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import bot.services.digest as digest_mod
from bot.db.models import Message
from bot.db.repository import Repository

_VALID_DATA = {
    "important_topics": [
        {"title": "T", "summary": "S", "first_message_id": 1, "participants": []}
    ],
    "discussed_topics": [],
    "week_stats": {"total_messages": 1, "active_users": 1, "most_active_user": "Alice"},
}


async def _seed_group_with_message():
    repo = Repository()
    source = await repo.get_or_create_source(-100123, "group", title="Test")
    await repo.save_message(
        Message(
            id=None,
            source_id=source.id,
            message_id=1,
            user_id=42,
            user_name="Alice",
            text="hi",
            reply_to_message_id=None,
            date=datetime.now(UTC) - timedelta(days=1),
        )
    )
    return source


@patch("bot.services.digest.generate_poster", new_callable=AsyncMock)
@patch("bot.services.digest.build_image_prompt", new_callable=AsyncMock)
@patch("bot.services.digest.analyze_messages", new_callable=AsyncMock)
async def test_digest_sends_poster_when_enabled(mock_analyze, mock_prompt, mock_poster):
    source = await _seed_group_with_message()
    mock_analyze.return_value = _VALID_DATA
    mock_prompt.return_value = "funny poster prompt"
    mock_poster.return_value = b"\xff\xd8\xff fake jpeg"

    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=555)

    with patch.object(digest_mod.settings, "generate_digest_image", True):
        await digest_mod.generate_and_send_digest(bot, source.telegram_id)

    mock_poster.assert_awaited_once()
    bot.send_photo.assert_awaited_once()
    bot.send_message.assert_awaited()


@patch("bot.services.digest.generate_poster", new_callable=AsyncMock)
@patch("bot.services.digest.build_image_prompt", new_callable=AsyncMock)
@patch("bot.services.digest.analyze_messages", new_callable=AsyncMock)
async def test_digest_skips_poster_when_disabled(mock_analyze, mock_prompt, mock_poster):
    source = await _seed_group_with_message()
    mock_analyze.return_value = _VALID_DATA

    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=556)

    with patch.object(digest_mod.settings, "generate_digest_image", False):
        await digest_mod.generate_and_send_digest(bot, source.telegram_id)

    mock_poster.assert_not_awaited()
    bot.send_photo.assert_not_called()
    bot.send_message.assert_awaited()


@patch("bot.services.digest.generate_poster", new_callable=AsyncMock)
@patch("bot.services.digest.build_image_prompt", new_callable=AsyncMock)
@patch("bot.services.digest.analyze_messages", new_callable=AsyncMock)
async def test_digest_sent_when_poster_fails(mock_analyze, mock_prompt, mock_poster):
    source = await _seed_group_with_message()
    mock_analyze.return_value = _VALID_DATA
    mock_prompt.return_value = "prompt"
    mock_poster.return_value = None  # генерация картинки провалилась

    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=557)

    with patch.object(digest_mod.settings, "generate_digest_image", True):
        await digest_mod.generate_and_send_digest(bot, source.telegram_id)

    bot.send_photo.assert_not_called()
    bot.send_message.assert_awaited()  # дайджест всё равно ушёл
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `pytest tests/test_digest.py -k "poster" -v`
Expected: FAIL — `AttributeError: module 'bot.services.digest' has no attribute 'build_image_prompt'` (импорт ещё не добавлен).

- [ ] **Step 3: Обновить импорты в `bot/services/digest.py`**

Заменить:

```python
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
```

на:

```python
from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
```

И заменить:

```python
from bot.services.analyzer import analyze_messages
```

на:

```python
from bot.services.analyzer import analyze_messages
from bot.services.image import build_image_prompt, generate_poster
```

- [ ] **Step 4: Вставить генерацию плаката после заполнения статистики**

В `generate_and_send_digest` найти блок:

```python
    stats.setdefault(
        "active_users",
        len({m.user_id for m in messages if m.user_id}),
    )

    content = format_digest_html(data, week_start, week_end, chat_id, source.username)
```

и вставить между `setdefault(...)` и `content = ...`:

```python

    # Сгенерировать плакат недели (опционально, не должен блокировать дайджест)
    poster: bytes | None = None
    if settings.generate_digest_image:
        if progress_message:
            try:
                await progress_message.edit_text("🎨 Рисую плакат недели (~2 мин)…")
            except Exception:
                logger.debug("Could not update progress message for poster step")
        image_prompt = await build_image_prompt(data, source.type)
        poster = await generate_poster(image_prompt)
```

- [ ] **Step 5: Отправить фото перед текстом дайджеста**

Найти блок:

```python
    # Send message first, then save to DB (avoids orphaned records)
    keyboard_placeholder = build_digest_keyboard(0)
```

и вставить перед строкой `# Send message first`:

```python
    # Плакат публикуется НАД текстом дайджеста, если сгенерирован
    if poster:
        try:
            await bot.send_photo(
                chat_id,
                BufferedInputFile(poster, filename=f"poster.{settings.image_output_format}"),
            )
        except Exception:
            logger.exception("Failed to send poster to chat %d", chat_id)

```

- [ ] **Step 6: Запустить тесты — убедиться, что проходят**

Run: `pytest tests/test_digest.py -k "poster" -v`
Expected: PASS (3 теста)

- [ ] **Step 7: Коммит**

```bash
git add bot/services/digest.py tests/test_digest.py
git commit -m "feat: publish weekly poster above digest text"
```

---

## Task 5: Обновить документацию проекта

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Добавить новые переменные в блок конфигурации `CLAUDE.md`**

В `CLAUDE.md` в блоке ```env (раздел «Конфигурация (.env)») после строки `AUTO_PIN_DIGEST=true` добавить:

```env
GENERATE_DIGEST_IMAGE=false
IMAGE_MODEL=openai/gpt-image-2
IMAGE_QUALITY=medium
IMAGE_OUTPUT_FORMAT=jpeg
```

- [ ] **Step 2: Добавить пункт в раздел «UX-фичи»**

В список «UX-фичи» добавить пункт:

```markdown
- **Плакат недели** — при `GENERATE_DIGEST_IMAGE=true` над дайджестом публикуется сатирический плакат-инфографика (gpt-image-2 через Replicate, ~2 мин). При сбое генерации дайджест выходит без картинки.
```

- [ ] **Step 3: Коммит**

```bash
git add CLAUDE.md
git commit -m "docs: document weekly poster feature in CLAUDE.md"
```

---

## Task 6: Финальная проверка всего набора тестов

- [ ] **Step 1: Прогнать все тесты**

Run: `pytest tests/ -v`
Expected: PASS — 43 существующих + 4 (config) + 7 (image) + 3 (digest poster) = 57 тестов, 0 warnings.

- [ ] **Step 2: Если есть падения — исправить и повторить**

Run: `pytest tests/ -v`
Expected: все зелёные.

---

## Self-Review (выполнено при написании плана)

- **Покрытие спеки:** поток данных → Task 4; `image.py` (build_image_prompt + generate_poster) → Tasks 2-3; конфиг → Task 1; обработка ошибок (дефолтный промпт, None при сбое картинки, try/except на send_photo, дайджест без картинки) → Tasks 2-4; БД без изменений → не требует задач; область применения (глобальный флаг, все источники) → Task 4 через `settings.generate_digest_image`; тесты → Tasks 2-4; auto-pin дайджеста не меняется (фото отправляется отдельным сообщением, пин остаётся на тексте дайджеста) → Task 4.
- **Плейсхолдеры:** отсутствуют, весь код приведён.
- **Согласованность имён:** `build_image_prompt`, `generate_poster`, `DEFAULT_IMAGE_PROMPT`, `_IMAGE_RETRIES`, поля `generate_digest_image` / `image_model` / `image_quality` / `image_output_format` используются единообразно во всех задачах и тестах.

## Риск, требующий проверки при реализации

Точные имена входных параметров `openai/gpt-image-2` на Replicate (`quality`, `output_format`) взяты из документации OpenAI gpt-image-2. Если при первом реальном запуске Replicate вернёт ошибку валидации входа — свериться со схемой модели (`GET https://api.replicate.com/v1/models/openai/gpt-image-2` → `latest_version.openapi_schema.components.schemas.Input.properties`) и скорректировать ключи в `input={...}` функции `generate_poster`. На graceful degradation это не влияет: при ошибке вернётся `None`, дайджест выйдет без картинки.
