# Roadmap — Telegram Digest Bot

## Фаза 1: Каркас + БД
- [x] Инициализация git-репозитория
- [x] Создание структуры проекта (директории, `__init__.py`)
- [x] `requirements.txt` / `pyproject.toml`
- [x] `.env.example`, `.gitignore`
- [x] `bot/config.py` — pydantic-settings конфигурация
- [x] `bot/db/models.py` — dataclass-модели (Message, Source, Digest)
- [x] `bot/db/database.py` — инициализация SQLite + WAL mode + миграции
- [x] `bot/db/repository.py` — CRUD-операции с сообщениями

## Фаза 2: Сбор сообщений
- [x] `bot/services/collector.py` — нормализация текста
- [x] `bot/handlers/messages.py` — обработчик входящих сообщений
- [x] `bot/main.py` — точка входа, запуск бота
- [x] Тест: бот запускается, сохраняет сообщения в БД

## Фаза 3: Интеграция с Replicate API
- [x] `bot/services/analyzer.py` — промпт, запрос к API, парсинг JSON
- [x] `bot/utils/text.py` — разбиение на чанки, очистка текста
- [x] Двухэтапный анализ для больших объёмов

## Фаза 4: Формирование дайджеста
- [x] `bot/utils/message_links.py` — генерация ссылок на сообщения
- [x] `bot/services/digest.py` — форматирование HTML, отправка в группу

## Фаза 5: Команды + планировщик
- [x] `bot/handlers/commands.py` — /digest, /status, /help, /sources
- [x] `bot/services/scheduler.py` — APScheduler, еженедельная отправка

## Фаза 6: Тесты + Railway + README
- [x] `tests/conftest.py` — фикстуры
- [x] `tests/test_repository.py`
- [x] `tests/test_analyzer.py`
- [x] `tests/test_digest.py`
- [x] `railway.toml`
- [x] `README.md`

## Фаза 7: Расширение на каналы
- [ ] Обработчик `channel_post`
- [ ] Команды `/add_channel`, `/remove_channel`
- [ ] Отдельный промпт для анализа каналов
