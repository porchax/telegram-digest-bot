# CLAUDE.md — Telegram Digest Bot

## Описание проекта

Telegram-бот для автоматического формирования еженедельных дайджестов группового чата. Бот находится в группе (~10 человек), читает все сообщения, сохраняет их в БД, и раз в неделю генерирует структурированный отчёт с помощью Claude API, публикуя его в группу.

## Стек технологий

- **Язык:** Python 3.11+
- **Telegram:** aiogram 3.x (асинхронный фреймворк)
- **БД:** SQLite через aiosqlite (асинхронный драйвер)
- **LLM:** Anthropic Claude API (claude-sonnet-4-20250514)
- **Планировщик:** APScheduler (для еженедельной генерации дайджеста)
- **Конфигурация:** pydantic-settings + .env файл
- **Деплой:** Docker (опционально)

## Структура проекта

```
telegram-digest-bot/
├── CLAUDE.md
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── bot/
│   ├── __init__.py
│   ├── main.py              # Точка входа, запуск бота
│   ├── config.py             # Настройки из .env через pydantic-settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py         # Dataclass-модели (Message, Source, Digest)
│   │   ├── database.py       # Инициализация БД, миграции
│   │   └── repository.py     # CRUD-операции с сообщениями
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── messages.py       # Обработчик входящих сообщений группы
│   │   └── commands.py       # /digest, /status, /help и другие команды
│   ├── services/
│   │   ├── __init__.py
│   │   ├── collector.py      # Логика сбора и нормализации сообщений
│   │   ├── analyzer.py       # Взаимодействие с Claude API, промпты
│   │   ├── digest.py         # Формирование и отправка дайджеста
│   │   └── scheduler.py      # Планировщик еженедельной отправки
│   └── utils/
│       ├── __init__.py
│       ├── message_links.py  # Генерация ссылок на сообщения
│       └── text.py           # Утилиты для работы с текстом (чанки, очистка)
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_repository.py
    ├── test_analyzer.py
    └── test_digest.py
```

## Архитектура и поток данных

```
1. Пользователь пишет в группу
2. Telegram → aiogram handler (handlers/messages.py)
3. Handler → collector.py (нормализация) → repository.py (сохранение в SQLite)
4. По расписанию (воскресенье 20:00) или по команде /digest:
   4a. repository.py → получить сообщения за неделю
   4b. analyzer.py → сформировать промпт → отправить в Claude API
   4c. digest.py → отформатировать ответ → отправить в группу
```

## Схема базы данных

```sql
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,  -- chat_id группы или канала
    type TEXT NOT NULL CHECK(type IN ('group', 'channel')),
    title TEXT,
    username TEXT,  -- @username если есть (для публичных)
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    message_id INTEGER NOT NULL,          -- telegram message_id
    user_id INTEGER,
    user_name TEXT,                        -- display name автора
    text TEXT,
    reply_to_message_id INTEGER,          -- если это реплай
    date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, message_id)
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    content TEXT NOT NULL,                 -- итоговый текст дайджеста
    raw_response TEXT,                     -- сырой ответ от LLM
    message_count INTEGER,                -- сколько сообщений проанализировано
    sent_message_id INTEGER,              -- message_id отправленного дайджеста
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_source_date ON messages(source_id, date);
CREATE INDEX idx_messages_date ON messages(date);
```

## Конфигурация (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=123456789,987654321   # ID администраторов бота (через запятую)

# Anthropic
ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=4096

# Дайджест
DIGEST_DAY=6                # День недели (0=пн, 6=вс)
DIGEST_HOUR=20              # Час отправки (по UTC или по TZ)
DIGEST_TIMEZONE=Europe/Moscow

# БД
DATABASE_PATH=data/bot.db

# Лимиты
MAX_MESSAGES_PER_PROMPT=2000       # Макс. сообщений в один промпт
MAX_MESSAGE_LENGTH=500             # Обрезать длинные сообщения
```

## Детали реализации

### 1. config.py

Использовать `pydantic-settings` для валидации конфигурации:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    telegram_bot_token: str
    admin_user_ids: list[int] = []
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096
    digest_day: int = 6
    digest_hour: int = 20
    digest_timezone: str = "Europe/Moscow"
    database_path: str = "data/bot.db"
    max_messages_per_prompt: int = 2000
    max_message_length: int = 500

    model_config = {"env_file": ".env"}
```

### 2. Обработка входящих сообщений (handlers/messages.py)

