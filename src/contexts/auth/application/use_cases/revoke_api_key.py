from dataclasses import dataclass
from uuid import UUID

from src.contexts.auth.domain.errors import ApiKeyNotFoundError, UserNotFoundError
from src.contexts.auth.domain.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class RevokeApiKeyDTO:
    user_id: UUID
    api_key: str


class RevokeApiKeyUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, dto: RevokeApiKeyDTO) -> None:
        user = await self.user_repository.find_by_id(dto.user_id)

        if not user:
            raise UserNotFoundError(dto.user_id)

        api_key = next(
            (key for key in user.api_keys if key.api_key == dto.api_key),
            None,
        )
        if not api_key:
            raise ApiKeyNotFoundError(UUID(dto.api_key))

        user.revoke_api_key(UUID(dto.api_key))

        await self.user_repository.save(user)
