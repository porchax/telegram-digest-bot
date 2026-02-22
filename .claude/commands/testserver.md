Подними всю локальную инфраструктуру DnD Clash для тестирования как Telegram Mini App. Выполни все шаги последовательно, проверяя успешность каждого.

## Шаги

### 1. PostgreSQL и Redis
- Проверь что PostgreSQL 16 запущен: `/usr/local/opt/postgresql@16/bin/pg_isready -p 5433`
- Если нет — `brew services start postgresql@16`
- Проверь что Redis запущен: `redis-cli ping` (ответ PONG)
- Если нет — `brew services start redis`

### 2. Сервер
- `cd server`
- Проверь наличие `server/.env` — если нет, скопируй из `server/.env.example` и попроси BOT_TOKEN
- Проверь наличие `node_modules` — если нет, `npm install`
- Проверь что Prisma клиент сгенерирован — `npx prisma generate`
- Проверь что миграции применены — `npx prisma migrate dev`
- Запусти сервер в фоне: `npm run dev`
- Подожди 3 секунды и проверь что сервер отвечает на `http://localhost:3001`

### 3. Клиент
- `cd` в корень проекта
- Проверь наличие `node_modules` — если нет, `npm install`
- Запусти клиент в фоне: `npm run dev`
- Подожди 3 секунды и определи на каком порту запустился Vite (5173 или 5174)

### 4. ngrok
- Проверь наличие ngrok: `which ngrok`
- Если нет — `brew install ngrok`
- Проверь что authtoken настроен: запусти `ngrok http <порт_vite>` в фоне
- Если ошибка авторизации — попроси пользователя ввести authtoken
- Подожди 5 секунд и получи публичный URL через `curl -s http://127.0.0.1:4040/api/tunnels`

### 5. Итог
Выведи итоговую таблицу со статусами всех сервисов и URL-ами. Напомни пользователю обновить URL в @BotFather если он изменился.
