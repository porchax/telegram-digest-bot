# CLAUDE.md — Telegram Digest Bot

## Описание проекта

Telegram-бот для автоматического формирования еженедельных дайджестов группового чата. Бот находится в группе (~10 человек), читает все сообщения, сохраняет их в БД, и раз в неделю генерирует структурированный отчёт с помощью Replicate API (Claude 4.5 Sonnet), публикуя его в группу.

## Стек технологий

- **Язык:** Python 3.11+
- **Telegram:** aiogram 3.x (асинхронный фреймворк)
- **БД:** SQLite через aiosqlite (singleton connection, WAL mode)
- **LLM:** Replicate API (Claude 4.5 Sonnet) — async вызовы через `replicate.async_run()`
- **Планировщик:** APScheduler (для еженедельной генерации дайджеста)
- **Конфигурация:** pydantic-settings + .env файл
- **Деплой:** Railway

## Структура проекта

```
telegram-digest-bot/
├── CLAUDE.md
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── railway.toml
├── docs/
│   └── USAGE.md              # Инструкция по использованию бота
├── bot/
│   ├── __init__.py
│   ├── main.py              # Точка входа, профиль бота, запуск
│   ├── config.py             # Настройки из .env через pydantic-settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py         # Dataclass-модели (Message, Source, Digest)
│   │   ├── database.py       # Singleton connection, инициализация БД
│   │   └── repository.py     # CRUD-операции (messages, sources, digests)
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── messages.py       # Входящие сообщения + edited + welcome
│   │   ├── commands.py       # /digest, /status, /help, /sources, /add_channel, /remove_channel
│   │   └── callbacks.py      # Inline-кнопки навигации по дайджесту
│   ├── services/
│   │   ├── __init__.py
│   │   ├── collector.py      # Нормализация текста, display name
│   │   ├── analyzer.py       # Replicate API: async_run, retry, JSON-парсинг
│   │   ├── digest.py         # Форматирование, blockquotes, keyboard, auto-pin
│   │   └── scheduler.py      # Планировщик + уведомление админов при ошибках
│   └── utils/
│       ├── __init__.py
│       ├── message_links.py  # Генерация ссылок на сообщения (prefix-safe)
│       └── text.py           # Утилиты: format_message, chunk_by_day
└── tests/
    ├── __init__.py
    ├── conftest.py            # Temp DB, singleton reset, cleanup
    ├── test_repository.py     # CRUD + новые методы (12 тестов)
    ├── test_analyzer.py       # Промпты, JSON-парсинг, retry (13 тестов)
    └── test_digest.py         # Форматирование, blockquotes, truncate (18 тестов)
```

## Архитектура и поток данных

```
1. Пользователь пишет/редактирует сообщение в группу
2. Telegram → aiogram handler (handlers/messages.py)
3. Handler → collector.py (нормализация) → repository.py (save/update в SQLite)
4. По расписанию (воскресенье 20:00) или по команде /digest:
   4a. repository.py → получить сообщения за период
   4b. analyzer.py → async_run Replicate API (retry + backoff)
   4c. digest.py → format HTML + blockquotes → send + keyboard + auto-pin
5. Пользователь нажимает inline-кнопку → callbacks.py → edit_message_text
```

## Ключевые архитектурные решения

### Singleton DB Connection
`database.py` хранит одно подключение (`_connection`). Все методы Repository используют `await get_connection()` без open/close. Закрытие — при shutdown через `close_connection()`. Для тестов: `reset_connection()` сбрасывает синглтон.

### Async Replicate API
`analyzer.py` использует `replicate.async_run()` (не блокирующий `replicate.run()`). Retry с backoff: 3 попытки с задержками 2s, 5s, 10s. При полном отказе — возвращает пустой результат, не крашит бота.

### JSON-парсинг ответов LLM
Три стратегии: прямой `json.loads()` → markdown code block → balanced brace parser (не greedy regex). Balanced parser находит первый валидный `{...}` блок с корректной вложенностью.

### Send-before-save
Дайджест отправляется в Telegram ДО записи в БД. Это предотвращает "дайджесты-призраки" (запись есть, сообщение не отправлено). Keyboard обновляется после получения digest_id.

