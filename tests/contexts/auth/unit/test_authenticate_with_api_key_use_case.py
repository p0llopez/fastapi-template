import pytest

from src.contexts.auth.application.use_cases.authenticate_with_api_key import (
    AuthenticateWithApiKeyDTO,
    AuthenticateWithApiKeyUseCase,
)
from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import InactiveApiKeyError, InvalidApiKeyError
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestAuthenticateWithApiKeyUseCase:
    async def test_authenticates_with_valid_key(
        self,
        fake_user_repository: FakeUserRepository,
        sample_user_with_api_key: tuple[User, str],
    ) -> None:
        user, api_key = sample_user_with_api_key
        await fake_user_repository.save(user)
        use_case = AuthenticateWithApiKeyUseCase(fake_user_repository)

        result = await use_case.execute(AuthenticateWithApiKeyDTO(api_key=api_key))

        assert result is True

    async def test_raises_error_for_invalid_key(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        use_case = AuthenticateWithApiKeyUseCase(fake_user_repository)

        with pytest.raises(InvalidApiKeyError):
            await use_case.execute(AuthenticateWithApiKeyDTO(api_key="invalid"))

    async def test_raises_error_for_inactive_key(
        self,
        fake_user_repository: FakeUserRepository,
        sample_user_with_api_key: tuple[User, str],
    ) -> None:
        user, api_key = sample_user_with_api_key
        api_key_entity = user.find_api_key(api_key)
        assert api_key_entity is not None
        user.revoke_api_key(api_key_entity.api_key_id)
        await fake_user_repository.save(user)
        use_case = AuthenticateWithApiKeyUseCase(fake_user_repository)

        with pytest.raises(InactiveApiKeyError):
            await use_case.execute(AuthenticateWithApiKeyDTO(api_key=api_key))
