# Template Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add API key hashing, auth REST endpoints, deep health check, cursor pagination, rate limiting, and domain events to the FastAPI template.

**Architecture:** Follows the existing hexagonal DDD pattern with bounded contexts. All new domain code is pure Python with no infra deps. New shared kernel primitives (events, pagination) live in `src/contexts/shared/domain/`. Infrastructure implementations follow the established container/provider pattern.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, dependency-injector, Alembic, pytest-asyncio, hashlib (SHA-256)

**Spec:** `docs/superpowers/specs/2026-03-18-template-improvements-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `src/contexts/shared/domain/events.py` | DomainEvent base class + EventBus ABC |
| `src/contexts/shared/domain/pagination.py` | CursorParams, CursorResult, encode/decode |
| `src/contexts/shared/application/use_cases/check_health.py` | CheckHealthUseCase |
| `src/contexts/shared/infrastructure/events/__init__.py` | Package init |
| `src/contexts/shared/infrastructure/events/in_memory_event_bus.py` | InMemoryEventBus |
| `src/contexts/shared/infrastructure/events/logging_subscriber.py` | LoggingSubscriber |
| `src/contexts/shared/infrastructure/http/rate_limit_middleware.py` | SlidingWindowRateLimiter |
| `src/contexts/auth/domain/services.py` | hash_api_key pure function |
| `src/contexts/auth/domain/events.py` | UserCreated, ApiKeyCreated, ApiKeyRevoked events |
| `src/contexts/auth/application/use_cases/get_user.py` | GetUserUseCase |
| `src/contexts/auth/application/use_cases/delete_user.py` | DeleteUserUseCase |
| `src/contexts/auth/infrastructure/http/__init__.py` | (may need update for router export) |
| `src/contexts/auth/infrastructure/http/router.py` | Auth REST endpoints |
| `tests/contexts/shared/unit/test_domain_events.py` | Unit tests for events |
| `tests/contexts/shared/unit/test_event_bus.py` | Unit tests for InMemoryEventBus |
| `tests/contexts/shared/unit/test_pagination.py` | Unit tests for cursor encode/decode |
| `tests/contexts/shared/unit/test_rate_limiter.py` | Unit tests for rate limiter |
| `tests/contexts/shared/unit/test_check_health_use_case.py` | Unit tests for health check |
| `tests/contexts/auth/unit/test_api_key_hashing.py` | Unit tests for hash service |
| `tests/contexts/auth/unit/test_get_user_use_case.py` | Unit tests for GetUser |
| `tests/contexts/auth/unit/test_delete_user_use_case.py` | Unit tests for DeleteUser |
| `tests/contexts/auth/e2e/test_auth_endpoints.py` | E2E tests for auth router |
| New Alembic migration | Rename key → key_hash, hash existing values |

### Modified Files
| File | Changes |
|------|---------|
| `src/contexts/shared/domain/aggregate_root.py` | Add PrivateAttr `_events`, `record_event()`, `pull_events()` |
| `src/contexts/shared/domain/errors.py` | Add `InvalidCursorError` |
| `src/contexts/shared/infrastructure/container.py` | Add EventBus, CheckHealthUseCase providers |
| `src/contexts/auth/domain/aggregates.py` | `ApiKey.key` → `key_hash`, tuple returns, emit events |
| `src/contexts/auth/domain/repositories.py` | `find_api_key_by_hash`, `find_by_username`, `list_paginated` |
| `src/contexts/auth/domain/errors.py` | Add `UsernameAlreadyExistsError` |
| `src/contexts/auth/application/use_cases/authenticate_with_api_key.py` | Hash before lookup |
| `src/contexts/auth/application/use_cases/create_api_key.py` | Return plain key string |
| `src/contexts/auth/application/use_cases/create_user.py` | Duplicate check, publish events, accept EventBus |
| `src/contexts/auth/application/use_cases/list_users.py` | Accept CursorParams, return CursorResult |
| `src/contexts/auth/application/use_cases/revoke_api_key.py` | Find by hash, publish events |
| `src/contexts/auth/infrastructure/persistence/models.py` | `key` → `key_hash` |
| `src/contexts/auth/infrastructure/persistence/user_repository.py` | Hash-based lookup, paginated query, find_by_username |
| `src/contexts/auth/infrastructure/container.py` | New use cases, event_bus dep |
| `src/contexts/auth/infrastructure/cli/create_api_key_command.py` | Print plain key from string |
| `src/contexts/auth/infrastructure/cli/deactivate_api_key_command.py` | Hash key for revocation |
| `src/container.py` | Wire new modules |
| `src/main.py` | Include auth router, deep health, rate limiter, remove health-protected |
| `src/settings.py` | Rate limit settings |
| `tests/contexts/auth/conftest.py` | Update FakeUserRepository for new methods |
| `tests/contexts/auth/unit/test_user_aggregate.py` | Update for key_hash + events |
| `tests/contexts/auth/unit/test_authenticate_with_api_key_use_case.py` | Update for hashing |
| `tests/contexts/auth/unit/test_create_api_key_use_case.py` | Update for plain key return |
| `tests/contexts/auth/unit/test_revoke_api_key_use_case.py` | Update for hash-based find |
| `tests/contexts/auth/e2e/test_health_endpoint.py` | Deep health, remove protected test |
| `README.md` | Roadmap section |

---

### Task 1: Domain Events — Shared Foundation

**Files:**
- Create: `src/contexts/shared/domain/events.py`
- Create: `src/contexts/shared/infrastructure/events/__init__.py`
- Create: `src/contexts/shared/infrastructure/events/in_memory_event_bus.py`
- Create: `src/contexts/shared/infrastructure/events/logging_subscriber.py`
- Modify: `src/contexts/shared/domain/aggregate_root.py`
- Create: `tests/contexts/shared/unit/test_domain_events.py`
- Create: `tests/contexts/shared/unit/test_event_bus.py`

- [ ] **Step 1: Write tests for DomainEvent and AggregateRoot event recording**

```python
# tests/contexts/shared/unit/test_domain_events.py
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.contexts.shared.domain.aggregate_root import AggregateRoot
from src.contexts.shared.domain.events import DomainEvent


class SampleEvent(DomainEvent):
    entity_id: str


class SampleAggregate(AggregateRoot):
    name: str


@pytest.mark.unit
class TestAggregateRootEvents:
    def test_new_aggregate_has_no_events(self) -> None:
        agg = SampleAggregate(name="test")
        assert agg.pull_events() == []

    def test_record_event_and_pull(self) -> None:
        agg = SampleAggregate(name="test")
        event = SampleEvent(occurred_on=datetime.now(UTC), entity_id="123")
        agg.record_event(event)

        events = agg.pull_events()
        assert len(events) == 1
        assert events[0] is event

    def test_pull_events_clears_list(self) -> None:
        agg = SampleAggregate(name="test")
        agg.record_event(SampleEvent(occurred_on=datetime.now(UTC), entity_id="1"))
        agg.pull_events()

        assert agg.pull_events() == []

    def test_multiple_events_preserve_order(self) -> None:
        agg = SampleAggregate(name="test")
        e1 = SampleEvent(occurred_on=datetime.now(UTC), entity_id="1")
        e2 = SampleEvent(occurred_on=datetime.now(UTC), entity_id="2")
        agg.record_event(e1)
        agg.record_event(e2)

        events = agg.pull_events()
        assert events == [e1, e2]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `make test-unit-local`
Expected: FAIL — `src.contexts.shared.domain.events` does not exist

- [ ] **Step 3: Implement DomainEvent and AggregateRoot event recording**

```python
# src/contexts/shared/domain/events.py
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DomainEvent:
    occurred_on: datetime
```

```python
# src/contexts/shared/domain/aggregate_root.py
from pydantic import BaseModel, PrivateAttr

from src.contexts.shared.domain.events import DomainEvent


class AggregateRoot(BaseModel):
    model_config = {"populate_by_name": True}

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `make test-unit-local`
Expected: PASS for all `test_domain_events.py` tests

- [ ] **Step 5: Write tests for InMemoryEventBus**

```python
# tests/contexts/shared/unit/test_event_bus.py
from datetime import UTC, datetime

import pytest

from src.contexts.shared.domain.events import DomainEvent
from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
    InMemoryEventBus,
)


class OrderCreated(DomainEvent):
    order_id: str


class OrderCancelled(DomainEvent):
    order_id: str


@pytest.mark.unit
class TestInMemoryEventBus:
    async def test_publish_invokes_subscribed_handler(self) -> None:
        bus = InMemoryEventBus()
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe(OrderCreated, handler)
        event = OrderCreated(occurred_on=datetime.now(UTC), order_id="1")
        await bus.publish([event])

        assert len(received) == 1
        assert received[0] is event

    async def test_handler_not_invoked_for_different_event_type(self) -> None:
        bus = InMemoryEventBus()
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe(OrderCreated, handler)
        event = OrderCancelled(occurred_on=datetime.now(UTC), order_id="1")
        await bus.publish([event])

        assert len(received) == 0

    async def test_multiple_handlers_for_same_event(self) -> None:
        bus = InMemoryEventBus()
        results: list[str] = []

        async def handler_a(event: DomainEvent) -> None:
            results.append("a")

        async def handler_b(event: DomainEvent) -> None:
            results.append("b")

        bus.subscribe(OrderCreated, handler_a)
        bus.subscribe(OrderCreated, handler_b)
        await bus.publish([OrderCreated(occurred_on=datetime.now(UTC), order_id="1")])

        assert results == ["a", "b"]

    async def test_publish_empty_list_does_nothing(self) -> None:
        bus = InMemoryEventBus()
        await bus.publish([])  # should not raise
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `make test-unit-local`
Expected: FAIL — `in_memory_event_bus` does not exist

