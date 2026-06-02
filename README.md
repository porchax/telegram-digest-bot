<div align="center">

# 🤖 Telegram Digest Bot

**Еженедельные AI-дайджесты группового чата с сатирическим плакатом недели**

Бот читает все сообщения группы, сохраняет их в базу и раз в неделю формирует
структурированный отчёт с ключевыми темами — а сверху публикует
карикатурный плакат-инфографику, нарисованный по итогам недели.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![LLM](https://img.shields.io/badge/LLM-Claude%204.5%20Sonnet-D97757)](https://www.anthropic.com/claude)
[![Replicate](https://img.shields.io/badge/Replicate-API-000000?logo=replicate&logoColor=white)](https://replicate.com/)
[![Deploy](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway&logoColor=white)](https://railway.app/)
[![Tests](https://img.shields.io/badge/tests-43%20passing-success)](#-тестирование)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](#-лицензия)

</div>

---

## ✨ Возможности

| | |
|---|---|
| 🗓️ **Дайджест по расписанию** | Автоматическая генерация в настраиваемый день и время (по умолчанию воскресенье, 20:00) |
| ⚡ **Ручная генерация** | Команда `/digest` для немедленного отчёта за 7 или произвольное число дней |
| 🎨 **Плакат недели** | Сатирический плакат-инфографика по темам недели (gpt-image-2), публикуется над дайджестом |
| 🧠 **Анализ через LLM** | Claude 4.5 Sonnet выделяет важные и обсуждаемые темы, считает статистику |
| 🔀 **Двухэтапный анализ** | Большие объёмы (>2000 сообщений) суммаризируются по дням, затем сводятся в финальный отчёт |
| 🎛️ **Интерактивный дайджест** | Inline-кнопки: Важные / Обсуждаемые / Статистика / Полный |
| 📑 **Expandable blockquotes** | Заголовки тем всегда видны, описание раскрывается по тапу |
| 🔗 **Ссылки на сообщения** | Каждая тема ведёт на начало обсуждения в чате |
| 📌 **Автозакрепление** | Свежий дайджест закрепляется в чате |
| 📣 **Поддержка каналов** | Отслеживание постов каналов с отдельным промптом |
| ✏️ **Учёт правок** | Отредактированные сообщения обновляются в базе |
| 📜 **Backfill истории** | Разовая дозагрузка прошлых сообщений через личный аккаунт (Telethon) |

---

## 🎨 Плакат недели

При включённом `GENERATE_DIGEST_IMAGE=true` над дайджестом публикуется **сатирический
плакат-инфографика**, нарисованный по темам прошедшей недели:

1. По заголовкам тем (важные + обсуждаемые) LLM генерирует англоязычный арт-промпт
   в стиле «обложка таблоида / агитплакат» — с гиперболой, мемами и дружеским подколом.
2. Весь текст **на самом плакате принудительно на русском** (кириллица, без латиницы).
3. Промпт уходит в `gpt-image-2` через Replicate (~2 минуты на картинку).
4. Готовый плакат отправляется в чат **перед** дайджестом.

> 🛡️ **Отказоустойчивость:** при сбое генерации промпта используется безопасный дефолт,
> а при сбое самой картинки дайджест выходит **без плаката** — текст всегда доходит до чата.
> Генерация ограничена жёстким таймаутом (240 с) и мягким retry без агрессивного backoff.

Настраивается через `GENERATE_DIGEST_IMAGE`, `IMAGE_MODEL`, `IMAGE_QUALITY`, `IMAGE_OUTPUT_FORMAT`.

---

## 📋 Пример дайджеста

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

---

## 🚀 Быстрый старт

### 1. Создание бота

1. Откройте [@BotFather](https://t.me/BotFather) и отправьте `/newbot`
2. Сохраните полученный токен
3. **Важно:** `Bot Settings → Group Privacy → Turn off` — иначе бот не увидит сообщения в группе

### 2. Replicate API

1. Зарегистрируйтесь на [replicate.com](https://replicate.com)
2. Создайте токен в [API tokens](https://replicate.com/account/api-tokens)

### 3. Установка

```bash
git clone https://github.com/porchax/telegram-digest-bot.git
cd telegram-digest-bot

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

cp .env.example .env
# Заполните TELEGRAM_BOT_TOKEN, REPLICATE_API_TOKEN, ADMIN_USER_IDS
```

### 4. Свой Telegram ID

Откройте [@userinfobot](https://t.me/userinfobot) — он покажет ваш числовой ID.
Впишите его в `ADMIN_USER_IDS` в `.env`.

### 5. Запуск

```bash
python -m bot.main
```

### 6. Добавление в группу

Добавьте бота в группу — он отправит приветствие и начнёт собирать сообщения.
Для автозакрепления выдайте боту права администратора с разрешением `Pin Messages`.

---

## ⚙️ Конфигурация

Все настройки задаются через `.env`:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | **обязательно** |
| `ADMIN_USER_IDS` | ID администраторов (через запятую) | `[]` |
| `REPLICATE_API_TOKEN` | API-ключ Replicate | **обязательно** |
| `REPLICATE_MODEL` | Модель LLM | `anthropic/claude-4.5-sonnet` |
| `REPLICATE_MAX_TOKENS` | Макс. токенов ответа | `4096` |
| `DIGEST_DAY` | День дайджеста (0=Пн … 6=Вс) | `6` |
| `DIGEST_HOUR` | Час отправки | `20` |
| `DIGEST_TIMEZONE` | Часовой пояс | `Europe/Moscow` |
| `DATABASE_PATH` | Путь к SQLite-файлу | `data/bot.db` |
| `MAX_MESSAGES_PER_PROMPT` | Макс. сообщений в промпт | `2000` |
| `MAX_MESSAGE_LENGTH` | Макс. длина сообщения | `500` |
| `AUTO_PIN_DIGEST` | Закреплять дайджест | `true` |
| `GENERATE_DIGEST_IMAGE` | Генерировать плакат недели | `false` |
| `IMAGE_MODEL` | Модель генерации картинки | `openai/gpt-image-2` |
| `IMAGE_QUALITY` | Качество (`low`/`medium`/`high`) | `medium` |
| `IMAGE_OUTPUT_FORMAT` | Формат (`jpeg`/`png`/`webp`) | `jpeg` |

Подробное руководство: [docs/USAGE.md](docs/USAGE.md)

---

## 💬 Команды бота

| Команда | Описание | Доступ |
|---------|----------|--------|
| `/digest` | Дайджест за последние 7 дней | Админы |
| `/digest N` | Дайджест за N дней (1–365) | Админы |
| `/status` | Статистика: сообщения, последний дайджест | Все |
| `/help` | Справка по командам | Все |
| `/sources` | Список отслеживаемых чатов | Админы |
| `/add_channel ID` | Добавить канал | Админы |
| `/remove_channel ID` | Убрать канал | Админы |

---

## 📜 Backfill истории чата

Telegram Bot API не позволяет ботам читать сообщения, отправленные **до** их добавления
в чат. Для разовой дозагрузки прошлой истории есть скрипт `bot/backfill.py`, который
логинится **вашим личным аккаунтом** (MTProto / Telethon) и кладёт сообщения в ту же базу.

```bash
pip install telethon
# Нужны TELEGRAM_API_ID и TELEGRAM_API_HASH с https://my.telegram.org
python -m bot.backfill --chat -1001234567890 --days 7
```

Скрипт идемпотентен (`INSERT OR IGNORE`) — дубли с уже собранными ботом сообщениями
не создаются. На Railway запускается внутри контейнера через `railway ssh`
(там смонтирован volume с базой). Подробнее — в докстринге `bot/backfill.py`.

---

## 🚂 Деплой на Railway

<details>
<summary><b>Через GitHub</b></summary>

1. Запушьте проект на GitHub
2. На [railway.app](https://railway.app) создайте проект → «Deploy from GitHub repo»
3. Добавьте переменные окружения во вкладке Variables
4. Создайте Volume и примонтируйте к `/app/data` для хранения SQLite
5. Railway автоматически подхватит `railway.toml`

</details>

<details>
<summary><b>Через CLI</b></summary>

```bash
npm install -g @railway/cli
railway login
railway init
railway variables set TELEGRAM_BOT_TOKEN=...
railway variables set REPLICATE_API_TOKEN=...
railway variables set ADMIN_USER_IDS=...
railway up
```

</details>

---

## 💰 Стоимость

Telegram Bot API — **бесплатно**. Платежи идут только за вызовы Replicate (оплата по
использованию). Ориентировочные траты на один дайджест:

| Что | Модель | Примерная цена |
|-----|--------|----------------|
| Анализ тем недели | Claude 4.5 Sonnet | ~$0.01–0.05 (зависит от объёма текста) |
| Плакат недели *(опционально)* | gpt-image-2, `medium` | ~$0.03–0.05 за картинку |
| **Итого за дайджест** | | **~$0.05–0.10** с плакатом, **~$0.01–0.05** без него |

Для одной группы с еженедельным дайджестом это примерно **$0.20–0.40 в месяц**
(или **~$0.05–0.20/мес** без генерации плаката). Точные тарифы — на странице моделей
[Replicate Pricing](https://replicate.com/pricing).

> ℹ️ Двухэтапный анализ больших чатов (>2000 сообщений) делает дополнительные вызовы LLM —
> стоимость такого дайджеста может быть выше указанной.

---

## 🏗️ Архитектура

```
Telegram Group / Channel
          │
          ▼
   aiogram handlers ───────────► SQLite (messages, sources, digests)
          │                              │
          ▼                              ▼
   /digest command            APScheduler (weekly cron)
          │                              │
          └──────────────┬───────────────┘
                         ▼
              Replicate · Claude 4.5 Sonnet
              (анализ тем + промпт плаката)
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
   gpt-image-2 (плакат)      format HTML + blockquotes
            │                         │
            └────────────┬────────────┘
                         ▼
     send_photo + send + inline keyboard + auto-pin
```

**Ключевые решения:**

- **Singleton DB connection** — одно подключение aiosqlite в WAL-режиме на весь процесс
- **Async Replicate** — `replicate.async_run()` с retry и экспоненциальным backoff (2s/5s/10s)
- **JSON-парсинг ответов LLM** — три стратегии (`json.loads` → markdown-блок → balanced-brace парсер)
- **Send-before-save** — дайджест отправляется в Telegram до записи в БД, чтобы не было «призраков»
- **Graceful degradation** — сбой картинки или API не роняет бота: дайджест выходит без плаката

---

## 🧰 Стек

- **Python 3.11+**
- **aiogram 3.x** — асинхронный Telegram Bot API
- **aiosqlite** — async SQLite (singleton connection, WAL mode)
- **replicate** — клиент Replicate API (async): Claude 4.5 Sonnet + gpt-image-2
- **APScheduler** — планировщик еженедельной генерации
- **pydantic-settings** — валидация конфигурации
- **Telethon** *(опционально)* — backfill истории через личный аккаунт

---

## ✅ Тестирование

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

**43 теста** покрывают: CRUD-операции, JSON-парсинг (5 стратегий), форматирование
дайджеста, blockquotes, ссылки, экранирование и edge cases.

---

## 📂 Структура проекта

```
bot/
├── main.py              # Точка входа, профиль бота, запуск
├── config.py            # Настройки из .env (pydantic-settings)
├── backfill.py          # Разовый backfill истории через Telethon
├── db/                  # models · database (singleton) · repository (CRUD)
├── handlers/            # messages · commands · callbacks
├── services/            # collector · analyzer · digest · image · scheduler
└── utils/               # message_links · text
```

---

## 📄 Лицензия

[MIT](LICENSE)
