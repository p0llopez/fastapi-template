import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestHealthEndpoint:
    async def test_returns_healthy(self, client: AsyncClient) -> None:
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_protected_requires_api_key(self, client: AsyncClient) -> None:
        response = await client.get("/health-protected")

        assert response.status_code in (401, 403)
