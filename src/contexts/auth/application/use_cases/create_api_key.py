from dataclasses import dataclass
from uuid import UUID

from src.contexts.auth.domain.errors import UserNotFoundError
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.shared.domain.events import EventBus


@dataclass(frozen=True, slots=True)
class CreateApiKeyDTO:
    user_id: UUID


class CreateApiKeyUseCase:
    def __init__(self, user_repository: UserRepository, event_bus: EventBus) -> None:
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def execute(self, dto: CreateApiKeyDTO) -> str:
        user = await self.user_repository.find_by_id(dto.user_id)

        if not user:
            raise UserNotFoundError(dto.user_id)

        _api_key, plain_key = user.create_api_key()

        await self.user_repository.save(user)
        await self.event_bus.publish(user.pull_events())

        return plain_key
