import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestHealthEndpoint:
    async def test_returns_healthy_with_components(self, client: AsyncClient) -> None:
        response = await client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "database" in body["components"]
