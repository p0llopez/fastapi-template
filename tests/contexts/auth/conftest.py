from uuid import UUID

import pytest

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.repositories import UserRepository


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def save(self, user: User) -> None:
        self._users[user.user_id] = user

    async def find_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    async def find_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def find_by_api_key(self, api_key: str) -> User | None:
        for user in self._users.values():
            for key in user.api_keys:
                if key.api_key == api_key:
                    return user
        return None

    async def delete(self, user_id: UUID) -> None:
        self._users.pop(user_id, None)

    async def list_all(self) -> list[User]:
        return list(self._users.values())

    def count(self) -> int:
        return len(self._users)


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
    return sample_user, api_key.api_key
