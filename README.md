# Telegram Digest Bot

Telegram-бот для автоматического формирования еженедельных дайджестов группового чата. Анализирует сообщения за неделю с помощью Replicate API (Claude 4.5 Sonnet) и публикует структурированный отчёт в группу.

## Возможности

- Сбор всех текстовых сообщений группы в SQLite
- Еженедельная генерация дайджеста по расписанию
- Выделение важных и обсуждаемых тем с ссылками на сообщения
- Ручная генерация дайджеста через команду `/digest`
- Двухэтапный анализ для больших объёмов сообщений

## Быстрый старт

### Предварительные требования

- Python 3.11+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- Replicate API Token ([replicate.com](https://replicate.com))

### Установка

```bash
git clone <repo-url>
cd telegram-digest-bot
pip install -r requirements.txt
cp .env.example .env
# Заполнить .env своими токенами
```

### Настройка бота

1. В @BotFather отключить Group Privacy Mode: Bot Settings → Group Privacy → Turn off
2. Добавить бота в группу

### Запуск

```bash
python -m bot.main
```

## Команды

| Команда | Описание | Доступ |
|---------|----------|--------|
| `/digest` | Дайджест за 7 дней | Админы |
| `/digest N` | Дайджест за N дней | Админы |
| `/status` | Статистика бота | Все |
| `/help` | Справка | Все |
| `/sources` | Список чатов | Админы |

## Конфигурация

Все настройки задаются через `.env` файл. См. [.env.example](.env.example).

## Деплой на Railway

1. Создать проект на [Railway](https://railway.app)
2. Подключить репозиторий
3. Добавить переменные окружения из `.env.example`
4. Создать Volume и примонтировать к `/app/data` для хранения SQLite БД

Конфигурация Railway описана в `railway.toml`.

## Тесты

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Стек

- **aiogram 3.x** — Telegram Bot API
- **aiosqlite** — асинхронная SQLite
- **Replicate API** — Claude 4.5 Sonnet для анализа
- **APScheduler** — планировщик еженедельных дайджестов
- **pydantic-settings** — конфигурация
