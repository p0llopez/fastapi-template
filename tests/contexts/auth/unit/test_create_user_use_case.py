import pytest

from src.contexts.auth.application.use_cases.create_user import (
    CreateUserDTO,
    CreateUserUseCase,
)
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestCreateUserUseCase:
    async def test_creates_user_with_hashed_password(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        use_case = CreateUserUseCase(fake_user_repository)

        user = await use_case.execute(
            CreateUserDTO(username="newuser", password="password123")
        )

        assert user.username == "newuser"
        assert user.password.startswith("$2b$")
        assert fake_user_repository.count() == 1
