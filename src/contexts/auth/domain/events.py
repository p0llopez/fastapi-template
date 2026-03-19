from dataclasses import dataclass
from uuid import UUID

from src.contexts.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True)
class UserCreatedEvent(DomainEvent):
    user_id: UUID
    username: str


@dataclass(frozen=True, slots=True)
class ApiKeyCreatedEvent(DomainEvent):
    user_id: UUID
    api_key_id: UUID


@dataclass(frozen=True, slots=True)
class ApiKeyRevokedEvent(DomainEvent):
    user_id: UUID
    api_key_id: UUID
