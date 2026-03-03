# FiFoD — Files For Device

Сервис для привязки файлов к устройствам. Получает список устройств из внешнего REST API,
работает с файлами в локальной директории и хранит привязки в PostgreSQL.

## Запуск

```bash
cp .env.example .env
# Отредактировать .env: указать EXTERNAL_API_URL, EXTERNAL_API_TOKEN и JWT_SECRET_KEY

docker compose up --build
```

Сервис поднимется на `http://localhost:8000`. Миграции применяются автоматически при старте контейнера.

В dev-режиме (с `docker-compose.override.yml`) код монтируется в контейнер и uvicorn
перезапускается при изменениях — пересборка образа не нужна.

## Авторизация

Все эндпоинты (кроме `/api/auth/*` и `/health`) защищены JWT-токеном.
Swagger UI (`/docs`) поддерживает кнопку **Authorize** для удобного тестирования.

### Регистрация

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret123"}'
```

### Логин

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=admin&password=secret123"
```

Возвращает `access_token` (JWT, живёт 30 мин) и `refresh_token` (UUID, живёт 7 дней).

### Использование токена

```bash
curl http://localhost:8000/api/devices \
  -H "Authorization: Bearer <access_token>"
```

### Обновление токена

Когда access-токен истёк, отправьте refresh-токен для получения новой пары:

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

Каждый refresh-токен одноразовый — после использования выдаётся новая пара токенов (ротация).

## API

### GET /api/devices

Проксирует список свободных устройств из внешнего API. Возвращает только поля
`serial`, `model`, `version`, `notes` и только устройства с `ready=true`, `using=false`.

Если внешний API отвечает 5xx или `success=false`, сервис повторяет запрос
(количество попыток и задержка настраиваются через env).

### GET /api/files

Список файлов в рабочей директории (`FILE_DIR`). Поддерживает пагинацию
через query-параметры `skip` и `limit`.

Файлы добавляются любым удобным способом — через volume они сразу видны в контейнере:
```bash
cp firmware.bin ./files/
```

### POST /api/attachments

Создать привязку файлов к устройству.

```json
{
  "deviceId": "ABC123",
  "fileNames": ["firmware.bin", "config.json"]
}
```

Перед сохранением проверяется, что устройство есть в списке свободных и все файлы существуют.

### GET /api/attachments

Все созданные привязки с информацией о файлах. Поддерживает пагинацию (`skip`, `limit`)
и фильтрацию по тегам (query-параметр `tag`, можно указать несколько).

### GET /health

Проверка состояния сервиса и подключения к БД. Возвращает `{"status": "ok", "database": "available"}`
или `{"status": "unhealthy", "database": "unavailable"}`.

### WebSocket /ws/files

Подключение по WebSocket для получения событий об изменении файлов в реальном времени.
Тестовая страница доступна по адресу `/ws-test`.

## Переменные окружения

Полный список с описаниями — в `.env.example`. Ниже все доступные переменные:

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `DATABASE_URL` | да | — | Строка подключения к PostgreSQL (`postgresql+asyncpg://...`) |
| `DB_POOL_SIZE` | нет | `10` | Количество постоянных соединений в пуле |
| `DB_MAX_OVERFLOW` | нет | `20` | Дополнительные соединения сверх пула |
| `DB_POOL_RECYCLE` | нет | `3600` | Пересоздавать соединения через N секунд |
| `JWT_SECRET_KEY` | да | — | Секретный ключ для подписи JWT-токенов |
| `JWT_ALGORITHM` | нет | `HS256` | Алгоритм подписи JWT |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | нет | `30` | Время жизни access-токена (минуты) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | нет | `7` | Время жизни refresh-токена (дни) |
| `EXTERNAL_API_URL` | да | — | URL внешнего API устройств |
| `EXTERNAL_API_TOKEN` | да | — | Bearer-токен для внешнего API |
| `EXTERNAL_API_RETRY_COUNT` | нет | `3` | Количество повторных попыток при ошибке |
| `EXTERNAL_API_RETRY_DELAY` | нет | `1.0` | Пауза между попытками (секунды) |
| `HTTP_TIMEOUT_CONNECT` | нет | `5.0` | Таймаут на установку соединения (сек) |
| `HTTP_TIMEOUT_READ` | нет | `10.0` | Таймаут ожидания ответа (сек) |
| `HTTP_TIMEOUT_WRITE` | нет | `10.0` | Таймаут на отправку запроса (сек) |
| `HTTP_TIMEOUT_POOL` | нет | `5.0` | Таймаут ожидания свободного коннекта из пула (сек) |
| `HTTP_MAX_CONNECTIONS` | нет | `100` | Максимум одновременных HTTP-соединений |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | нет | `20` | Максимум keep-alive соединений |
| `HTTP_KEEPALIVE_EXPIRY` | нет | `30.0` | Время жизни keep-alive соединения (сек) |
| `FILE_DIR` | нет | `/app/files` | Директория с файлами для привязки |
| `CACHE_FILES_TTL` | нет | `60` | TTL кэша списка файлов (секунды) |
| `CACHE_DEVICES_TTL` | нет | `30` | TTL кэша списка устройств (секунды) |
| `LOG_LEVEL` | нет | `INFO` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

Для Docker Compose также нужны `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — они передаются в контейнер PostgreSQL.

## Структура проекта

```
app/
  api/              # Роуты (devices, files, attachments) и обработчики ошибок
  services/         # Бизнес-логика
  repositories/     # Работа с БД
  db/               # ORM-модели, сессии, декларативная база
  schemas/          # Pydantic-схемы запросов/ответов
  infrastructure/   # Движок БД, HTTP-клиент, lifespan
  core/             # Логирование
  main.py           # Точка входа (FastAPI-приложение)
  router.py         # Подключение роутеров
  dependencies.py   # Фабрики зависимостей (Depends)
  config.py         # Настройки (pydantic-settings)
  exceptions.py     # Доменные исключения
migrations/         # Alembic-миграции
tests/              # Тесты (pytest + pytest-asyncio)
files/              # Директория для файлов (монтируется в контейнер)
```

## Тестирование

```bash
pip install -r requirements.txt
pytest
```

Тесты используют SQLite in-memory (aiosqlite) и не требуют запущенного PostgreSQL.

## Стек

- Python 3.12, FastAPI, uvicorn
- PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic
- PyJWT + passlib/bcrypt (JWT-авторизация с refresh-токенами)
- httpx (async HTTP-клиент для внешнего API)
- watchfiles (отслеживание изменений файлов, WebSocket-уведомления)
- pytest + pytest-asyncio (тестирование)
- Docker, Docker Compose
