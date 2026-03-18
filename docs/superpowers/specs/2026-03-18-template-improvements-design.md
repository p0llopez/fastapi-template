# Template Improvements Design

**Date**: 2026-03-18
**Status**: Approved
**Goal**: Improve the FastAPI template for both production use and portfolio showcase with security, API completeness, operational maturity, and DDD patterns.

## Scope

Six improvements, plus a roadmap section in the README for deferred work.

### 1. API Key Hashing

**Problem**: API keys stored in plain text in the database.

**Solution**: Hash keys with SHA-256 before persisting. Return the plain key only once at creation time.

**Changes**:

- **Domain** (`aggregates.py`): `ApiKey.key` becomes `ApiKey.key_hash: str`. `ApiKey.create()` returns a tuple `(ApiKey, plain_key)` — the domain does not retain the plain value. `User.create_api_key()` propagates the tuple: it calls `ApiKey.create()`, appends the `ApiKey` (with hash) to `self.api_keys`, and returns `(ApiKey, plain_key)`. The plain key flows: `ApiKey.create()` → `User.create_api_key()` → `CreateApiKeyUseCase` → CLI output. After creation, the plain key exists only in the caller's scope.
- **Domain service** (`src/contexts/auth/domain/services.py`): Pure function `hash_api_key(key: str) -> str` using `hashlib.sha256(key.encode()).hexdigest()`. Called by `ApiKey.create()` to produce the hash, and by use cases to hash incoming keys before lookup.
- **Repository** (`repositories.py`): `find_api_key_by_key(key: str)` becomes `find_api_key_by_hash(key_hash: str)`. Hashing happens in the use case before calling the repo.
- **Application**: `AuthenticateWithApiKey` receives the plain key, hashes it, and searches by hash. `CreateApiKeyUseCase` calls `user.create_api_key()`, receives `(ApiKey, plain_key)`, persists via repo, and returns the plain key in its response DTO.
- **Infrastructure**: Column `key` in `api_keys` table becomes `key_hash`. `ApiKeyModel` attributes rename accordingly: `key` → `key_hash` in the model class, `from_domain()`, and `to_domain()`. Alembic migration renames and rehashes existing keys.
- **Cache**: Cache keys become `api_key:{hash}` instead of `api_key:{plain}`. The repository's `save()` method updates all cache operations to use `api_key:{api_key.key_hash}` for both set and delete. The `find_api_key_by_hash()` method looks up cache by `api_key:{key_hash}`. This ensures the cache write path and read path use the same key pattern.

**Why SHA-256 and not bcrypt**: API keys are UUIDs with 128 bits of entropy. They don't need salt or cost factor — SHA-256 is sufficient and doesn't penalize latency on every authenticated request.

### 2. Auth REST Endpoints

**Problem**: All user management is CLI-only. A real project needs HTTP endpoints.

**New endpoints** under `src/contexts/auth/infrastructure/http/router.py`, mounted at `/api/v1/auth`:

| Method | Route | Public | Description |
|--------|-------|--------|-------------|
| `POST` | `/users` | Yes | Create user (returns user without password) |
| `GET` | `/users` | No | List users (cursor-paginated) |
| `GET` | `/users/{user_id}` | No | Get user by ID |
| `DELETE` | `/users/{user_id}` | No | Delete user |

**API key management stays CLI-only** — no HTTP endpoints for creating, revoking, or listing API keys. This keeps the attack surface minimal; keys are managed only from the server with container access.

**New use cases**:
- `GetUser` — find by ID (reuses `find_by_id` from repo).
- `DeleteUser` — uses existing `delete` from repo.

**New error**: `UsernameAlreadyExistsError(ConflictError)` — when creating a duplicate user.

**Duplicate detection**: The repository gains a new method `find_by_username(username: str) -> User | None`. The `CreateUserUseCase` calls it before saving — if a user with that username exists, it raises `UsernameAlreadyExistsError`. This keeps the validation in the application layer and avoids catching SQLAlchemy `IntegrityError` in the use case (which would violate hexagonal architecture). The DB unique constraint remains as a safety net.

**`DeleteUser` behavior**: The use case calls `find_by_id` first. If the user doesn't exist, it raises `UserNotFoundError`. The endpoint returns 404 in that case, 204 on success.

**Response DTOs** (Pydantic BaseModel):
- `UserResponse`: id, username, email (`str | None`), is_active, created_at (no password, no keys).

**`POST /users` is public** because you need to create the first user without having an API key, same pattern as the current CLI.

**Wiring**: Add the router module to `container.wire()` in `lifespan()`.

### 3. Deep Health Check

**Problem**: `/health` returns `{"status": "healthy"}` without verifying anything.

**Solution**: Execute `SELECT 1` against the database and report component status.

**Changes**:

- **New use case** in shared: `CheckHealthUseCase` at `src/contexts/shared/application/use_cases/check_health.py`. Receives `session_factory` via DI, executes `SELECT 1`, catches exceptions.
- **Response**:

```json
{
    "status": "healthy | unhealthy",
    "components": {
        "database": {
            "status": "healthy | unhealthy",
            "latency_ms": 2.3
        }
    }
}
```

