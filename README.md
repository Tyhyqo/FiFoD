# FiFoD — Files For Device

Сервис для привязки файлов к устройствам. Получает список устройств из внешнего REST API,
позволяет просматривать файлы в рабочей директории и создавать привязки «устройство — файлы»,
сохраняя их в PostgreSQL.

### Возможности

- **JWT-авторизация** с access/refresh-токенами и ротацией
- **Проксирование внешнего API** устройств с retry-логикой и кэшированием
- **Управление файлами** — просмотр содержимого рабочей директории с пагинацией
- **Привязки** — связывание файлов с устройствами, фильтрация по тегам
- **WebSocket** — уведомления об изменении файлов в реальном времени
- **Healthcheck** — проверка состояния сервиса и подключения к БД
- **Rate limiting** — защита auth-эндпоинтов от перебора

---

## Быстрый старт

```bash
# 1. Скопировать конфиг и заполнить обязательные переменные
cp .env.example .env

# 2. Поднять сервис
docker compose up --build

# 3. Открыть документацию
#    http://localhost:8000/docs
```

Миграции применяются автоматически при старте контейнера. Swagger UI доступен
по адресу `/docs` — там же можно авторизоваться через кнопку **Authorize**.

![Swagger UI](docs/swagger.png)

---

## Архитектура

### Общая схема

```
                        ┌────────────┐
                        │   Клиент   │
                        └─────┬──────┘
                              │
                     HTTP / WebSocket
                              │
                        ┌─────▼──────┐
                        │  FastAPI   │
                        │  (Router)  │
                        └─────┬──────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────▼──────┐     ┌──────▼───────┐    ┌──────▼───────┐
    │AuthService │     │DeviceService │    │AttachmentSvc │
    └─────┬──────┘     └─┬───────┬────┘    └─┬───────┬────┘
          │              │       │           │       │
    ┌─────▼──────┐       │  ┌────▼─────┐     │  ┌────▼────┐
    │  UserRepo  │       │  │ External │     │  │FileSvc  │
    └─────┬──────┘       │  │   API    │     │  └────┬────┘
          │              │  └──────────┘     │       │
          │       ┌──────▼───────┐           │    FILE_DIR
          │       │AttachmentRepo│           │
          │       └──────┬───────┘           │
          │              │                   │
          └──────┬───────┘       ┌───────────┘
                 │               │
           ┌─────▼──────┐  ┌────▼──────┐
           │ PostgreSQL │  │ WebSocket │
           └────────────┘  │ (watcher) │
                           └───────────┘
```

Проект построен по **слоёной архитектуре**:

| Слой | Назначение |
|---|---|
| `api/` | Роуты, валидация запросов, HTTP-ответы |
| `services/` | Бизнес-логика, оркестрация |
| `repositories/` | Работа с БД через SQLAlchemy |
| `schemas/` | Pydantic-модели запросов и ответов |
| `infrastructure/` | Движок БД, HTTP-клиент, кэш, WebSocket, lifespan |

Зависимости идут строго сверху вниз — сервисы не знают про роуты,
репозитории не знают про сервисы. Всё собирается через FastAPI `Depends`.

### Схема базы данных

```
┌─────────────────────────┐       ┌──────────────────────────┐
│       users             │       │     refresh_tokens       │
├─────────────────────────┤       ├──────────────────────────┤
│ id            UUID  PK  │───┐   │ id          UUID      PK │
│ username      VARCHAR UK│   │   │ user_id     UUID      FK │──→ users.id
│ hashed_password  VARCHAR│   │   │ expires_at  TIMESTAMP    │
│ created_at    TIMESTAMP │   └──→│ created_at  TIMESTAMP    │
└─────────────────────────┘       └──────────────────────────┘

┌──────────────────────┐       ┌──────────────────────────┐
│     attachments      │       │    attachment_files      │
├──────────────────────┤       ├──────────────────────────┤
│ id          UUID  PK │───┐   │ id             UUID   PK │
│ device_id   VARCHAR  │   │   │ attachment_id  UUID   FK │──→ attachments.id
│ comment     VARCHAR  │   └──→│ file_name      VARCHAR   │
│ tags        VARCHAR[]│       └──────────────────────────┘
│ created_at  TIMESTAMP│
└──────────────────────┘
```

Связи: **users** `1 ── *` **refresh_tokens**, **attachments** `1 ── *` **attachment_files**.
Все FK с `ON DELETE CASCADE` — удаление родителя каскадно удаляет дочерние записи.

---

## Авторизация

Все эндпоинты (кроме `/api/auth/*` и `/health`) защищены JWT-токеном.

### Флоу

```
Register → Login → Получить access + refresh токены
                      │
                      ├── Использовать access_token в заголовке Authorization
                      │
                      └── Когда access истёк → POST /auth/refresh с refresh_token
                              → Получить новую пару токенов (ротация)
```

Каждый refresh-токен **одноразовый** — после использования старый удаляется
и выдаётся новый. Это защищает от повторного использования украденного токена.

