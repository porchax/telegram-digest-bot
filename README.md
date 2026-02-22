# Telegram Digest Bot

Telegram-бот для автоматического формирования еженедельных дайджестов группового чата. Бот читает все сообщения, сохраняет в базу данных и раз в неделю генерирует структурированный отчёт с ключевыми темами с помощью LLM (Claude через Replicate API).

## Возможности

- **Автоматический сбор сообщений** — текст, подписи к медиа, реплаи, отредактированные сообщения
- **Еженедельный дайджест по расписанию** — настраиваемый день и время (по умолчанию воскресенье 20:00)
- **Ручная генерация** — команда `/digest` для немедленного создания дайджеста
- **Интерактивный дайджест** — inline-кнопки для переключения между видами (Важные / Обсуждаемые / Статистика / Полный)
- **Expandable blockquotes** — компактный вид на мобильных, раскрытие по тапу
- **Автозакрепление** — дайджест автоматически закрепляется в чате
- **Поддержка каналов** — отслеживание постов каналов с отдельным промптом
- **Ссылки на сообщения** — каждая тема содержит кликабельную ссылку на начало обсуждения
- **Двухэтапный анализ** — автоматическое разбиение больших объёмов сообщений на чанки

## Пример дайджеста

```
📋 Дайджест недели: 13–19 января 2025
📊 Сообщений: 230 | Активных участников: 8

🔴 Важные темы:

1️⃣ Дедлайн по проекту
  ▸ Обсудили сроки, решили сдать до пятницы. Иван взял координацию.
  🔗 Начало обсуждения

💬 Обсуждаемые темы:

1️⃣ Выбор фреймворка (15 сообщений)
  ▸ Спор между React и Vue, склонились к React.
  🔗 Начало обсуждения

[ 🔴 Важные | 💬 Обсуждаемые | 📊 Статистика | 📋 Полный ]
```

## Быстрый старт

### 1. Создание бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot` и следуйте инструкциям
3. Сохраните полученный токен
4. **Важно:** зайдите в `Bot Settings → Group Privacy → Turn off`

### 2. Получение Replicate API ключа

1. Зарегистрируйтесь на [replicate.com](https://replicate.com)
2. Перейдите в [API tokens](https://replicate.com/account/api-tokens)
3. Создайте новый токен

### 3. Установка и запуск

```bash
git clone https://github.com/your-username/telegram-digest-bot.git
cd telegram-digest-bot

# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установить зависимости
pip install -e ".[dev]"

# Настроить конфигурацию
cp .env.example .env
# Отредактировать .env — заполнить токены и ADMIN_USER_IDS
```

### 4. Узнать свой Telegram ID

Откройте [@userinfobot](https://t.me/userinfobot) — он покажет ваш числовой ID. Впишите его в `ADMIN_USER_IDS` в `.env`.

### 5. Запуск

```bash
python -m bot.main
```

### 6. Добавление в группу

Добавьте бота в нужную группу. Он отправит приветственное сообщение и начнёт собирать сообщения.

## Конфигурация

Все настройки задаются через `.env` файл:

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | обязательно |
| `ADMIN_USER_IDS` | ID администраторов (через запятую) | `[]` |
| `REPLICATE_API_TOKEN` | API ключ Replicate | обязательно |
| `REPLICATE_MODEL` | Модель LLM | `anthropic/claude-4.5-sonnet` |
| `REPLICATE_MAX_TOKENS` | Макс. токенов ответа | `4096` |
| `DIGEST_DAY` | День дайджеста (0=Пн, 6=Вс) | `6` |
| `DIGEST_HOUR` | Час отправки | `20` |
| `DIGEST_TIMEZONE` | Часовой пояс | `Europe/Moscow` |
| `DATABASE_PATH` | Путь к SQLite файлу | `data/bot.db` |
| `MAX_MESSAGES_PER_PROMPT` | Макс. сообщений в промпт | `2000` |
| `MAX_MESSAGE_LENGTH` | Макс. длина сообщения | `500` |
| `AUTO_PIN_DIGEST` | Закреплять дайджест | `true` |

Подробнее: [docs/USAGE.md](docs/USAGE.md)

## Команды бота

| Команда | Описание | Доступ |
|---------|----------|--------|
| `/digest` | Сгенерировать дайджест за 7 дней | Админы |
| `/digest N` | Дайджест за N дней (1-365) | Админы |
| `/status` | Статистика: сообщений, последний дайджест | Все |
| `/help` | Справка по командам | Все |
| `/sources` | Список отслеживаемых чатов | Админы |
| `/add_channel ID` | Добавить канал | Админы |
| `/remove_channel ID` | Убрать канал | Админы |

## Деплой на Railway

### Через GitHub

1. Запушьте проект на GitHub
2. Зайдите на [railway.app](https://railway.app), создайте новый проект
3. Выберите "Deploy from GitHub repo"
4. Добавьте переменные окружения во вкладке Variables
5. Создайте Volume и примонтируйте к `/app/data` для хранения SQLite БД
6. Railway автоматически подхватит `railway.toml`

### Через CLI

```bash
npm install -g @railway/cli
railway login
railway init
railway variables set TELEGRAM_BOT_TOKEN=...
railway variables set REPLICATE_API_TOKEN=...
railway variables set ADMIN_USER_IDS=...
railway up
```

## Архитектура

```
Telegram Group
    │
    ▼
aiogram handlers ──► SQLite (messages, sources)
    │                    │
    ▼                    ▼
/digest command     APScheduler (weekly cron)
    │                    │
    └──────┬─────────────┘
           ▼
    Replicate API (Claude 4.5 Sonnet)
           │
           ▼
    format HTML + blockquotes
           │
           ▼
    send + inline keyboard + auto-pin
```

## Стек

- **Python 3.11+**
- **aiogram 3.x** — асинхронный Telegram Bot API
- **aiosqlite** — async SQLite (singleton connection, WAL mode)
- **replicate** — Replicate API client (async)
- **APScheduler** — планировщик задач
- **pydantic-settings** — валидация конфигурации

## Тестирование

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

43 теста покрывают: CRUD операции, JSON-парсинг, форматирование дайджеста, ссылки, edge cases.

## Лицензия

MIT
