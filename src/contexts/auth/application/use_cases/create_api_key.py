from uuid import UUID

from src.contexts.auth.domain.aggregates import ApiKey
from src.contexts.auth.domain.errors import UserNotFoundError
from src.contexts.auth.domain.repositories import UserRepository


class CreateApiKeyUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, user_id: UUID) -> ApiKey | None:
        user = await self.user_repository.find_by_id(user_id)

        if not user:
            raise UserNotFoundError(user_id)

        api_key = user.create_api_key()

        await self.user_repository.save(user)

        return api_key