### Регистрация

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret123"}'
```

Ответ (`201`):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "admin",
  "created_at": "2026-03-03T10:00:00Z"
}
```

### Логин

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=admin&password=secret123"
```

Ответ (`200`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "token_type": "bearer"
}
```

### Использование токена

```bash
curl http://localhost:8000/api/devices \
  -H "Authorization: Bearer <access_token>"
```

### Обновление токена

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

---

## API

### `GET /api/devices`

Список свободных устройств из внешнего API. Возвращает только устройства
с `ready=true`, `using=false` — отфильтрованные и с ограниченным набором полей.

При 5xx от внешнего API или `success=false` — автоматический retry
(количество попыток и задержка настраиваются через env).

Ответ (`200`):
```json
[
  {
    "serial": "ABC123",
    "model": "Pixel 6",
    "version": "12.0",
    "notes": "test device"
  }
]
```

### `GET /api/files`

Список файлов в рабочей директории. Поддерживает пагинацию: `skip`, `limit`.

```bash
curl http://localhost:8000/api/files?skip=0&limit=50 \
  -H "Authorization: Bearer <token>"
```

Ответ (`200`):
```json
[
  {
    "name": "firmware.bin",
    "size": 1048576,
    "modified_at": "2026-03-03T09:30:00Z"
  }
]
```

Файлы добавляются любым способом — через volume они сразу видны в контейнере:
```bash
cp firmware.bin ./files/
```

### `POST /api/attachments`

Создать привязку файлов к устройству. Перед сохранением проверяется,
что устройство есть в списке свободных и все файлы существуют на диске.

```bash
curl -X POST http://localhost:8000/api/attachments \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "ABC123",
    "fileNames": ["firmware.bin", "config.json"],
    "comment": "production release",
    "tags": ["release", "v2.0"]
  }'
```

Ответ (`201`):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "ABC123",
  "comment": "production release",
  "tags": ["release", "v2.0"],
  "created_at": "2026-03-03T10:15:00Z",
  "files": [
    {"id": "...", "file_name": "firmware.bin"},
    {"id": "...", "file_name": "config.json"}
  ]
}
```

### `GET /api/attachments`

Все привязки с информацией о файлах. Поддерживает пагинацию (`skip`, `limit`)
и фильтрацию по тегам (`tag`, можно указать несколько):

```bash
curl "http://localhost:8000/api/attachments?tag=release&tag=v2.0&limit=10" \
  -H "Authorization: Bearer <token>"
```

### `GET /health`

Проверка состояния сервиса и подключения к БД:

```json
{"status": "ok", "database": "available"}
```

Если БД недоступна:
```json
{"status": "unhealthy", "database": "unavailable"}
```

---

## WebSocket

Подключение к `/ws/files` для получения событий об изменении файлов в реальном времени.
Тестовая страница доступна по адресу `/ws-test`.

![WebSocket Test Page](docs/ws-test.png)

### События

При добавлении файла:
```json
{"event": "file_added", "name": "firmware.bin"}
```

При изменении:
```json
{"event": "file_modified", "name": "firmware.bin"}
```

При удалении:
```json
{"event": "file_deleted", "name": "firmware.bin"}
```

Под капотом — `watchfiles` отслеживает изменения в `FILE_DIR`, инвалидирует
кэш списка файлов и рассылает событие через `ConnectionManager` всем подключённым клиентам.

---

## Разработка

В dev-режиме используется `docker-compose.override.yml` — код монтируется
в контейнер и uvicorn перезапускается при изменениях:

```bash
docker compose up
```

Пересборка образа не нужна — достаточно сохранить файл.

---

## Тестирование

```bash
pip install -r requirements.txt
pytest
```

Тесты используют SQLite in-memory через `aiosqlite` и не требуют запущенного PostgreSQL.

**25 тестов** покрывают ключевые сценарии:

| Модуль | Что проверяется |
|---|---|
| `test_auth.py` | Регистрация, логин, refresh-токены, невалидные данные, повторное использование токена |
| `test_files.py` | Список файлов, пагинация, несуществующая директория, защита от path traversal |
| `test_devices.py` | Фильтрация устройств, кэширование, retry на 5xx, ошибки 4xx |
| `test_healthcheck.py` | Проверка эндпоинта `/health` с подключением к БД |

---

## Конфигурация

Все настройки задаются через переменные окружения. Полный пример — в `.env.example`.

### PostgreSQL

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | **обязательная** | `postgresql+asyncpg://user:pass@host:5432/db` |
| `DB_POOL_SIZE` | `10` | Постоянных соединений в пуле |
| `DB_MAX_OVERFLOW` | `20` | Дополнительных соединений сверх пула |
| `DB_POOL_RECYCLE` | `3600` | Пересоздание соединений (сек) |

### JWT-авторизация

