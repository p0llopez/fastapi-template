from dataclasses import dataclass

from src.contexts.auth.domain.errors import InactiveApiKeyError, InvalidApiKeyError
from src.contexts.auth.domain.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class AuthenticateWithApiKeyDTO:
    api_key: str


class AuthenticateWithApiKeyUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, dto: AuthenticateWithApiKeyDTO) -> bool | None:
        user = await self.user_repository.find_by_api_key(dto.api_key)

        if not user:
            raise InvalidApiKeyError

        api_key_entity = user.find_api_key(dto.api_key)

        if not api_key_entity:
            raise InvalidApiKeyError

        if not api_key_entity.is_active:
            raise InactiveApiKeyError

        return True
