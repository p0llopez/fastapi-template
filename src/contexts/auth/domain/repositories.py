from abc import ABC, abstractmethod
from uuid import UUID

from src.contexts.auth.domain.aggregates import User


class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> None: ...

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def find_by_api_key(self, api_key: str) -> User | None: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...