- [ ] **Step 7: Implement EventBus ABC and InMemoryEventBus**

Add `EventBus` ABC to `src/contexts/shared/domain/events.py`:

```python
# src/contexts/shared/domain/events.py
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class DomainEvent:
    occurred_on: datetime


EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventBus(ABC):
    @abstractmethod
    async def publish(self, events: list[DomainEvent]) -> None: ...

    @abstractmethod
    def subscribe(
        self, event_type: type[DomainEvent], handler: EventHandler
    ) -> None: ...
```

```python
# src/contexts/shared/infrastructure/events/__init__.py
from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
    InMemoryEventBus,
)

__all__ = ["InMemoryEventBus"]
```

```python
# src/contexts/shared/infrastructure/events/in_memory_event_bus.py
from collections import defaultdict

from src.contexts.shared.domain.events import DomainEvent, EventBus, EventHandler


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    async def publish(self, events: list[DomainEvent]) -> None:
        for event in events:
            for handler in self._handlers.get(type(event), []):
                await handler(event)

    def subscribe(
        self, event_type: type[DomainEvent], handler: EventHandler
    ) -> None:
        self._handlers[event_type].append(handler)
```

```python
# src/contexts/shared/infrastructure/events/logging_subscriber.py
from loguru import logger

from src.contexts.shared.domain.events import DomainEvent


async def log_domain_event(event: DomainEvent) -> None:
    logger.info(f"Domain event: {type(event).__name__} at {event.occurred_on}")
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `make test-unit-local`
Expected: PASS for all `test_domain_events.py` and `test_event_bus.py` tests

- [ ] **Step 9: Run formatter and linter**

Run: `make fmt && make lint`
Expected: Clean

- [ ] **Step 10: Commit**

```bash
git add src/contexts/shared/domain/events.py src/contexts/shared/domain/aggregate_root.py src/contexts/shared/infrastructure/events/ tests/contexts/shared/unit/test_domain_events.py tests/contexts/shared/unit/test_event_bus.py
git commit -m ":sparkles: feat(shared): add domain events foundation and in-memory event bus"
```

---

### Task 2: API Key Hashing — Domain Layer

**Files:**
- Create: `src/contexts/auth/domain/services.py`
- Create: `tests/contexts/auth/unit/test_api_key_hashing.py`
- Modify: `src/contexts/auth/domain/aggregates.py`
- Modify: `src/contexts/auth/domain/errors.py`
- Modify: `src/contexts/auth/domain/repositories.py`
- Modify: `tests/contexts/auth/unit/test_user_aggregate.py`
- Modify: `tests/contexts/auth/conftest.py`

- [ ] **Step 1: Write tests for hash_api_key service**

```python
# tests/contexts/auth/unit/test_api_key_hashing.py
import hashlib

import pytest

from src.contexts.auth.domain.services import hash_api_key


@pytest.mark.unit
class TestHashApiKey:
    def test_returns_sha256_hex_digest(self) -> None:
        key = "test-api-key-123"
        expected = hashlib.sha256(key.encode()).hexdigest()
        assert hash_api_key(key) == expected

    def test_same_input_produces_same_hash(self) -> None:
        assert hash_api_key("my-key") == hash_api_key("my-key")

    def test_different_inputs_produce_different_hashes(self) -> None:
        assert hash_api_key("key-a") != hash_api_key("key-b")

    def test_returns_64_char_hex_string(self) -> None:
        result = hash_api_key("any-key")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-unit-local`
Expected: FAIL — `src.contexts.auth.domain.services` does not exist

- [ ] **Step 3: Implement hash_api_key**

```python
# src/contexts/auth/domain/services.py
import hashlib


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `make test-unit-local`
Expected: PASS for `test_api_key_hashing.py`

- [ ] **Step 5: Update ApiKey aggregate — key → key_hash, tuple return**

Modify `src/contexts/auth/domain/aggregates.py`:

- `ApiKey.key` → `ApiKey.key_hash: str`
- `ApiKey.create()` returns `tuple[ApiKey, str]` (ApiKey with hash, plain key)
- `User.create_api_key()` returns `tuple[ApiKey, str]`
- `User.find_api_key()` parameter changes: searches by hash, not plain text (rename to `find_api_key_by_hash`)

```python
# src/contexts/auth/domain/aggregates.py
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.contexts.auth.domain.errors import ApiKeyNotFoundError
from src.contexts.auth.domain.services import hash_api_key
from src.contexts.shared.domain.aggregate_root import AggregateRoot


class ApiKey(BaseModel):
    api_key_id: UUID = Field(..., alias="id")
    user_id: UUID
    key_hash: str
    updated_at: datetime
    created_at: datetime
    is_active: bool = True

    model_config = {"populate_by_name": True}

    @staticmethod
    def create(user_id: UUID) -> tuple[ApiKey, str]:
        now = datetime.now(UTC)
        plain_key = str(uuid4())
        return (
            ApiKey(
                id=uuid4(),
                user_id=user_id,
                key_hash=hash_api_key(plain_key),
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            plain_key,
        )


class User(AggregateRoot):
    user_id: UUID = Field(..., alias="id")
    email: str | None
    username: str
    password: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    api_keys: list[ApiKey] = Field(default_factory=list)

    @staticmethod
    def create(
        username: str,
        password: str,
        email: str | None = None,
    ) -> User:
        user_id = uuid4()
        now = datetime.now(UTC)
        return User(
            id=user_id,
            username=username,
            password=password,
            is_active=True,
            created_at=now,
            updated_at=now,
            email=email,
            api_keys=[],
        )

    def create_api_key(self) -> tuple[ApiKey, str]:
        api_key, plain_key = ApiKey.create(user_id=self.user_id)
        self.api_keys.append(api_key)
        self.updated_at = datetime.now(UTC)
        return api_key, plain_key

    def revoke_api_key(self, api_key_id: UUID) -> None:
        for api_key in self.api_keys:
            if api_key.api_key_id == api_key_id:
                api_key.is_active = False
                api_key.updated_at = datetime.now(UTC)
                self.updated_at = datetime.now(UTC)
                return
        raise ApiKeyNotFoundError

    def get_active_api_keys(self) -> list[ApiKey]:
        return [key for key in self.api_keys if key.is_active]

    def find_api_key_by_hash(self, key_hash: str) -> ApiKey | None:
        for key in self.api_keys:
            if key.key_hash == key_hash:
                return key
        return None
```

- [ ] **Step 6: Add UsernameAlreadyExistsError**

Add to `src/contexts/auth/domain/errors.py`:

```python
class UsernameAlreadyExistsError(ConflictError):
    def __init__(self, username: str) -> None:
        super().__init__(f"Username '{username}' already exists")
        self.username = username
```

Import `ConflictError` from shared errors (add to existing imports).

- [ ] **Step 7: Update repository interface**

Modify `src/contexts/auth/domain/repositories.py`:

```python
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
    async def list_paginated(
        self, params: CursorParams
    ) -> CursorResult[User]: ...
```

Note: `CursorParams` and `CursorResult` don't exist yet — they will be created in Task 5. For now, add a forward reference or create pagination.py as a stub in the same step. **Better approach: create pagination.py stub now** (just the dataclasses) so the import works.

Create a minimal `src/contexts/shared/domain/pagination.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CursorParams:
    cursor: str | None = None
    page_size: int = 20


@dataclass(frozen=True, slots=True)
class CursorResult[T]:
    items: list[T]
    next_cursor: str | None
    previous_cursor: str | None
```

This stub will be expanded with encode/decode logic in Task 5.

- [ ] **Step 8: Update FakeUserRepository and fixtures**

Modify `tests/contexts/auth/conftest.py`:

```python
from uuid import UUID

import pytest

from src.contexts.auth.domain.aggregates import ApiKey, User
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.shared.domain.pagination import CursorParams, CursorResult


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def save(self, user: User) -> None:
        self._users[user.user_id] = user

    async def find_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    async def find_by_username(self, username: str) -> User | None:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    async def delete(self, user_id: UUID) -> None:
        self._users.pop(user_id, None)

    async def list_all(self) -> list[User]:
        return list(self._users.values())

    async def list_paginated(
        self, params: CursorParams
    ) -> CursorResult[User]:
        users = sorted(
            self._users.values(),
            key=lambda u: (u.created_at, u.user_id),
            reverse=True,
        )
        # Simplified: no cursor logic, just return page_size items
        items = users[: params.page_size]
        return CursorResult(
            items=items, next_cursor=None, previous_cursor=None
        )

    def count(self) -> int:
        return len(self._users)

    async def find_api_key_by_hash(self, key_hash: str) -> ApiKey | None:
        for user in self._users.values():
            for api_key in user.api_keys:
                if api_key.key_hash == key_hash:
                    return api_key
        return None


@pytest.fixture
def fake_user_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def sample_user() -> User:
    return User.create(
        username="testuser",
        password="hashedpassword123",
        email="test@example.com",
    )


@pytest.fixture
def sample_user_with_api_key(sample_user: User) -> tuple[User, str]:
    api_key, plain_key = sample_user.create_api_key()
    return sample_user, plain_key
```

