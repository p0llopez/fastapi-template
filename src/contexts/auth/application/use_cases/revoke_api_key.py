from dataclasses import dataclass
from uuid import UUID

from src.contexts.auth.domain.errors import ApiKeyNotFoundError, UserNotFoundError
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.auth.domain.services import ApiKeyHasher
from src.contexts.shared.domain.events import EventBus


@dataclass(frozen=True, slots=True)
class RevokeApiKeyDTO:
    user_id: UUID
    api_key: str


class RevokeApiKeyUseCase:
    def __init__(self, user_repository: UserRepository, event_bus: EventBus) -> None:
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def execute(self, dto: RevokeApiKeyDTO) -> None:
        user = await self.user_repository.find_by_id(dto.user_id)

        if not user:
            raise UserNotFoundError(dto.user_id)

        key_hash = ApiKeyHasher.hash(dto.api_key)
        api_key = user.find_api_key_by_hash(key_hash)
        if not api_key:
            raise ApiKeyNotFoundError(dto.api_key)

        user.revoke_api_key(api_key.api_key_id)

        await self.user_repository.save(user)
        await self.event_bus.publish(user.pull_events())
