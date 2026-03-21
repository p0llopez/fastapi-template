from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestAuthEndpoints:
    async def test_create_user_is_public(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/users",
            json={
                "username": f"testuser-{uuid4().hex[:8]}",
                "password": "secret123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"].startswith("testuser-")
        assert "id" in data
        assert "is_active" in data
        assert "created_at" in data
        assert "password" not in data

    async def test_list_users_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/users")

        assert response.status_code == 401

    async def test_get_user_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/auth/users/{uuid4()}")

        assert response.status_code == 401

    async def test_delete_user_requires_auth(self, client: AsyncClient) -> None:
        response = await client.delete(f"/api/v1/auth/users/{uuid4()}")

        assert response.status_code == 401