- [ ] **Step 9: Update existing aggregate tests**

Modify `tests/contexts/auth/unit/test_user_aggregate.py`:

```python
from uuid import uuid4

import pytest

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import ApiKeyNotFoundError
from src.contexts.auth.domain.services import hash_api_key


@pytest.mark.unit
class TestUserAggregate:
    def test_create(self) -> None:
        user = User.create(username="johndoe", password="pass123")

        assert user.username == "johndoe"
        assert user.is_active is True
        assert user.api_keys == []

    def test_create_api_key_returns_tuple(self) -> None:
        user = User.create(username="johndoe", password="pass123")

        api_key, plain_key = user.create_api_key()

        assert len(user.api_keys) == 1
        assert api_key.user_id == user.user_id
        assert api_key.is_active is True
        assert api_key.key_hash == hash_api_key(plain_key)

    def test_create_api_key_plain_key_is_not_stored(self) -> None:
        user = User.create(username="johndoe", password="pass123")

        api_key, plain_key = user.create_api_key()

        assert plain_key != api_key.key_hash
        assert not hasattr(api_key, "key") or api_key.key_hash != plain_key

    def test_revoke_api_key(self) -> None:
        user = User.create(username="johndoe", password="pass123")
        api_key, _ = user.create_api_key()

        user.revoke_api_key(api_key.api_key_id)

        assert user.api_keys[0].is_active is False

    def test_revoke_api_key_raises_when_not_found(self) -> None:
        user = User.create(username="johndoe", password="pass123")

        with pytest.raises(ApiKeyNotFoundError):
            user.revoke_api_key(uuid4())

    def test_find_api_key_by_hash(self) -> None:
        user = User.create(username="johndoe", password="pass123")
        api_key, plain_key = user.create_api_key()

        found = user.find_api_key_by_hash(hash_api_key(plain_key))

        assert found is not None
        assert found.api_key_id == api_key.api_key_id

    def test_find_api_key_by_hash_returns_none_for_unknown(self) -> None:
        user = User.create(username="johndoe", password="pass123")

        assert user.find_api_key_by_hash("nonexistent") is None
```

**IMPORTANT: Steps 5-9 of this task MUST be applied atomically.** After Step 5 changes `User.create_api_key()` to return a tuple, existing tests and fixtures will break until Steps 8-9 update them. Do not run tests between Step 5 and Step 9.

- [ ] **Step 10: Run all unit tests**

Run: `make test-unit-local`
Expected: PASS — all existing tests updated, new hash tests pass

- [ ] **Step 11: Run formatter and linter**

Run: `make fmt && make lint`
Expected: Clean

- [ ] **Step 12: Commit**

```bash
git add src/contexts/auth/domain/ src/contexts/shared/domain/pagination.py tests/contexts/auth/
git commit -m ":lock: feat(auth): hash API keys with SHA-256 in domain layer"
```

---

### Task 3: Auth Domain Events

**Files:**
- Create: `src/contexts/auth/domain/events.py`
- Modify: `src/contexts/auth/domain/aggregates.py` (emit events)
- Modify: `tests/contexts/auth/unit/test_user_aggregate.py` (verify events)

- [ ] **Step 1: Write tests for event emission in aggregates**

Add to `tests/contexts/auth/unit/test_user_aggregate.py`:

```python
from src.contexts.auth.domain.events import (
    ApiKeyCreatedEvent,
    ApiKeyRevokedEvent,
    UserCreatedEvent,
)

# Add these test methods inside TestUserAggregate:

    def test_create_records_user_created_event(self) -> None:
        user = User.create(username="johndoe", password="pass123")
        events = user.pull_events()

        assert len(events) == 1
        assert isinstance(events[0], UserCreatedEvent)
        assert events[0].user_id == user.user_id
        assert events[0].username == "johndoe"

    def test_create_api_key_records_event(self) -> None:
        user = User.create(username="johndoe", password="pass123")
        user.pull_events()  # clear creation event
        api_key, _ = user.create_api_key()
        events = user.pull_events()

        assert len(events) == 1
        assert isinstance(events[0], ApiKeyCreatedEvent)
        assert events[0].api_key_id == api_key.api_key_id

    def test_revoke_api_key_records_event(self) -> None:
        user = User.create(username="johndoe", password="pass123")
        api_key, _ = user.create_api_key()
        user.pull_events()  # clear prior events

        user.revoke_api_key(api_key.api_key_id)
        events = user.pull_events()

        assert len(events) == 1
        assert isinstance(events[0], ApiKeyRevokedEvent)
        assert events[0].api_key_id == api_key.api_key_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `make test-unit-local`
Expected: FAIL — `src.contexts.auth.domain.events` does not exist

- [ ] **Step 3: Implement auth domain events**

```python
# src/contexts/auth/domain/events.py
from dataclasses import dataclass
from datetime import datetime
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
```

- [ ] **Step 4: Modify aggregates to emit events**

In `src/contexts/auth/domain/aggregates.py`, add event recording:

- `User.create()`: after creating the user, call `user.record_event(UserCreatedEvent(...))`
- `User.create_api_key()`: after creating key, call `self.record_event(ApiKeyCreatedEvent(...))`
- `User.revoke_api_key()`: after revoking, call `self.record_event(ApiKeyRevokedEvent(...))`

```python
# In User.create():
    @staticmethod
    def create(
        username: str,
        password: str,
        email: str | None = None,
    ) -> User:
        user_id = uuid4()
        now = datetime.now(UTC)
        user = User(
            id=user_id,
            username=username,
            password=password,
            is_active=True,
            created_at=now,
            updated_at=now,
            email=email,
            api_keys=[],
        )
        user.record_event(
            UserCreatedEvent(occurred_on=now, user_id=user_id, username=username)
        )
        return user

# In User.create_api_key():
    def create_api_key(self) -> tuple[ApiKey, str]:
        api_key, plain_key = ApiKey.create(user_id=self.user_id)
        self.api_keys.append(api_key)
        now = datetime.now(UTC)
        self.updated_at = now
        self.record_event(
            ApiKeyCreatedEvent(
                occurred_on=now,
                user_id=self.user_id,
                api_key_id=api_key.api_key_id,
            )
        )
        return api_key, plain_key

# In User.revoke_api_key():
    def revoke_api_key(self, api_key_id: UUID) -> None:
        for api_key in self.api_keys:
            if api_key.api_key_id == api_key_id:
                api_key.is_active = False
                now = datetime.now(UTC)
                api_key.updated_at = now
                self.updated_at = now
                self.record_event(
                    ApiKeyRevokedEvent(
                        occurred_on=now,
                        user_id=self.user_id,
                        api_key_id=api_key_id,
                    )
                )
                return
        raise ApiKeyNotFoundError
```

Add imports at top of aggregates.py:
```python
from src.contexts.auth.domain.events import (
    ApiKeyCreatedEvent,
    ApiKeyRevokedEvent,
    UserCreatedEvent,
)
```

- [ ] **Step 5: Run all unit tests**

Run: `make test-unit-local`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/contexts/auth/domain/events.py src/contexts/auth/domain/aggregates.py tests/contexts/auth/unit/test_user_aggregate.py
git commit -m ":sparkles: feat(auth): emit domain events from User aggregate"
```

---

### Task 4: API Key Hashing — Application Layer

**Files:**
- Modify: `src/contexts/auth/application/use_cases/authenticate_with_api_key.py`
- Modify: `src/contexts/auth/application/use_cases/create_api_key.py`
- Modify: `src/contexts/auth/application/use_cases/create_user.py`
- Modify: `src/contexts/auth/application/use_cases/revoke_api_key.py`
- Modify: `tests/contexts/auth/unit/test_authenticate_with_api_key_use_case.py`
- Modify: `tests/contexts/auth/unit/test_create_api_key_use_case.py`
- Modify: `tests/contexts/auth/unit/test_create_user_use_case.py`
- Modify: `tests/contexts/auth/unit/test_revoke_api_key_use_case.py`

- [ ] **Step 1: Update authenticate use case tests**

```python
# tests/contexts/auth/unit/test_authenticate_with_api_key_use_case.py
import pytest

from src.contexts.auth.application.use_cases.authenticate_with_api_key import (
    AuthenticateWithApiKeyDTO,
    AuthenticateWithApiKeyUseCase,
)
from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import InactiveApiKeyError, InvalidApiKeyError
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestAuthenticateWithApiKeyUseCase:
    async def test_authenticates_with_valid_key(
        self,
        fake_user_repository: FakeUserRepository,
        sample_user_with_api_key: tuple[User, str],
    ) -> None:
        user, plain_key = sample_user_with_api_key
        await fake_user_repository.save(user)
        use_case = AuthenticateWithApiKeyUseCase(fake_user_repository)

        await use_case.execute(AuthenticateWithApiKeyDTO(api_key=plain_key))

    async def test_raises_error_for_invalid_key(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        use_case = AuthenticateWithApiKeyUseCase(fake_user_repository)

        with pytest.raises(InvalidApiKeyError):
            await use_case.execute(AuthenticateWithApiKeyDTO(api_key="invalid"))

    async def test_raises_error_for_inactive_key(
        self,
        fake_user_repository: FakeUserRepository,
        sample_user_with_api_key: tuple[User, str],
    ) -> None:
        user, plain_key = sample_user_with_api_key
        api_key_entity = user.api_keys[0]
        user.revoke_api_key(api_key_entity.api_key_id)
        await fake_user_repository.save(user)
        use_case = AuthenticateWithApiKeyUseCase(fake_user_repository)

        with pytest.raises(InactiveApiKeyError):
            await use_case.execute(AuthenticateWithApiKeyDTO(api_key=plain_key))
```

