import pytest

from src.contexts.auth.application.use_cases.list_users import (
    ListUsersDTO,
    ListUsersUseCase,
)
from src.contexts.auth.domain.aggregates import User
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestListUsersUseCase:
    async def test_returns_empty_list_when_no_users(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        use_case = ListUsersUseCase(fake_user_repository)

        users = await use_case.execute(ListUsersDTO())

        assert users == []

    async def test_returns_all_users(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        user1 = User.create(username="user1", password="pass")
        user2 = User.create(username="user2", password="pass")
        await fake_user_repository.save(user1)
        await fake_user_repository.save(user2)
        use_case = ListUsersUseCase(fake_user_repository)

        users = await use_case.execute(ListUsersDTO())

        assert len(users) == 2
