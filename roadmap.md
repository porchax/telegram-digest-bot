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
- [ ] `bot/services/collector.py` — нормализация текста
- [ ] `bot/handlers/messages.py` — обработчик входящих сообщений
- [ ] `bot/main.py` — точка входа, запуск бота
- [ ] Тест: бот запускается, сохраняет сообщения в БД

## Фаза 3: Интеграция с Claude API
- [ ] `bot/services/analyzer.py` — промпт, запрос к API, парсинг JSON
- [ ] `bot/utils/text.py` — разбиение на чанки, очистка текста
- [ ] Двухэтапный анализ для больших объёмов

## Фаза 4: Формирование дайджеста
- [ ] `bot/utils/message_links.py` — генерация ссылок на сообщения
- [ ] `bot/services/digest.py` — форматирование HTML, отправка в группу

## Фаза 5: Команды + планировщик
- [ ] `bot/handlers/commands.py` — /digest, /status, /help, /sources
- [ ] `bot/services/scheduler.py` — APScheduler, еженедельная отправка

## Фаза 6: Тесты + Docker + README
- [ ] `tests/conftest.py` — фикстуры
- [ ] `tests/test_repository.py`
- [ ] `tests/test_analyzer.py`
- [ ] `tests/test_digest.py`
- [ ] `Dockerfile` + `docker-compose.yml`
- [ ] `README.md`

## Фаза 7: Расширение на каналы
- [ ] Обработчик `channel_post`
- [ ] Команды `/add_channel`, `/remove_channel`
- [ ] Отдельный промпт для анализа каналов