- [ ] **Step 2: Update authenticate use case implementation**

```python
# src/contexts/auth/application/use_cases/authenticate_with_api_key.py
from dataclasses import dataclass

from src.contexts.auth.domain.errors import InactiveApiKeyError, InvalidApiKeyError
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.auth.domain.services import hash_api_key


@dataclass(frozen=True, slots=True)
class AuthenticateWithApiKeyDTO:
    api_key: str


class AuthenticateWithApiKeyUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, dto: AuthenticateWithApiKeyDTO) -> None:
        key_hash = hash_api_key(dto.api_key)
        api_key = await self.user_repository.find_api_key_by_hash(key_hash)

        if not api_key:
            raise InvalidApiKeyError

        if not api_key.is_active:
            raise InactiveApiKeyError
```

- [ ] **Step 3: Update create_api_key use case tests**

```python
# tests/contexts/auth/unit/test_create_api_key_use_case.py
from uuid import uuid4

import pytest

from src.contexts.auth.application.use_cases.create_api_key import (
    CreateApiKeyDTO,
    CreateApiKeyUseCase,
)
from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import UserNotFoundError
from src.contexts.auth.domain.services import hash_api_key
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestCreateApiKeyUseCase:
    async def test_creates_api_key_for_user(
        self, fake_user_repository: FakeUserRepository, sample_user: User
    ) -> None:
        await fake_user_repository.save(sample_user)
        use_case = CreateApiKeyUseCase(fake_user_repository)

        plain_key = await use_case.execute(
            CreateApiKeyDTO(user_id=sample_user.user_id)
        )

        assert isinstance(plain_key, str)
        assert len(plain_key) == 36  # UUID format

    async def test_plain_key_matches_stored_hash(
        self, fake_user_repository: FakeUserRepository, sample_user: User
    ) -> None:
        await fake_user_repository.save(sample_user)
        use_case = CreateApiKeyUseCase(fake_user_repository)

        plain_key = await use_case.execute(
            CreateApiKeyDTO(user_id=sample_user.user_id)
        )

        stored_user = await fake_user_repository.find_by_id(sample_user.user_id)
        assert stored_user is not None
        assert stored_user.api_keys[0].key_hash == hash_api_key(plain_key)

    async def test_raises_error_for_nonexistent_user(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        use_case = CreateApiKeyUseCase(fake_user_repository)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(CreateApiKeyDTO(user_id=uuid4()))
```

- [ ] **Step 4: Update create_api_key use case — return plain key**

```python
# src/contexts/auth/application/use_cases/create_api_key.py
from dataclasses import dataclass
from uuid import UUID

from src.contexts.auth.domain.errors import UserNotFoundError
from src.contexts.auth.domain.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class CreateApiKeyDTO:
    user_id: UUID


class CreateApiKeyUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, dto: CreateApiKeyDTO) -> str:
        user = await self.user_repository.find_by_id(dto.user_id)

        if not user:
            raise UserNotFoundError(dto.user_id)

        _api_key, plain_key = user.create_api_key()

        await self.user_repository.save(user)

        return plain_key
```

- [ ] **Step 5: Update create_user use case — add duplicate check and event publishing**

```python
# src/contexts/auth/application/use_cases/create_user.py
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
    def __init__(
        self, user_repository: UserRepository, event_bus: EventBus
    ) -> None:
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
```

- [ ] **Step 6: Update create_user tests**

```python
# tests/contexts/auth/unit/test_create_user_use_case.py
import pytest

from src.contexts.auth.application.use_cases.create_user import (
    CreateUserDTO,
    CreateUserUseCase,
)
from src.contexts.auth.domain.errors import UsernameAlreadyExistsError
from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
    InMemoryEventBus,
)
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestCreateUserUseCase:
    async def test_creates_user_with_hashed_password(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        event_bus = InMemoryEventBus()
        use_case = CreateUserUseCase(fake_user_repository, event_bus)

        user = await use_case.execute(
            CreateUserDTO(
                username="johndoe",
                password="plaintext123",
                email="john@example.com",
            )
        )

        assert user.username == "johndoe"
        assert user.password != "plaintext123"
        assert fake_user_repository.count() == 1

    async def test_raises_error_for_duplicate_username(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        event_bus = InMemoryEventBus()
        use_case = CreateUserUseCase(fake_user_repository, event_bus)

        await use_case.execute(
            CreateUserDTO(username="johndoe", password="pass123")
        )

        with pytest.raises(UsernameAlreadyExistsError):
            await use_case.execute(
                CreateUserDTO(username="johndoe", password="pass456")
            )
```

- [ ] **Step 7: Update revoke_api_key use case — find by hash**

```python
# src/contexts/auth/application/use_cases/revoke_api_key.py
from dataclasses import dataclass
from uuid import UUID

from src.contexts.auth.domain.errors import ApiKeyNotFoundError, UserNotFoundError
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.auth.domain.services import hash_api_key
from src.contexts.shared.domain.events import EventBus


@dataclass(frozen=True, slots=True)
class RevokeApiKeyDTO:
    user_id: UUID
    api_key: str


class RevokeApiKeyUseCase:
    def __init__(
        self, user_repository: UserRepository, event_bus: EventBus
    ) -> None:
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def execute(self, dto: RevokeApiKeyDTO) -> None:
        user = await self.user_repository.find_by_id(dto.user_id)

        if not user:
            raise UserNotFoundError(dto.user_id)

        key_hash = hash_api_key(dto.api_key)
        api_key = user.find_api_key_by_hash(key_hash)
        if not api_key:
            raise ApiKeyNotFoundError(dto.api_key)

        user.revoke_api_key(api_key.api_key_id)

        await self.user_repository.save(user)
        await self.event_bus.publish(user.pull_events())
```

- [ ] **Step 8: Update revoke_api_key tests**

Update `tests/contexts/auth/unit/test_revoke_api_key_use_case.py` — the fixture `sample_user_with_api_key` now returns `(User, plain_key)`. Use `plain_key` in `RevokeApiKeyDTO.api_key`.

```python
# tests/contexts/auth/unit/test_revoke_api_key_use_case.py
from uuid import uuid4

import pytest

from src.contexts.auth.application.use_cases.revoke_api_key import (
    RevokeApiKeyDTO,
    RevokeApiKeyUseCase,
)
from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import ApiKeyNotFoundError, UserNotFoundError
from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
    InMemoryEventBus,
)
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestRevokeApiKeyUseCase:
    async def test_revokes_api_key(
        self,
        fake_user_repository: FakeUserRepository,
        sample_user_with_api_key: tuple[User, str],
    ) -> None:
        user, plain_key = sample_user_with_api_key
        await fake_user_repository.save(user)
        event_bus = InMemoryEventBus()
        use_case = RevokeApiKeyUseCase(fake_user_repository, event_bus)

        await use_case.execute(
            RevokeApiKeyDTO(user_id=user.user_id, api_key=plain_key)
        )

        updated = await fake_user_repository.find_by_id(user.user_id)
        assert updated is not None
        assert updated.api_keys[0].is_active is False

    async def test_raises_error_for_nonexistent_user(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        event_bus = InMemoryEventBus()
        use_case = RevokeApiKeyUseCase(fake_user_repository, event_bus)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(
                RevokeApiKeyDTO(user_id=uuid4(), api_key="some-key")
            )

    async def test_raises_error_for_nonexistent_key(
        self,
        fake_user_repository: FakeUserRepository,
        sample_user: User,
    ) -> None:
        await fake_user_repository.save(sample_user)
        event_bus = InMemoryEventBus()
        use_case = RevokeApiKeyUseCase(fake_user_repository, event_bus)

        with pytest.raises(ApiKeyNotFoundError):
            await use_case.execute(
                RevokeApiKeyDTO(
                    user_id=sample_user.user_id, api_key="nonexistent"
                )
            )
```

- [ ] **Step 9: Run all unit tests**

Run: `make test-unit-local`
Expected: PASS

- [ ] **Step 10: Run formatter and linter**

Run: `make fmt && make lint`
Expected: Clean

- [ ] **Step 11: Commit**

```bash
git add src/contexts/auth/application/ tests/contexts/auth/unit/
git commit -m ":lock: feat(auth): hash API keys in use cases and add duplicate username check"
```

---

### Task 5: Cursor Pagination — Domain

**Files:**
- Modify: `src/contexts/shared/domain/pagination.py` (expand stub)
- Modify: `src/contexts/shared/domain/errors.py`
- Create: `tests/contexts/shared/unit/test_pagination.py`

- [ ] **Step 1: Write tests for cursor encode/decode**

