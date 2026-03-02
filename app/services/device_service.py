import asyncio
import json
import logging

import httpx

from app.config import settings
from app.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)

_EXPOSED_FIELDS = ("serial", "model", "version", "notes")


class DeviceService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._url = f"{settings.EXTERNAL_API_URL.rstrip('/')}/device"
        self._headers = {"Authorization": f"Bearer {settings.EXTERNAL_API_TOKEN}"}

    async def get_free_devices(self) -> list[dict]:
        """
        Получить список свободных устройств.

        Повторяет запрос только при HTTP 5xx или success=false в теле ответа.
        Ошибки 4xx не ретраятся — они сигнализируют о проблеме конфигурации
        (неверный токен, неверный URL) и немедленно поднимают ExternalAPIError.

        Raises:
            ExternalAPIError: при 4xx, сетевой ошибке или исчерпании попыток.
        """
        last_exc: Exception | None = None

        for attempt in range(1, settings.EXTERNAL_API_RETRY_COUNT + 1):
            try:
                response = await self._client.get(self._url, headers=self._headers)

                if response.status_code >= 500:
                    logger.warning(
                        "External API returned %s (attempt %d/%d)",
                        response.status_code,
                        attempt,
                        settings.EXTERNAL_API_RETRY_COUNT,
                    )
                    last_exc = httpx.HTTPStatusError(
                        f"Server error {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                    await asyncio.sleep(settings.EXTERNAL_API_RETRY_DELAY)
                    continue

                # 4xx — конфигурационная ошибка, retry бесполезен
                if not response.is_success:
                    raise ExternalAPIError(
                        f"External API returned {response.status_code}. "
                        "Check EXTERNAL_API_URL and EXTERNAL_API_TOKEN."
                    )

                try:
                    data = response.json()
                except (json.JSONDecodeError, httpx.DecodingError) as exc:
                    logger.warning(
                        "External API returned non-JSON response (attempt %d/%d): %s",
                        attempt,
                        settings.EXTERNAL_API_RETRY_COUNT,
                        exc,
                    )
                    last_exc = exc
                    await asyncio.sleep(settings.EXTERNAL_API_RETRY_DELAY)
                    continue

                # STF оборачивает ответ в {"success": bool, "devices": [...]}
                # Поддерживаем также общий вариант с ключом "data"
                if isinstance(data, dict):
                    if not data.get("success", True):
                        logger.warning(
                            "External API busy (success=false), attempt %d/%d",
                            attempt,
                            settings.EXTERNAL_API_RETRY_COUNT,
                        )
                        last_exc = RuntimeError("External API returned success=false")
                        await asyncio.sleep(settings.EXTERNAL_API_RETRY_DELAY)
                        continue
                    devices_raw = data.get("devices") or data.get("data", [])
                else:
                    devices_raw = data

                return self._filter(devices_raw)

            except ExternalAPIError:
                raise
            except httpx.TransportError as exc:
                # TransportError покрывает: TimeoutException, NetworkError,
                # ProtocolError (RemoteProtocolError), ProxyError, UnsupportedProtocol
                logger.warning(
                    "Network error while calling external API (attempt %d/%d): %s",
                    attempt,
                    settings.EXTERNAL_API_RETRY_COUNT,
                    exc,
                )
                last_exc = exc
                await asyncio.sleep(settings.EXTERNAL_API_RETRY_DELAY)

        raise ExternalAPIError(
            f"External API unavailable after {settings.EXTERNAL_API_RETRY_COUNT} attempts"
        ) from last_exc

    @staticmethod
    def _filter(devices_raw: list[dict]) -> list[dict]:
        """Оставить только свободные устройства (ready=true, using=false) и нужные поля."""
        return [
            {field: device.get(field) for field in _EXPOSED_FIELDS}
            for device in devices_raw
            if device.get("ready") is True and device.get("using") is False
        ]
