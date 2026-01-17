from dataclasses import dataclass

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class ListUsersDTO:
    pass


class ListUsersUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, _dto: ListUsersDTO) -> list[User]:
        return await self.user_repository.list_all()
