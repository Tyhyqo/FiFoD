# FiFoD — Files For Device

Сервис для привязки файлов к устройствам. Получает список устройств из внешнего REST API,
работает с файлами в локальной директории и хранит привязки в PostgreSQL.

## Запуск

```bash
cp .env.example .env
# Отредактировать .env: указать EXTERNAL_API_URL и EXTERNAL_API_TOKEN

docker compose up --build
```

Сервис поднимется на `http://localhost:8000`. Миграции применяются автоматически при старте контейнера.

В dev-режиме (с `docker-compose.override.yml`) код монтируется в контейнер и uvicorn
перезапускается при изменениях — пересборка образа не нужна.

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

Все созданные привязки с информацией о файлах. Поддерживает пагинацию (`skip`, `limit`).

## Переменные окружения

Полный список с описаниями — в `.env.example`. Ниже все доступные переменные:

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `DATABASE_URL` | да | — | Строка подключения к PostgreSQL (`postgresql+asyncpg://...`) |
| `DB_POOL_SIZE` | нет | `10` | Количество постоянных соединений в пуле |
| `DB_MAX_OVERFLOW` | нет | `20` | Дополнительные соединения сверх пула |
| `DB_POOL_RECYCLE` | нет | `3600` | Пересоздавать соединения через N секунд |
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
| `LOG_LEVEL` | нет | `INFO` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

Для Docker Compose также нужны `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — они передаются в контейнер PostgreSQL.

## Структура проекта

```
app/
  api/              # Роуты (devices, files, attachments)
  services/         # Бизнес-логика
  repositories/     # Работа с БД
  db/               # ORM-модели, сессии
  schemas/          # Pydantic-схемы запросов/ответов
  infrastructure/   # Движок БД, HTTP-клиент, lifespan
  core/             # Логирование
  config.py         # Настройки (pydantic-settings)
  exceptions.py     # Доменные исключения
migrations/         # Alembic-миграции
files/              # Директория для файлов (монтируется в контейнер)
```

## Стек

- Python 3.12, FastAPI, uvicorn
- PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic
- httpx (async HTTP-клиент для внешнего API)
- Docker, Docker Compose
