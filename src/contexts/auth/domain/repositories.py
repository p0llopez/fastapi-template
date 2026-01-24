from abc import ABC, abstractmethod
from uuid import UUID

from src.contexts.auth.domain.aggregates import ApiKey, User


class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> None: ...

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def find_api_key_by_key(self, key: str) -> ApiKey | None: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...
