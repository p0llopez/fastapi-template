from dataclasses import dataclass

import bcrypt

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import UsernameAlreadyExistsError
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.shared.domain.events import EventBus


@dataclass(frozen=True, slots=True)
class CreateUserDTO:
    username: str
    password: str
    email: str | None = None


class CreateUserUseCase:
    def __init__(self, user_repository: UserRepository, event_bus: EventBus) -> None:
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def execute(self, dto: CreateUserDTO) -> User:
        existing = await self.user_repository.find_by_username(dto.username)
        if existing:
            raise UsernameAlreadyExistsError(dto.username)

        hashed_password = bcrypt.hashpw(
            dto.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user = User.create(
            username=dto.username,
            password=hashed_password,
            email=dto.email,
        )

        await self.user_repository.save(user)
        await self.event_bus.publish(user.pull_events())

        return user