- Бот должен работать с выключенным Privacy Mode (настроить через @BotFather → Bot Settings → Group Privacy → Turn off)
- Сохранять ВСЕ текстовые сообщения, подписи к медиа, пересланные сообщения
- Игнорировать: сервисные сообщения, сообщения от других ботов
- Нормализовать текст: убрать лишние пробелы, ограничить длину
- Сохранять reply_to_message_id для понимания цепочек дискуссий
- При первом сообщении из нового чата — автоматически создавать запись в sources

### 3. Генерация ссылок (utils/message_links.py)

Формат ссылок на сообщения в Telegram:

- **Публичная группа/канал** (есть @username): `https://t.me/{username}/{message_id}`
- **Приватная группа** (нет @username): `https://t.me/c/{chat_id_without_minus100}/{message_id}`
  - chat_id приватных групп начинается с `-100`, эту часть надо убрать для ссылки
  - Пример: chat_id = `-1001234567890` → ссылка `https://t.me/c/1234567890/42`

```python
def make_message_link(chat_id: int, message_id: int, username: str | None = None) -> str:
    if username:
        return f"https://t.me/{username}/{message_id}"
    # Приватная группа: убираем префикс -100
    clean_id = str(chat_id).replace("-100", "")
    return f"https://t.me/c/{clean_id}/{message_id}"
```

### 4. Анализ через Claude API (services/analyzer.py)

**Стратегия промптинга:**

Системный промпт:

```
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
```

Формат ответа LLM (запрашивать JSON):

```json
{
  "important_topics": [
    {
      "title": "Заголовок темы",
      "summary": "Описание сути обсуждения",
      "first_message_id": 12345,
      "participants": ["Имя1", "Имя2"]
    }
  ],
  "discussed_topics": [
    {
      "title": "Заголовок темы",
      "summary": "Описание сути обсуждения",
      "first_message_id": 12346,
      "participants": ["Имя1", "Имя3"],
      "message_count": 15
    }
  ],
  "week_stats": {
    "total_messages": 230,
    "active_users": 8,
    "most_active_user": "Имя1"
  }
}
```

**Формат входных данных для LLM:**

```
[2025-01-20 10:15] Иван (#msg:1234): Привет всем, давайте обсудим дедлайн по проекту
[2025-01-20 10:16] Мария (#msg:1235) [→1234]: Согласна, нужно определиться до пятницы
[2025-01-20 10:20] Пётр (#msg:1236): А что по бюджету?
```

Где `#msg:XXXX` — message_id для идентификации, `[→1234]` — реплай на сообщение 1234.

**Обработка больших объёмов:**

- Если сообщений > MAX_MESSAGES_PER_PROMPT: разбить на чанки по дням
- Сначала суммаризировать каждый день отдельно
- Затем из дневных саммари сформировать финальный недельный дайджест
- Это двухэтапный анализ: chunked summarization → final digest

### 5. Формирование дайджеста (services/digest.py)

Преобразовать JSON-ответ от LLM в красивое Telegram-сообщение с Markdown:

```
📋 *Дайджест недели: 13–19 января 2025*
📊 Сообщений: 230 | Активных участников: 8

🔴 *Важные темы:*

1️⃣ *Дедлайн по проекту*
Обсудили сроки, решили сдать до пятницы. Иван взял на себя координацию.
🔗 [Начало обсуждения](https://t.me/c/1234567890/1234)

2️⃣ *Новый дизайн лендинга*
Мария представила макеты, команда одобрила второй вариант.
🔗 [Начало обсуждения](https://t.me/c/1234567890/1567)

💬 *Обсуждаемые темы:*

1️⃣ *Выбор фреймворка для фронтенда* (15 сообщений)
Спор между React и Vue, в итоге склонились к React.
🔗 [Начало обсуждения](https://t.me/c/1234567890/1890)
```

Использовать `parse_mode="Markdown"` или `parse_mode="HTML"` при отправке. HTML надёжнее — в Markdown много edge cases с экранированием.

Рекомендация: использовать HTML формат:

```html
📋 <b>Дайджест недели: 13–19 января 2025</b> 📊 Сообщений: 230 | Активных
участников: 8 🔴 <b>Важные темы:</b>

1️⃣ <b>Дедлайн по проекту</b> Обсудили сроки, решили сдать до пятницы. 🔗
<a href="https://t.me/c/1234567890/1234">Начало обсуждения</a>
```

### 6. Команды бота (handlers/commands.py)

