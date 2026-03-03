import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.exceptions import ExternalAPIError
from app.infrastructure.cache import devices_cache
from app.services.device_service import DeviceService


@pytest.fixture(autouse=True)
def clear_devices_cache():
    devices_cache.invalidate()
    yield
    devices_cache.invalidate()


def _mock_response(data: dict | list, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("GET", "http://test/device"),
    )


class TestDeviceService:

    async def test_get_free_devices_filters_correctly(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({
            "success": True,
            "devices": [
                {"serial": "A1", "model": "M1", "version": "1.0", "notes": "", "ready": True, "using": False},
                {"serial": "A2", "model": "M2", "version": "2.0", "notes": "", "ready": True, "using": True},
                {"serial": "A3", "model": "M3", "version": "3.0", "notes": "", "ready": False, "using": False},
            ],
        })

        svc = DeviceService(mock_client)
        result = await svc.get_free_devices()

        assert len(result) == 1
        assert result[0]["serial"] == "A1"
        assert set(result[0].keys()) == {"serial", "model", "version", "notes"}

    async def test_get_free_devices_empty_list(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({"success": True, "devices": []})

        svc = DeviceService(mock_client)
        result = await svc.get_free_devices()

        assert result == []

    async def test_get_free_devices_uses_cache(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({
            "success": True,
            "devices": [
                {"serial": "C1", "model": "M", "version": "1", "notes": "", "ready": True, "using": False},
            ],
        })

        svc = DeviceService(mock_client)
        await svc.get_free_devices()
        await svc.get_free_devices()

        assert mock_client.get.call_count == 1

    async def test_get_free_devices_4xx_raises(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(
            {"error": "forbidden"}, status_code=403,
        )

        svc = DeviceService(mock_client)
        with pytest.raises(ExternalAPIError, match="403"):
            await svc.get_free_devices()

    async def test_get_free_devices_retries_on_5xx(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            _mock_response({"error": "internal"}, status_code=500),
            _mock_response({
                "success": True,
                "devices": [
                    {"serial": "R1", "model": "M", "version": "1", "notes": "", "ready": True, "using": False},
                ],
            }),
        ]

        svc = DeviceService(mock_client)
        result = await svc.get_free_devices()

        assert len(result) == 1
        assert result[0]["serial"] == "R1"
        assert mock_client.get.call_count == 2