```python
# tests/contexts/shared/unit/test_pagination.py
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.contexts.shared.domain.errors import InvalidCursorError
from src.contexts.shared.domain.pagination import (
    CursorParams,
    decode_cursor,
    encode_cursor,
)


@pytest.mark.unit
class TestCursorEncoding:
    def test_encode_decode_next_roundtrip(self) -> None:
        ts = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        uid = uuid4()

        cursor = encode_cursor("next", ts, uid)
        direction, decoded_ts, decoded_uid = decode_cursor(cursor)

        assert direction == "next"
        assert decoded_ts == ts
        assert decoded_uid == uid

    def test_encode_decode_previous_roundtrip(self) -> None:
        ts = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
        uid = uuid4()

        cursor = encode_cursor("previous", ts, uid)
        direction, decoded_ts, decoded_uid = decode_cursor(cursor)

        assert direction == "previous"
        assert decoded_ts == ts
        assert decoded_uid == uid

    def test_decode_malformed_base64_raises(self) -> None:
        with pytest.raises(InvalidCursorError):
            decode_cursor("not-valid-base64!!!")

    def test_decode_invalid_content_raises(self) -> None:
        import base64

        bad = base64.b64encode(b"garbage").decode()
        with pytest.raises(InvalidCursorError):
            decode_cursor(bad)

    def test_decode_wrong_direction_raises(self) -> None:
        import base64

        bad = base64.b64encode(b"sideways|2026-01-01T00:00:00+00:00|" + str(uuid4()).encode()).decode()
        with pytest.raises(InvalidCursorError):
            decode_cursor(bad)


@pytest.mark.unit
class TestCursorParams:
    def test_defaults(self) -> None:
        params = CursorParams()
        assert params.cursor is None
        assert params.page_size == 20

    def test_page_size_too_small_raises(self) -> None:
        with pytest.raises(ValueError):
            CursorParams(page_size=0)

    def test_page_size_too_large_raises(self) -> None:
        with pytest.raises(ValueError):
            CursorParams(page_size=101)

    def test_valid_page_size_boundaries(self) -> None:
        assert CursorParams(page_size=1).page_size == 1
        assert CursorParams(page_size=100).page_size == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `make test-unit-local`
Expected: FAIL — `encode_cursor`, `decode_cursor` not defined

- [ ] **Step 3: Add InvalidCursorError**

Add to `src/contexts/shared/domain/errors.py`:

```python
class InvalidCursorError(DomainError):
    """Raised when a pagination cursor is malformed or corrupted."""
```

- [ ] **Step 4: Implement full pagination module**

```python
# src/contexts/shared/domain/pagination.py
import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.contexts.shared.domain.errors import InvalidCursorError

VALID_DIRECTIONS = {"next", "previous"}


@dataclass(frozen=True, slots=True)
class CursorParams:
    cursor: str | None = None
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page_size < 1 or self.page_size > 100:
            msg = "page_size must be between 1 and 100"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CursorResult[T]:
    items: list[T]
    next_cursor: str | None
    previous_cursor: str | None


def encode_cursor(direction: str, created_at: datetime, entity_id: UUID) -> str:
    payload = f"{direction}|{created_at.isoformat()}|{entity_id}"
    return base64.b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, datetime, UUID]:
    try:
        payload = base64.b64decode(cursor).decode()
        parts = payload.split("|")
        if len(parts) != 3:
            raise InvalidCursorError("Invalid cursor format")

        direction, ts_str, uid_str = parts

        if direction not in VALID_DIRECTIONS:
            raise InvalidCursorError(f"Invalid cursor direction: {direction}")

        created_at = datetime.fromisoformat(ts_str)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        entity_id = UUID(uid_str)
    except InvalidCursorError:
        raise
    except Exception as exc:
        raise InvalidCursorError("Malformed cursor") from exc
    else:
        return direction, created_at, entity_id
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `make test-unit-local`
Expected: PASS

- [ ] **Step 6: Run formatter and linter**

Run: `make fmt && make lint`
Expected: Clean

- [ ] **Step 7: Commit**

```bash
git add src/contexts/shared/domain/pagination.py src/contexts/shared/domain/errors.py tests/contexts/shared/unit/test_pagination.py
git commit -m ":sparkles: feat(shared): add bidirectional cursor pagination primitives"
```

---

### Task 6: API Key Hashing — Infrastructure + Migration

**Files:**
- Modify: `src/contexts/auth/infrastructure/persistence/models.py`
- Modify: `src/contexts/auth/infrastructure/persistence/user_repository.py`
- Modify: `src/contexts/auth/infrastructure/cli/create_api_key_command.py`
- Modify: `src/contexts/auth/infrastructure/cli/deactivate_api_key_command.py`
- Create: new Alembic migration

- [ ] **Step 1: Update ApiKeyModel — key → key_hash**

```python
# In src/contexts/auth/infrastructure/persistence/models.py
# Change ApiKeyModel:

class ApiKeyModel(SQLAlchemyBaseModel):
    __tablename__ = "api_keys"

    api_key_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    key_hash = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False)

    user = relationship("UserModel", back_populates="api_keys")

    @staticmethod
    def from_domain(api_key: ApiKey) -> ApiKeyModel:
        return ApiKeyModel(
            api_key_id=str(api_key.api_key_id),
            user_id=str(api_key.user_id),
            key_hash=api_key.key_hash,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
        )

    def to_domain(self) -> ApiKey:
        return ApiKey(
            id=UUID(str(self.api_key_id)),
            user_id=UUID(str(self.user_id)),
            key_hash=str(self.key_hash),
            is_active=bool(self.is_active),
            created_at=cast("datetime", self.created_at),
            updated_at=cast("datetime", self.updated_at),
        )
```

- [ ] **Step 2: Update UserSQLAlchemyRepository**

In `src/contexts/auth/infrastructure/persistence/user_repository.py`:

- Rename `find_api_key_by_key` → `find_api_key_by_hash`
- Update `save()`: cache operations use `api_key.key_hash` instead of `api_key.key`
- Update `save()`: model sync uses `key_hash` instead of `key`/`api_key`
- Add `find_by_username` method
- Add `list_paginated` method (uses keyset pagination from `decode_cursor`)

Key changes in `save()`:
```python
# In the update path for existing api keys:
api_key_model.key_hash = api_key.key_hash
# NOTE: The current code has `api_key_model.api_key = api_key.key` but the
# actual SQLAlchemy model attribute is `key` (not `api_key`). This is a
# pre-existing bug. The rename fixes it: model attr becomes `key_hash`.

# Cache operations (update both set and delete to use key_hash):
await self.cache_client.set(f"api_key:{api_key.key_hash}", api_key)
await self.cache_client.delete(f"api_key:{old_key.key_hash}")
# NOTE: Current code uses `old_key.api_key` for delete — another reference
# to the non-existent model attribute. Rename to `old_key.key_hash`.
```

New methods:
```python
    async def find_by_username(self, username: str) -> User | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserModel)
                .where(UserModel.username == username)
                .options(selectinload(UserModel.api_keys))
            )
            model = result.scalar_one_or_none()
            if model:
                return model.to_domain()
            return None

    async def find_api_key_by_hash(self, key_hash: str) -> ApiKey | None:
        cached_api_key = await self.cache_client.get(f"api_key:{key_hash}")
        if cached_api_key:
            return cached_api_key

        async with self.session_factory() as session:
            result = await session.execute(
                select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
            )
            model = result.scalar_one_or_none()

            if model:
                api_key_domain = model.to_domain()
                await self.cache_client.set(
                    f"api_key:{key_hash}", api_key_domain
                )
                return api_key_domain
            return None

    async def list_paginated(
        self, params: CursorParams
    ) -> CursorResult[User]:
        from src.contexts.shared.domain.pagination import (
            decode_cursor,
            encode_cursor,
        )

        async with self.session_factory() as session:
            query = select(UserModel).options(selectinload(UserModel.api_keys))

            is_previous = False
            if params.cursor:
                direction, cursor_ts, cursor_id = decode_cursor(params.cursor)
                is_previous = direction == "previous"
                if is_previous:
                    query = query.where(
                        (UserModel.created_at, UserModel.user_id)
                        > (cursor_ts, str(cursor_id))
                    ).order_by(
                        UserModel.created_at.asc(), UserModel.user_id.asc()
                    )
                else:
                    query = query.where(
                        (UserModel.created_at, UserModel.user_id)
                        < (cursor_ts, str(cursor_id))
                    ).order_by(
                        UserModel.created_at.desc(), UserModel.user_id.desc()
                    )
            else:
                query = query.order_by(
                    UserModel.created_at.desc(), UserModel.user_id.desc()
                )

            query = query.limit(params.page_size + 1)
            result = await session.execute(query)
            models = list(result.scalars().all())

            has_more = len(models) > params.page_size
            models = models[: params.page_size]

            if is_previous:
                models.reverse()

            items = [m.to_domain() for m in models]

            next_cursor = None
            previous_cursor = None

            if items:
                last = items[-1]
                first = items[0]

                # Forward nav: next exists if has_more
                # Backward nav: next always exists (we came from a later page)
                if (not is_previous and has_more) or is_previous:
                    next_cursor = encode_cursor(
                        "next", last.created_at, last.user_id
                    )

                # Forward nav: previous exists if we have a cursor (not first page)
                # Backward nav: previous exists if has_more (more earlier pages)
                if (not is_previous and params.cursor) or (
                    is_previous and has_more
                ):
                    previous_cursor = encode_cursor(
                        "previous", first.created_at, first.user_id
                    )

            return CursorResult(
                items=items,
                next_cursor=next_cursor,
                previous_cursor=previous_cursor,
            )
```

- [ ] **Step 3: Update CLI commands**