- `/digest` — принудительно сгенерировать дайджест за последние 7 дней (только для админов)
- `/digest N` — дайджест за последние N дней
- `/status` — статистика: сколько сообщений собрано, последний дайджест, следующий запланированный
- `/help` — справка по командам
- `/sources` — список подключённых групп/каналов (для будущего расширения)

Команды `/digest` и `/sources` доступны только пользователям из ADMIN_USER_IDS.

### 7. Планировщик (services/scheduler.py)

Использовать `apscheduler` с `AsyncIOScheduler`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone=settings.digest_timezone)
scheduler.add_job(
    generate_and_send_digest,
    CronTrigger(day_of_week=settings.digest_day, hour=settings.digest_hour),
    id="weekly_digest"
)
```

## Расширение: чтение каналов

Для будущей поддержки каналов:

1. Бота добавить как администратора канала (или подписать на канал-дискуссию)
2. Посты каналов приходят как `channel_post` в aiogram — отдельный handler
3. Сохранять в ту же таблицу messages, но с source_id канала
4. При генерации дайджеста: можно делать отдельные дайджесты по каждому каналу или объединённый
5. Добавить команды `/add_channel` и `/remove_channel` для управления

Ключевое отличие: в каналах нет дискуссий (если нет привязанной группы обсуждений), поэтому промпт для анализа каналов будет другим — фокус на контенте постов, а не на обсуждениях.

## Обработка ошибок

- Claude API недоступен → retry с exponential backoff (3 попытки), уведомить админа
- Невалидный JSON от LLM → попробовать распарсить с помощью `json.loads` с fallback на regex-парсинг, при неудаче — повторный запрос с уточнением
- Telegram rate limits → aiogram обрабатывает автоматически через `RetryAfter`
- БД locked → использовать WAL mode в SQLite (`PRAGMA journal_mode=WAL`)
- Пустая неделя (0 сообщений) → не отправлять дайджест, залогировать

## Логирование

Использовать `logging` модуль Python:

- INFO: запуск бота, генерация дайджеста, отправка сообщений
- WARNING: retry запросов к API, пустые недели
- ERROR: ошибки API, парсинга, отправки
- DEBUG: сохранение каждого сообщения (отключить в проде)

Формат: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

## Безопасность

- Не логировать содержимое сообщений в production (приватность группы)
- .env и data/bot.db добавить в .gitignore
- ADMIN_USER_IDS — единственные кто может вызывать /digest вручную
- Бот не должен отвечать на сообщения в группе кроме команд (не спамить)
- При деплое: ограничить доступ к файлу БД

## Тестирование

- `test_repository.py` — тесты CRUD операций с in-memory SQLite
- `test_analyzer.py` — тесты формирования промпта и парсинга JSON-ответа (мокать API)
- `test_digest.py` — тесты форматирования сообщений, генерации ссылок
- Использовать `pytest` + `pytest-asyncio`

## Порядок реализации

1. **Фаза 1:** config.py + database.py + models.py + repository.py (каркас + БД)
2. **Фаза 2:** handlers/messages.py + collector.py (сбор сообщений, запустить бота)
3. **Фаза 3:** analyzer.py + промпт (интеграция с Claude API)
4. **Фаза 4:** digest.py + форматирование + message_links.py (генерация красивого дайджеста)
5. **Фаза 5:** commands.py + scheduler.py (команды + автоматизация)
6. **Фаза 6:** тесты + Docker + README
7. **Фаза 7:** расширение на каналы

## Команды для начала работы

```bash
# Создать структуру
mkdir -p bot/{db,handlers,services,utils} tests data

# Установить зависимости
pip install aiogram aiosqlite anthropic apscheduler pydantic-settings python-dotenv

# Запуск
python -m bot.main

# Тесты
pytest tests/ -v
```

## Важные замечания

- В @BotFather обязательно отключить Group Privacy Mode, иначе бот не увидит сообщения
- Бот должен быть добавлен в группу как обычный участник (не админ, если не нужны каналы)
- SQLite + WAL mode достаточно для группы до 50 человек, для масштабирования — PostgreSQL
- Claude Sonnet — оптимальный баланс цены и качества для этой задачи
- Один запрос к Claude API за неделю стоит ~$0.01-0.10, это крайне дёшево

## Навыки и агенты

Перед написанием бэкенд-кода прочитай: `.claude/skills/backend-patterns.md`
Для архитектурных решений прочитай: `.claude/agents/architect.md`
Для понимания git flow: `.claude/skills/git-workflow-manager.md`
Для решения проблем и исправления багов: `.claude/agents/build-error-resolver.md`
Для использования актуальной документации используй context7 mcp