### Message Length Safety
`_truncate_html()` обрезает сообщение до 4096 символов (лимит Telegram) с пометкой "…обрезано".

## Схема базы данных

```sql
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('group', 'channel')),
    title TEXT,
    username TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    message_id INTEGER NOT NULL,
    user_id INTEGER,
    user_name TEXT,
    text TEXT,
    reply_to_message_id INTEGER,
    date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, message_id)
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    content TEXT NOT NULL,
    raw_response TEXT,            -- JSON от LLM (json.dumps)
    message_count INTEGER,
    sent_message_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_source_date ON messages(source_id, date);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date);
```

## Конфигурация (.env)

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=123456789,987654321
REPLICATE_API_TOKEN=your_replicate_token_here
REPLICATE_MODEL=anthropic/claude-4.5-sonnet
REPLICATE_MAX_TOKENS=4096
DIGEST_DAY=6
DIGEST_HOUR=20
DIGEST_TIMEZONE=Europe/Moscow
DATABASE_PATH=data/bot.db
MAX_MESSAGES_PER_PROMPT=2000
MAX_MESSAGE_LENGTH=500
AUTO_PIN_DIGEST=true
GENERATE_DIGEST_IMAGE=false
IMAGE_MODEL=openai/gpt-image-2
IMAGE_QUALITY=medium
IMAGE_OUTPUT_FORMAT=jpeg
```

## UX-фичи

- **Меню команд** — `set_my_commands` при старте, видно в интерфейсе Telegram
- **Профиль бота** — `set_my_description` / `set_my_short_description`
- **Expandable blockquotes** — описание тем свёрнуто, раскрывается по тапу
- **Inline keyboard** — переключение между видами: Важные / Обсуждаемые / Статистика / Полный
- **Auto-pin** — дайджест закрепляется в чате (настраивается через `AUTO_PIN_DIGEST`)
- **Progress indicator** — при `/digest`: "⏳ Генерирую..." → "📨 Найдено N сообщений..." → "✅ Отправлен!"
- **Welcome message** — при добавлении бота в группу
- **Edited messages** — обновление текста в БД при редактировании
- **Плакат недели** — при `GENERATE_DIGEST_IMAGE=true` над дайджестом публикуется сатирический плакат-инфографика (gpt-image-2 через Replicate, ~2 мин). При сбое генерации дайджест выходит без картинки.

## Обработка ошибок

- Replicate API → retry с exponential backoff (2s, 5s, 10s), при отказе — пустой результат + лог
- Невалидный JSON от LLM → 3 стратегии парсинга, при неудаче — retry prompt, fallback на пустой результат
- Telegram rate limits → aiogram `RetryAfter`
- Telegram message too long → `_truncate_html()` до 4096 символов
- Отправка дайджеста → try/except, прогресс "❌ Не удалось отправить"
- Auto-pin без прав → silent warning в логах
- Callback на старое сообщение → "Не удалось обновить сообщение"
- Scheduled digest failure → уведомление админов в личку
- Админ-команды без прав → "⛔ У вас нет прав для этой команды"

## Тестирование

43 теста, 0 warnings:
- `test_repository.py` (12) — CRUD: sources, messages, digests + update_message_text, set_source_active
- `test_analyzer.py` (13) — format_message, JSON-парсинг (5 стратегий), API failure, retry
- `test_digest.py` (18) — format HTML, blockquotes, partial formatters, truncate, escaping, edge cases

```bash
pytest tests/ -v
```

## Команды для разработки

```bash
pip install -e ".[dev]"        # Установка с dev-зависимостями
python -m bot.main             # Запуск бота
pytest tests/ -v               # Тесты
```

## Навыки и агенты

Перед написанием бэкенд-кода прочитай: `.claude/skills/backend-patterns.md`
Для архитектурных решений прочитай: `.claude/agents/architect.md`
Для понимания git flow: `.claude/skills/git-workflow-manager.md`
Для решения проблем и исправления багов: `.claude/agents/build-error-resolver.md`
Для использования актуальной документации используй context7 mcp