**Note:** The CLI commands call `container.create_api_key_use_case()` / `container.revoke_api_key_use_case()`, which are provided by the DI container. The container is updated in Task 11. However, we update the CLI *print logic* now since the use case return types have changed. The CLI will fully work after Task 11 updates the container.

In `src/contexts/auth/infrastructure/cli/create_api_key_command.py` — the use case now returns `str` (plain key), not `ApiKey`:

```python
        plain_key = await use_case.execute(CreateApiKeyDTO(user_id=UUID(user_id)))

        console.print("[green]✓[/green] API key created successfully:")
        console.print(f"  • User ID: {user_id}")
        console.print(f"  • API Key: {plain_key}")
        console.print(
            "  • [yellow]Save this key now — it cannot be retrieved again.[/yellow]"
        )
```

In `src/contexts/auth/infrastructure/cli/create_user_command.py` — the use case now takes `event_bus`. Update the command to instantiate a bus inline:

```python
        from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
            InMemoryEventBus,
        )

        shared = SharedContainer()
        container = AuthContainer(shared=shared)
        use_case = CreateUserUseCase(
            container.user_repository(), InMemoryEventBus()
        )
```

In `src/contexts/auth/infrastructure/cli/deactivate_api_key_command.py` — same pattern for event_bus:

```python
        from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
            InMemoryEventBus,
        )

        shared = SharedContainer()
        container = AuthContainer(shared=shared)
        use_case = RevokeApiKeyUseCase(
            container.user_repository(), InMemoryEventBus()
        )
```

These inline bus creations will be cleaned up in Task 11 when the container is updated to provide event_bus to use cases directly.

- [ ] **Step 4: Create Alembic migration**

Run: `make migration-create` (or manually create)

The migration should:

```python
def upgrade() -> None:
    # Rename column
    op.alter_column("api_keys", "key", new_column_name="key_hash")

    # Hash existing plain-text values
    conn = op.get_bind()
    api_keys = conn.execute(sa.text("SELECT api_key_id, key_hash FROM api_keys"))
    for row in api_keys:
        hashed = hashlib.sha256(row.key_hash.encode()).hexdigest()
        conn.execute(
            sa.text("UPDATE api_keys SET key_hash = :hash WHERE api_key_id = :id"),
            {"hash": hashed, "id": row.api_key_id},
        )


def downgrade() -> None:
    # Cannot reverse hash — rename column back but data is lossy
    op.alter_column("api_keys", "key_hash", new_column_name="key")
```

- [ ] **Step 5: Run formatter and linter**

Run: `make fmt && make lint`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/contexts/auth/infrastructure/ migrations/
git commit -m ":lock: feat(auth): hash API keys in infrastructure layer and add migration"
```

---

### Task 7: New Use Cases (GetUser, DeleteUser) + ListUsers Pagination

**Files:**
- Create: `src/contexts/auth/application/use_cases/get_user.py`
- Create: `src/contexts/auth/application/use_cases/delete_user.py`
- Modify: `src/contexts/auth/application/use_cases/list_users.py`
- Create: `tests/contexts/auth/unit/test_get_user_use_case.py`
- Create: `tests/contexts/auth/unit/test_delete_user_use_case.py`
- Modify: `tests/contexts/auth/unit/test_list_users_use_case.py`

- [ ] **Step 1: Write tests for GetUserUseCase**

```python
# tests/contexts/auth/unit/test_get_user_use_case.py
from uuid import uuid4

import pytest

from src.contexts.auth.application.use_cases.get_user import (
    GetUserDTO,
    GetUserUseCase,
)
from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import UserNotFoundError
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestGetUserUseCase:
    async def test_returns_user_by_id(
        self, fake_user_repository: FakeUserRepository, sample_user: User
    ) -> None:
        await fake_user_repository.save(sample_user)
        use_case = GetUserUseCase(fake_user_repository)

        user = await use_case.execute(GetUserDTO(user_id=sample_user.user_id))

        assert user.user_id == sample_user.user_id
        assert user.username == sample_user.username

    async def test_raises_error_for_nonexistent_user(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        use_case = GetUserUseCase(fake_user_repository)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(GetUserDTO(user_id=uuid4()))
```

- [ ] **Step 2: Implement GetUserUseCase**

```python
# src/contexts/auth/application/use_cases/get_user.py
from dataclasses import dataclass
from uuid import UUID

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import UserNotFoundError
from src.contexts.auth.domain.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class GetUserDTO:
    user_id: UUID


class GetUserUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, dto: GetUserDTO) -> User:
        user = await self.user_repository.find_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(dto.user_id)
        return user
```

- [ ] **Step 3: Write tests for DeleteUserUseCase**

```python
# tests/contexts/auth/unit/test_delete_user_use_case.py
from uuid import uuid4

import pytest

from src.contexts.auth.application.use_cases.delete_user import (
    DeleteUserDTO,
    DeleteUserUseCase,
)
from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.errors import UserNotFoundError
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestDeleteUserUseCase:
    async def test_deletes_existing_user(
        self, fake_user_repository: FakeUserRepository, sample_user: User
    ) -> None:
        await fake_user_repository.save(sample_user)
        use_case = DeleteUserUseCase(fake_user_repository)

        await use_case.execute(DeleteUserDTO(user_id=sample_user.user_id))

        assert await fake_user_repository.find_by_id(sample_user.user_id) is None

    async def test_raises_error_for_nonexistent_user(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        use_case = DeleteUserUseCase(fake_user_repository)

        with pytest.raises(UserNotFoundError):
            await use_case.execute(DeleteUserDTO(user_id=uuid4()))
```

- [ ] **Step 4: Implement DeleteUserUseCase**

```python
# src/contexts/auth/application/use_cases/delete_user.py
from dataclasses import dataclass
from uuid import UUID

from src.contexts.auth.domain.errors import UserNotFoundError
from src.contexts.auth.domain.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class DeleteUserDTO:
    user_id: UUID


class DeleteUserUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, dto: DeleteUserDTO) -> None:
        user = await self.user_repository.find_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(dto.user_id)
        await self.user_repository.delete(dto.user_id)
```

- [ ] **Step 5: Update ListUsersUseCase to accept CursorParams**

```python
# src/contexts/auth/application/use_cases/list_users.py
from dataclasses import dataclass

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.shared.domain.pagination import CursorParams, CursorResult


@dataclass(frozen=True, slots=True)
class ListUsersDTO:
    cursor: str | None = None
    page_size: int = 20


class ListUsersUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def execute(self, dto: ListUsersDTO) -> CursorResult[User]:
        params = CursorParams(cursor=dto.cursor, page_size=dto.page_size)
        return await self.user_repository.list_paginated(params)
```

- [ ] **Step 6: Update list users tests**

```python
# tests/contexts/auth/unit/test_list_users_use_case.py
import pytest

from src.contexts.auth.application.use_cases.list_users import (
    ListUsersDTO,
    ListUsersUseCase,
)
from src.contexts.auth.domain.aggregates import User
from tests.contexts.auth.conftest import FakeUserRepository


@pytest.mark.unit
class TestListUsersUseCase:
    async def test_returns_paginated_users(
        self, fake_user_repository: FakeUserRepository, sample_user: User
    ) -> None:
        await fake_user_repository.save(sample_user)
        use_case = ListUsersUseCase(fake_user_repository)

        result = await use_case.execute(ListUsersDTO())

        assert len(result.items) == 1
        assert result.items[0].user_id == sample_user.user_id

    async def test_returns_empty_for_no_users(
        self, fake_user_repository: FakeUserRepository
    ) -> None:
        use_case = ListUsersUseCase(fake_user_repository)

        result = await use_case.execute(ListUsersDTO())

        assert result.items == []
        assert result.next_cursor is None
        assert result.previous_cursor is None
```

- [ ] **Step 7: Run all unit tests**

Run: `make test-unit-local`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/contexts/auth/application/use_cases/ tests/contexts/auth/unit/
git commit -m ":sparkles: feat(auth): add GetUser, DeleteUser use cases and paginate ListUsers"
```

---

### Task 8: Deep Health Check

**Files:**
- Create: `src/contexts/shared/application/__init__.py`
- Create: `src/contexts/shared/application/use_cases/__init__.py`
- Create: `src/contexts/shared/application/use_cases/check_health.py`
- Create: `tests/contexts/shared/unit/test_check_health_use_case.py`

- [ ] **Step 1: Write tests for CheckHealthUseCase**

```python
# tests/contexts/shared/unit/test_check_health_use_case.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.contexts.shared.application.use_cases.check_health import (
    CheckHealthUseCase,
    HealthResult,
)


@pytest.mark.unit
class TestCheckHealthUseCase:
    async def test_returns_healthy_when_db_responds(self) -> None:
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        session.execute = AsyncMock()

        session_factory = MagicMock(return_value=session)

        use_case = CheckHealthUseCase(session_factory)
        result = await use_case.execute()

        assert result.status == "healthy"
        assert result.components["database"]["status"] == "healthy"
        assert "latency_ms" in result.components["database"]

    async def test_returns_unhealthy_when_db_fails(self) -> None:
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        session.execute = AsyncMock(side_effect=Exception("connection refused"))

        session_factory = MagicMock(return_value=session)

        use_case = CheckHealthUseCase(session_factory)
        result = await use_case.execute()

        assert result.status == "unhealthy"
        assert result.components["database"]["status"] == "unhealthy"
```

- [ ] **Step 2: Implement CheckHealthUseCase**

