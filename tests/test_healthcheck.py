from httpx import AsyncClient


class TestHealthcheck:

    async def test_health_returns_ok(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "available"