- **Endpoint `/health`**: Stays public. Calls the use case. Returns HTTP 503 if any component fails.
- **Endpoint `/health-protected`**: Removed — a health check behind API key auth is not useful for load balancers or orchestrators.
- **DI**: `CheckHealthUseCase` registered in `SharedContainer`.

**Extensibility**: The `components` dict allows adding more checks (cache, external APIs) without changing the interface.

### 4. Cursor-Based Pagination

**Problem**: `list_all()` returns all records without limit.

**Solution**: Bidirectional cursor-based pagination in the shared kernel.

**Shared domain** (`src/contexts/shared/domain/pagination.py`):

```python
@dataclass(frozen=True, slots=True)
class CursorParams:
    cursor: str | None = None  # opaque, base64-encoded
    page_size: int = 20        # min 1, max 100

@dataclass(frozen=True, slots=True)
class CursorResult[T]:
    items: list[T]
    next_cursor: str | None      # None = last page
    previous_cursor: str | None  # None = first page
```

**Cursor encoding**: `base64(direction|created_at|user_id)`. Direction indicates whether the client is requesting "next" or "previous".

**Keyset logic**: `WHERE (created_at, user_id) < (cursor_created_at, cursor_id) ORDER BY created_at DESC, user_id DESC LIMIT page_size + 1`. The +1 detects whether there's a next page without an extra COUNT query.

**Bidirectional navigation**:
- `next_cursor` is built from the last item of the page.
- `previous_cursor` is built from the first item of the page.
- When cursor has direction "previous", the query order is inverted, then results are re-sorted to maintain consistent DESC order.
- First page: `previous_cursor` is `null`. Last page: `next_cursor` is `null`.

**Tie-breaker**: `user_id` guarantees deterministic ordering when multiple records share the same `created_at`.

**Existing `list_all()`** is kept because the CLI uses it for small admin listings.

**New error**: `InvalidCursorError(DomainError)` → 400 for malformed or corrupted cursors.

**HTTP**: `GET /users?cursor=abc123&page_size=20` returns:

```json
{
    "items": [...],
    "next_cursor": "eyJuZXh0...",
    "previous_cursor": "eyJwcmV2..."
}
```

**Edge cases**:
1. Malformed cursor (bad base64 or corrupted internals) → `InvalidCursorError` → 400
2. Cursor pointing to a deleted record — doesn't fail because `WHERE` uses `<`/`>`, not exact match
3. `page_size` out of range (<1 or >100) → validation in `CursorParams`
4. Empty collection → `items=[], next_cursor=None, previous_cursor=None`
5. Exactly `page_size` results — no next, the +1 detects it
6. Identical timestamps — tie-breaker with `user_id` ensures deterministic order
7. Previous on first page → `previous_cursor` is `null`
8. Backward navigation returns items in the same order (DESC) as forward

**Testing**:
- **Unit** (pure domain): cursor encode/decode roundtrip, malformed cursor → error, page_size validation, direction parsing.
- **Unit** (use case with fake repo): empty collection, fewer results than page_size, exactly page_size, more than page_size (next_cursor present), forward and backward navigation.
- **Integration** (real DB): insert N records and paginate forward to the end verifying no duplicates or skips; paginate forward then backward verifying consistency; records with same `created_at` verifying tie-breaker; delete record between paginations verifying no breakage.

### 5. Rate Limiting

**Problem**: No protection against abuse. A client can make unlimited requests.

**Solution**: In-memory sliding window rate limiter as FastAPI middleware.

**Changes**:

- **New module** `src/contexts/shared/infrastructure/http/rate_limit_middleware.py`:
  - Middleware that executes before authentication.
  - Identifies clients by IP (`request.client.host`).
  - Sliding window counter in memory (dict with timestamps per IP).
  - Periodic cleanup of expired entries on each request to prevent unbounded memory growth from unique IPs.
  - Exceeds limit → HTTP 429 with `Retry-After` header.

- **Configuration** in `settings.py`:

```python
rate_limit_requests: int = 100
rate_limit_window_seconds: int = 60
```

- **Response headers** (always present):

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 73
X-RateLimit-Reset: 1711036800
```

- **Excluded paths**: `/health` is excluded to avoid interfering with orchestrator health checks. Configurable via `rate_limit_exclude_paths: list[str]`.

**Why in-memory**: This is a template. In-memory works for single-instance. The README roadmap will mention Redis as an improvement for multi-instance. The interface is clean for swapping implementations.

**Why sliding window**: Fixed window has the burst problem at the edge between windows. Sliding window is fairer and the implementation is straightforward.

**Testing**:
- **Unit**: Counter respects window, expired entries are cleaned up, returns 429 when limit exceeded.
- **E2E**: Make N+1 requests and verify the last one returns 429 with correct headers.

### 6. Domain Events

**Problem**: No mechanism to react to domain happenings. Adding side effects (email, logging, notifications) requires putting logic in use cases, breaking SRP.

**Solution**: Synchronous in-process event system. Aggregates record events, use cases publish them after persisting, handlers react.

**Changes**:

- **Shared domain** (`src/contexts/shared/domain/events.py`):

```python
@dataclass(frozen=True, slots=True)
class DomainEvent:
    occurred_on: datetime

