from uuid import UUID

import pytest

from src.contexts.auth.domain.aggregates import ApiKey, User
from src.contexts.auth.domain.repositories import UserRepository


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def save(self, user: User) -> None:
        self._users[user.user_id] = user

    async def find_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    async def delete(self, user_id: UUID) -> None:
        self._users.pop(user_id, None)

    async def list_all(self) -> list[User]:
        return list(self._users.values())

    def count(self) -> int:
        return len(self._users)

    async def find_api_key_by_key(self, key: str) -> ApiKey | None:
        for user in self._users.values():
            for api_key in user.api_keys:
                if api_key.key == key:
                    return api_key
        return None


@pytest.fixture
def fake_user_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def sample_user() -> User:
    return User.create(
        username="testuser",
        password="hashedpassword123",
        email="test@example.com",
    )


@pytest.fixture
def sample_user_with_api_key(sample_user: User) -> tuple[User, str]:
    api_key = sample_user.create_api_key()
    return sample_user, api_key.key