```python
# src/contexts/shared/application/__init__.py
# (empty)

# src/contexts/shared/application/use_cases/__init__.py
# (empty)

# src/contexts/shared/application/use_cases/check_health.py
import time
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


@dataclass
class HealthResult:
    status: str = "healthy"
    components: dict[str, dict[str, object]] = field(default_factory=dict)


class CheckHealthUseCase:
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    async def execute(self) -> HealthResult:
        result = HealthResult()
        db_status = await self._check_database()
        result.components["database"] = db_status

        if db_status["status"] == "unhealthy":
            result.status = "unhealthy"

        return result

    async def _check_database(self) -> dict[str, object]:
        try:
            start = time.perf_counter()
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000
            return {"status": "healthy", "latency_ms": round(latency, 2)}
        except Exception:
            return {"status": "unhealthy", "latency_ms": 0}
```

- [ ] **Step 3: Run tests**

Run: `make test-unit-local`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/contexts/shared/application/ tests/contexts/shared/unit/test_check_health_use_case.py
git commit -m ":sparkles: feat(shared): add deep health check use case with DB verification"
```

---

### Task 9: Rate Limiting

**Files:**
- Create: `src/contexts/shared/infrastructure/http/rate_limit_middleware.py`
- Modify: `src/settings.py`
- Create: `tests/contexts/shared/unit/test_rate_limiter.py`

- [ ] **Step 1: Write tests for the rate limiter**

```python
# tests/contexts/shared/unit/test_rate_limiter.py
import time

import pytest

from src.contexts.shared.infrastructure.http.rate_limit_middleware import (
    SlidingWindowRateLimiter,
)


@pytest.mark.unit
class TestSlidingWindowRateLimiter:
    def test_allows_requests_under_limit(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)

        for _ in range(5):
            assert limiter.is_allowed("192.168.1.1") is True

    def test_blocks_requests_over_limit(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)

        for _ in range(3):
            limiter.is_allowed("192.168.1.1")

        assert limiter.is_allowed("192.168.1.1") is False

    def test_separate_limits_per_ip(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)

        assert limiter.is_allowed("192.168.1.1") is True
        assert limiter.is_allowed("192.168.1.2") is True
        assert limiter.is_allowed("192.168.1.1") is False

    def test_remaining_returns_correct_count(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)
        limiter.is_allowed("ip1")
        limiter.is_allowed("ip1")

        assert limiter.remaining("ip1") == 3

    def test_expired_entries_are_cleaned(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=0.1)

        assert limiter.is_allowed("ip1") is True
        assert limiter.is_allowed("ip1") is False

        time.sleep(0.15)

        assert limiter.is_allowed("ip1") is True

    def test_reset_time_returns_window_end(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)
        limiter.is_allowed("ip1")

        reset = limiter.reset_time("ip1")
        assert reset > time.time()
        assert reset <= time.time() + 60
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `make test-unit-local`
Expected: FAIL — module not found

- [ ] **Step 3: Implement SlidingWindowRateLimiter + middleware**

```python
# src/contexts/shared/infrastructure/http/rate_limit_middleware.py
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, client_id: str) -> None:
        cutoff = time.time() - self._window_seconds
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > cutoff
        ]
        if not self._requests[client_id]:
            del self._requests[client_id]

    def is_allowed(self, client_id: str) -> bool:
        self._cleanup(client_id)
        if len(self._requests[client_id]) >= self._max_requests:
            return False
        self._requests[client_id].append(time.time())
        return True

    def remaining(self, client_id: str) -> int:
        self._cleanup(client_id)
        return max(0, self._max_requests - len(self._requests[client_id]))

    def reset_time(self, client_id: str) -> float:
        timestamps = self._requests.get(client_id, [])
        if not timestamps:
            return time.time() + self._window_seconds
        return timestamps[0] + self._window_seconds


def create_rate_limit_middleware(
    max_requests: int,
    window_seconds: float,
    exclude_paths: list[str] | None = None,
) -> object:
    limiter = SlidingWindowRateLimiter(max_requests, window_seconds)
    excluded = set(exclude_paths or [])

    async def rate_limit_middleware(request: Request, call_next: callable) -> object:
        if request.url.path in excluded:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        if not limiter.is_allowed(client_ip):
            retry_after = int(limiter.reset_time(client_ip) - time.time()) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(limiter.reset_time(client_ip))),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            limiter.remaining(client_ip)
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(limiter.reset_time(client_ip))
        )
        return response

    return rate_limit_middleware
```

- [ ] **Step 4: Add rate limit settings**

In `src/settings.py`, add:

```python
    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100,
        description="Maximum requests per window",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Rate limit window in seconds",
    )
    rate_limit_exclude_paths: list[str] = Field(
        default=["/health"],
        description="Paths excluded from rate limiting",
    )
```

- [ ] **Step 5: Run tests**

Run: `make test-unit-local`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/contexts/shared/infrastructure/http/rate_limit_middleware.py src/settings.py tests/contexts/shared/unit/test_rate_limiter.py
git commit -m ":sparkles: feat(shared): add sliding window rate limiter middleware"
```

---

### Task 10: Auth REST Router

**Files:**
- Create: `src/contexts/auth/infrastructure/http/router.py`
- Create: `tests/contexts/auth/e2e/test_auth_endpoints.py`

- [ ] **Step 1: Implement the auth router**

```python
# src/contexts/auth/infrastructure/http/router.py
from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from src.contexts.auth.application.use_cases.create_user import (
    CreateUserDTO,
    CreateUserUseCase,
)
from src.contexts.auth.application.use_cases.delete_user import (
    DeleteUserDTO,
    DeleteUserUseCase,
)
from src.contexts.auth.application.use_cases.get_user import (
    GetUserDTO,
    GetUserUseCase,
)
from src.contexts.auth.application.use_cases.list_users import (
    ListUsersDTO,
    ListUsersUseCase,
)
from src.contexts.shared.infrastructure.http import public

router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str | None
    is_active: bool
    created_at: str


class PaginatedUsersResponse(BaseModel):
    items: list[UserResponse]
    next_cursor: str | None
    previous_cursor: str | None


