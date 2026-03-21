from abc import ABC, abstractmethod
from uuid import UUID

from src.contexts.auth.domain.aggregates import ApiKey, User
from src.contexts.shared.domain.pagination import CursorParams, CursorResult


class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> None: ...

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def find_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def find_api_key_by_hash(self, key_hash: str) -> ApiKey | None: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...

    @abstractmethod
    async def list_paginated(self, params: CursorParams) -> CursorResult[User]: ...