| Переменная | По умолчанию | Описание |
|---|---|---|
| `JWT_SECRET_KEY` | **обязательная** | Секрет для подписи токенов |
| `JWT_ALGORITHM` | `HS256` | Алгоритм подписи |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Время жизни access-токена |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Время жизни refresh-токена |

### Внешний API устройств

| Переменная | По умолчанию | Описание |
|---|---|---|
| `EXTERNAL_API_URL` | **обязательная** | URL внешнего API |
| `EXTERNAL_API_TOKEN` | **обязательная** | Bearer-токен |
| `EXTERNAL_API_RETRY_COUNT` | `3` | Попытки при ошибке |
| `EXTERNAL_API_RETRY_DELAY` | `1.0` | Пауза между попытками (сек) |

### HTTP-клиент

| Переменная | По умолчанию | Описание |
|---|---|---|
| `HTTP_TIMEOUT_CONNECT` | `5.0` | Таймаут соединения |
| `HTTP_TIMEOUT_READ` | `10.0` | Таймаут чтения |
| `HTTP_TIMEOUT_WRITE` | `10.0` | Таймаут записи |
| `HTTP_TIMEOUT_POOL` | `5.0` | Таймаут ожидания коннекта из пула |
| `HTTP_MAX_CONNECTIONS` | `100` | Макс. одновременных соединений |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | `20` | Макс. keep-alive соединений |
| `HTTP_KEEPALIVE_EXPIRY` | `30.0` | Время жизни keep-alive (сек) |

### Прочее

| Переменная | По умолчанию | Описание |
|---|---|---|
| `FILE_DIR` | `/app/files` | Директория с файлами |
| `CACHE_FILES_TTL` | `60` | TTL кэша файлов (сек) |
| `CACHE_DEVICES_TTL` | `30` | TTL кэша устройств (сек) |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

Для Docker Compose также нужны `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

---

## Структура проекта

```
app/
├── api/                 # Роуты и обработчики ошибок
│   ├── auth.py          #   POST /auth/register, /auth/login, /auth/refresh
│   ├── devices.py       #   GET /devices
│   ├── files.py         #   GET /files
│   ├── attachments.py   #   POST, GET /attachments
│   ├── ws.py            #   WebSocket /ws/files + тестовая страница
│   └── exception_handlers.py
├── services/            # Бизнес-логика
│   ├── auth_service.py  #   Регистрация, логин, JWT, refresh
│   ├── device_service.py#   Проксирование внешнего API с retry
│   ├── file_service.py  #   Листинг файлов, проверка существования
│   ├── attachment_service.py  # Валидация и создание привязок
│   └── file_watcher.py  #   Отслеживание изменений файлов
├── repositories/        # Слой доступа к данным
│   ├── user_repo.py     #   CRUD пользователей и refresh-токенов
│   └── attachment_repo.py #  CRUD привязок с eager loading
├── db/                  # ORM-модели и сессии
│   ├── base.py
│   ├── models.py
│   └── session.py
├── schemas/             # Pydantic-схемы запросов/ответов
├── infrastructure/      # Инфраструктурные компоненты
│   ├── database.py      #   Пул соединений (pool_pre_ping, recycle)
│   ├── http_client.py   #   httpx с настроенными таймаутами
│   ├── cache.py         #   TTL-кэш для файлов и устройств
│   ├── ws_manager.py    #   Менеджер WebSocket-соединений
│   └── lifespan.py      #   Startup/shutdown, фоновые задачи
├── core/                # Сквозная функциональность
│   ├── logging_config.py
│   └── rate_limit.py
├── main.py              # Точка входа
├── router.py            # Регистрация роутеров и обработчиков ошибок
├── dependencies.py      # Фабрики зависимостей (Depends)
├── config.py            # Настройки через pydantic-settings
└── exceptions.py        # Доменные исключения
migrations/              # Alembic-миграции
tests/                   # Тесты (pytest + pytest-asyncio)
files/                   # Рабочая директория (монтируется в контейнер)
```

---

## Стек

| Технология | Зачем |
|---|---|
| **Python 3.12** | Актуальная версия с нативной поддержкой `asyncio` |
| **FastAPI** | Async-first фреймворк, автогенерация OpenAPI, Depends для DI |
| **SQLAlchemy 2.0 (async)** | ORM с полной async-поддержкой, `selectinload` для решения N+1 |
| **PostgreSQL 16** | Надёжная СУБД, поддержка `ARRAY`, `RETURNING` |
| **Alembic** | Версионирование миграций с поддержкой downgrade |
| **PyJWT + passlib/bcrypt** | Стандарт для JWT-авторизации, bcrypt для хэширования паролей |
| **httpx** | Async HTTP-клиент с настраиваемыми таймаутами и пулом соединений |
| **watchfiles** | Эффективное отслеживание изменений файлов (на основе `notify`) |
| **Docker** | Воспроизводимое окружение, healthcheck, graceful shutdown |
| **pytest + pytest-asyncio** | Async-тесты с SQLite in-memory, без внешних зависимостей |