@router.post("/users", status_code=201)
@public
@inject
async def create_user(
    body: CreateUserRequest,
    use_case: Annotated[
        CreateUserUseCase,
        Depends(Provide["auth_container.create_user_use_case"]),
    ],
) -> UserResponse:
    user = await use_case.execute(
        CreateUserDTO(
            username=body.username,
            password=body.password,
            email=body.email,
        )
    )
    return UserResponse(
        id=user.user_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.get("/users")
@inject
async def list_users(
    use_case: Annotated[
        ListUsersUseCase,
        Depends(Provide["auth_container.list_users_use_case"]),
    ],
    cursor: str | None = None,
    page_size: int = 20,
) -> PaginatedUsersResponse:
    result = await use_case.execute(
        ListUsersDTO(cursor=cursor, page_size=page_size)
    )
    return PaginatedUsersResponse(
        items=[
            UserResponse(
                id=u.user_id,
                username=u.username,
                email=u.email,
                is_active=u.is_active,
                created_at=u.created_at.isoformat(),
            )
            for u in result.items
        ],
        next_cursor=result.next_cursor,
        previous_cursor=result.previous_cursor,
    )


@router.get("/users/{user_id}")
@inject
async def get_user(
    user_id: UUID,
    use_case: Annotated[
        GetUserUseCase,
        Depends(Provide["auth_container.get_user_use_case"]),
    ],
) -> UserResponse:
    user = await use_case.execute(GetUserDTO(user_id=user_id))
    return UserResponse(
        id=user.user_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.delete("/users/{user_id}", status_code=204)
@inject
async def delete_user(
    user_id: UUID,
    use_case: Annotated[
        DeleteUserUseCase,
        Depends(Provide["auth_container.delete_user_use_case"]),
    ],
) -> Response:
    await use_case.execute(DeleteUserDTO(user_id=user_id))
    return Response(status_code=204)
```

- [ ] **Step 2: Write E2E tests**

```python
# tests/contexts/auth/e2e/test_auth_endpoints.py
import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestAuthEndpoints:
    async def test_create_user_is_public(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/users",
            json={
                "username": "testuser",
                "password": "securepass123",
                "email": "test@example.com",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert "password" not in data

    async def test_list_users_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/users")

        assert response.status_code == 401

    async def test_get_user_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/auth/users/00000000-0000-0000-0000-000000000001"
        )

        assert response.status_code == 401

    async def test_delete_user_requires_auth(self, client: AsyncClient) -> None:
        response = await client.delete(
            "/api/v1/auth/users/00000000-0000-0000-0000-000000000001"
        )

        assert response.status_code == 401
```

- [ ] **Step 3: Run E2E tests** (these will need the full app wired — may fail until Task 11)

Run: `make test-unit-local` (unit tests should still pass)
Expected: PASS for unit tests. E2E tests may need Docker.

- [ ] **Step 4: Commit**

```bash
git add src/contexts/auth/infrastructure/http/router.py tests/contexts/auth/e2e/test_auth_endpoints.py
git commit -m ":sparkles: feat(auth): add REST endpoints for user management"
```

---

### Task 11: Wire Everything Together

**Files:**
- Modify: `src/contexts/auth/infrastructure/container.py`
- Modify: `src/contexts/shared/infrastructure/container.py`
- Modify: `src/container.py`
- Modify: `src/main.py`
- Modify: `tests/contexts/auth/e2e/test_health_endpoint.py`

- [ ] **Step 1: Update SharedContainer**

```python
# src/contexts/shared/infrastructure/container.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.contexts.shared.application.use_cases.check_health import CheckHealthUseCase
from src.contexts.shared.infrastructure.cache import InMemoryCacheClient
from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
    InMemoryEventBus,
)
from src.settings import settings


class SharedContainer(containers.DeclarativeContainer):
    engine = providers.Singleton(
        create_async_engine,
        url=settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    session_factory = providers.Singleton(
        sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    cache_client = providers.Singleton(
        InMemoryCacheClient,
    )

    event_bus = providers.Singleton(
        InMemoryEventBus,
    )

    check_health_use_case = providers.Factory(
        CheckHealthUseCase,
        session_factory=session_factory,
    )
```

- [ ] **Step 2: Update AuthContainer**

```python
# src/contexts/auth/infrastructure/container.py
from dependency_injector import containers, providers

from src.contexts.auth.application.use_cases.authenticate_with_api_key import (
    AuthenticateWithApiKeyUseCase,
)
from src.contexts.auth.application.use_cases.create_api_key import (
    CreateApiKeyUseCase,
)
from src.contexts.auth.application.use_cases.create_user import CreateUserUseCase
from src.contexts.auth.application.use_cases.delete_user import DeleteUserUseCase
from src.contexts.auth.application.use_cases.get_user import GetUserUseCase
from src.contexts.auth.application.use_cases.list_users import ListUsersUseCase
from src.contexts.auth.application.use_cases.revoke_api_key import RevokeApiKeyUseCase
from src.contexts.auth.infrastructure.persistence.user_repository import (
    UserSQLAlchemyRepository,
)


class AuthContainer(containers.DeclarativeContainer):
    shared = providers.DependenciesContainer()

    # Repositories
    user_repository = providers.Factory(
        UserSQLAlchemyRepository,
        session_factory=shared.session_factory,
        cache_client=shared.cache_client,
    )

    # Use cases
    create_api_key_use_case = providers.Factory(
        CreateApiKeyUseCase, user_repository=user_repository
    )
    authenticate_with_api_key_use_case = providers.Factory(
        AuthenticateWithApiKeyUseCase, user_repository=user_repository
    )
    create_user_use_case = providers.Factory(
        CreateUserUseCase,
        user_repository=user_repository,
        event_bus=shared.event_bus,
    )
    list_users_use_case = providers.Factory(
        ListUsersUseCase, user_repository=user_repository
    )
    revoke_api_key_use_case = providers.Factory(
        RevokeApiKeyUseCase,
        user_repository=user_repository,
        event_bus=shared.event_bus,
    )
    get_user_use_case = providers.Factory(
        GetUserUseCase, user_repository=user_repository
    )
    delete_user_use_case = providers.Factory(
        DeleteUserUseCase, user_repository=user_repository
    )
```

- [ ] **Step 3: Update main.py — router, health, rate limiter**

```python
# src/main.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from loguru import logger

from src.container import ApplicationContainer
from src.contexts.auth.infrastructure.http import verify_api_key
from src.contexts.auth.infrastructure.http.router import router as auth_router
from src.contexts.shared.infrastructure.http import public
from src.contexts.shared.infrastructure.http.exception_handlers import (
    register_exception_handlers,
)
from src.contexts.shared.infrastructure.http.rate_limit_middleware import (
    create_rate_limit_middleware,
)
from src.contexts.shared.infrastructure.logger import setup_logger
from src.settings import settings

container = ApplicationContainer()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    container.wire(
        modules=[
            "src.contexts.auth.infrastructure.http.api_key_middleware",
            "src.contexts.auth.infrastructure.http.router",
        ]
    )

    # Subscribe logging handler to domain events
    from src.contexts.shared.infrastructure.events.logging_subscriber import (
        log_domain_event,
    )
    from src.contexts.auth.domain.events import (
        ApiKeyCreatedEvent,
        ApiKeyRevokedEvent,
        UserCreatedEvent,
    )

    event_bus = container.shared_container.event_bus()
    event_bus.subscribe(UserCreatedEvent, log_domain_event)
    event_bus.subscribe(ApiKeyCreatedEvent, log_domain_event)
    event_bus.subscribe(ApiKeyRevokedEvent, log_domain_event)

    try:
        yield
    finally:
        container.unwire()
        logger.complete()


app = FastAPI(
    title="FastAPI Template",
    description=(
        "A FastAPI template with DDD, Clean Architecture, and Dependency Injection"
    ),
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)],
)

setup_logger(app)
register_exception_handlers(app)

app.middleware("http")(
    create_rate_limit_middleware(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        exclude_paths=settings.rate_limit_exclude_paths,
    )
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


@app.get("/health", tags=["Health"])
@public
@inject
async def read_health(
    check_health: Annotated[
        CheckHealthUseCase,
        Depends(Provide["shared_container.check_health_use_case"]),
    ],
) -> JSONResponse:
    result = await check_health.execute()

    status_code = 200 if result.status == "healthy" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": result.status,
            "components": result.components,
        },
    )
```

**Full imports for main.py** (all at top of file):
```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from loguru import logger

from src.container import ApplicationContainer
from src.contexts.auth.infrastructure.http import verify_api_key
from src.contexts.auth.infrastructure.http.router import router as auth_router
from src.contexts.shared.application.use_cases.check_health import CheckHealthUseCase
from src.contexts.shared.infrastructure.http import public
from src.contexts.shared.infrastructure.http.exception_handlers import (
    register_exception_handlers,
)
from src.contexts.shared.infrastructure.http.rate_limit_middleware import (
    create_rate_limit_middleware,
)
from src.contexts.shared.infrastructure.logger import setup_logger
from src.settings import settings
```

- [ ] **Step 4: Update health endpoint tests**

```python
# tests/contexts/auth/e2e/test_health_endpoint.py
import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestHealthEndpoint:
    async def test_returns_healthy_with_components(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data["components"]
        assert data["components"]["database"]["status"] == "healthy"
        assert "latency_ms" in data["components"]["database"]
```

- [ ] **Step 5: Update CLI commands for new use case signatures**

Update `create_api_key_command.py` — use case now returns `str`:
```python
        plain_key = await use_case.execute(CreateApiKeyDTO(user_id=UUID(user_id)))

        console.print("[green]✓[/green] API key created successfully:")
        console.print(f"  • User ID: {user_id}")
        console.print(f"  • API Key: {plain_key}")
        console.print(
            "  • [yellow]Save this key now — it cannot be retrieved again.[/yellow]"
        )
```

Update `deactivate_api_key_command.py` — `RevokeApiKeyUseCase` now needs event_bus. Create bus inline:
```python
        from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
            InMemoryEventBus,
        )

        shared = SharedContainer()
        container = AuthContainer(shared=shared)
        use_case = RevokeApiKeyUseCase(
            container.user_repository(), InMemoryEventBus()
        )
```

Similarly update `create_user_command.py` if it exists — `CreateUserUseCase` now needs event_bus.

- [ ] **Step 6: Run all tests**

Run: `make test-unit-local`
Expected: PASS

- [ ] **Step 7: Run formatter and linter**

Run: `make fmt && make lint`
Expected: Clean

- [ ] **Step 8: Commit**

```bash
git add src/contexts/auth/infrastructure/container.py src/contexts/shared/infrastructure/container.py src/container.py src/main.py src/contexts/auth/infrastructure/cli/ tests/contexts/auth/e2e/test_health_endpoint.py
git commit -m ":wrench: chore: wire all new components into DI containers and main app"
```

---

### Task 12: README Roadmap

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add Roadmap section to README**

Add before the Contributing section:

```markdown
## Roadmap

Planned improvements for future development:

- [ ] **Redis Cache** — Replace InMemoryCacheClient with Redis for distributed caching
- [ ] **JWT Authentication** — Token-based auth for user sessions alongside API keys
- [ ] **Prometheus Metrics** — `/metrics` endpoint for application observability
- [ ] **OpenTelemetry Tracing** — Distributed tracing for request flows
- [ ] **Distributed Rate Limiting** — Redis-backed rate limiter for multi-instance deployments
- [ ] **Event Persistence** — Event sourcing / domain event storage for audit trails
- [ ] **Roles & Permissions (RBAC)** — Role-based access control for fine-grained authorization
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m ":memo: docs: add roadmap section to README"
```

---

## Dependency Order

```
Task 1 (Domain Events) ─┐
                         ├─→ Task 3 (Auth Events) ─→ Task 4 (Use Cases) ─┐
Task 2 (API Key Hash) ──┘                                                │
                                                                          ├─→ Task 6 (Infra + Migration)
Task 5 (Cursor Pagination) ─→ Task 7 (Use Cases + Pagination) ──────────┤
                                                                          ├─→ Task 10 (Auth Router)
Task 8 (Health Check) ──────────────────────────────────────────────────┤
Task 9 (Rate Limiting) ────────────────────────────────────────────────┤
                                                                          ├─→ Task 11 (Wire Everything)
                                                                          └─→ Task 12 (README)
```

Tasks 1, 2, 5, 8, 9 can be worked on in parallel as they have no dependencies on each other.

**Important:** Tasks 2, 3, 4, and 6 form a batch — intermediate states between them will break tests because the aggregate return types and use case signatures change. Apply them sequentially without expecting green tests until Task 4 is complete. Task 6 (infrastructure) can follow after.
