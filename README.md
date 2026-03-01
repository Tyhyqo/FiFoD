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

Все созданные привязки с информацией о файлах.

## Переменные окружения

Полный список с описаниями и значениями по умолчанию — в `.env.example`.

Основные:

| Переменная | Обязательная | Описание |
|---|---|---|
| `DATABASE_URL` | да | Строка подключения к PostgreSQL (`postgresql+asyncpg://...`) |
| `EXTERNAL_API_URL` | да | URL внешнего API устройств |
| `EXTERNAL_API_TOKEN` | да | Токен авторизации для внешнего API |
| `FILE_DIR` | нет | Директория с файлами (по умолчанию `/app/files`) |
| `LOG_LEVEL` | нет | Уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

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
