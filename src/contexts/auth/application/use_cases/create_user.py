from dataclasses import dataclass

import bcrypt

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class CreateUserDTO:
    username: str
    password: str
    email: str | None = None


class CreateUserUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, dto: CreateUserDTO) -> User:
        hashed_password = bcrypt.hashpw(
            dto.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user = User.create(
            username=dto.username,
            password=hashed_password,
            email=dto.email,
        )

        await self.user_repository.save(user)

        return user