class EventBus(ABC):
    async def publish(self, events: list[DomainEvent]) -> None: ...
    def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None: ...
```

- **AggregateRoot** gains event recording:

```python
class AggregateRoot(BaseModel):
    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def record_event(self, event: DomainEvent) -> None: ...
    def pull_events(self) -> list[DomainEvent]: ...  # returns and clears
```

Note: `PrivateAttr` is required in Pydantic v2 for private attributes. Plain `_events = []` would be ignored or treated as a model field.

- **Auth domain events** (`src/contexts/auth/domain/events.py`):
  - `UserCreatedEvent(user_id, username)`
  - `ApiKeyCreatedEvent(user_id, api_key_id)`
  - `ApiKeyRevokedEvent(user_id, api_key_id)`

- **Aggregates emit events**: `User.create()` records `UserCreatedEvent`, `create_api_key()` records `ApiKeyCreatedEvent`, `revoke_api_key()` records `ApiKeyRevokedEvent`.

- **Infrastructure** (`src/contexts/shared/infrastructure/events/`):
  - `in_memory_event_bus.py`: Implementation with a dict of `{event_type: [handlers]}`. Executes handlers sequentially, async.
  - `logging_subscriber.py`: Example handler that logs all events with loguru. Demonstrates the pattern without adding complexity.

- **Use cases**: After `repository.save()`, call `event_bus.publish(user.pull_events())`.

- **DI**: `EventBus` registered in `SharedContainer`, injected into use cases via `AuthContainer`.

**What this does NOT do**:
- Not eventual consistency — synchronous, same process.
- Does not persist events (not event sourcing).
- No retry or dead letter queue.

This lays the foundation for swapping to an async bus (RabbitMQ, Kafka) without changing the domain.

**Testing**:
- **Unit**: `pull_events()` returns and clears, aggregates record correct events.
- **Unit** (event bus): publish invokes subscribed handlers, handlers for one type are not invoked for another type.
- **Integration**: Full flow — create user → event published → logging handler executed.

### 7. README Roadmap

A `## Roadmap` section at the end of the README listing deferred improvements:

- Redis as distributed cache (replace InMemoryCacheClient)
- JWT auth for user sessions
- Prometheus metrics (`/metrics` endpoint)
- OpenTelemetry distributed tracing
- Distributed rate limiting with Redis
- Event sourcing / domain event persistence
- Roles and permissions (RBAC)

## Migration Strategy

A single Alembic migration that:
1. Renames column `key` to `key_hash` in `api_keys` table.
2. Hashes all existing plain-text keys with SHA-256.
3. Removes the `/health-protected` endpoint (no migration needed, just code removal).

## Files Created or Modified

**New files**:
- `src/contexts/auth/domain/services.py` — API key hashing service
- `src/contexts/auth/domain/events.py` — Auth domain events
- `src/contexts/auth/application/use_cases/get_user.py`
- `src/contexts/auth/application/use_cases/delete_user.py`
- `src/contexts/auth/infrastructure/http/router.py` — Auth REST endpoints
- `src/contexts/shared/domain/pagination.py` — Cursor pagination primitives
- `src/contexts/shared/domain/events.py` — DomainEvent + EventBus interface
- `src/contexts/shared/application/use_cases/check_health.py`
- `src/contexts/shared/infrastructure/events/in_memory_event_bus.py`
- `src/contexts/shared/infrastructure/events/logging_subscriber.py`
- `src/contexts/shared/infrastructure/http/rate_limit_middleware.py`
- New Alembic migration for `key` → `key_hash`
- Tests for all new code

**Modified files**:
- `src/contexts/auth/domain/aggregates.py` — ApiKey.key → key_hash, event recording
- `src/contexts/auth/domain/repositories.py` — find_api_key_by_hash, find_by_username
- `src/contexts/auth/domain/errors.py` — UsernameAlreadyExistsError
- `src/contexts/auth/application/use_cases/authenticate_with_api_key.py` — hash before lookup
- `src/contexts/auth/application/use_cases/create_api_key.py` — return plain key
- `src/contexts/auth/application/use_cases/create_user.py` — publish events
- `src/contexts/auth/application/use_cases/list_users.py` — accept CursorParams
- `src/contexts/auth/infrastructure/persistence/models.py` — key → key_hash
- `src/contexts/auth/infrastructure/persistence/user_repository.py` — hash-based lookup, paginated query
- `src/contexts/auth/infrastructure/container.py` — new use cases, event bus
- `src/contexts/shared/domain/aggregate_root.py` — event recording
- `src/contexts/shared/infrastructure/container.py` — EventBus, CheckHealthUseCase
- `src/contexts/shared/domain/errors.py` — InvalidCursorError
- `src/container.py` — wire new modules
- `src/main.py` — include auth router, remove health-protected, add rate limit middleware, deep health check
- `src/settings.py` — rate limit settings
- `README.md` — roadmap section
