# Code Review — PR #18

## Issues Found (4)

### 1. CLI `list-users` command will crash at runtime

`ListUsersUseCase.execute()` was changed to return `CursorResult[User]`, but `list_users_command.py` still treats the result as a plain list — calling `len(users)`, `if not users:`, and `for user in users:`. `CursorResult` has no `__len__` and is not iterable, so the CLI will raise `TypeError` on every invocation. The fix is to use `result.items` instead.

**File:** `src/contexts/auth/infrastructure/cli/list_users_command.py:16-39`

### 2. `CreateApiKeyUseCase` silently drops `ApiKeyCreatedEvent`

The aggregate records an `ApiKeyCreatedEvent` when `create_api_key()` is called, but the use case never calls `user.pull_events()` or publishes to the event bus. Both `CreateUserUseCase` and `RevokeApiKeyUseCase` correctly publish events after saving — this one was missed. The use case also does not inject `event_bus` in its constructor.

**File:** `src/contexts/auth/application/use_cases/create_api_key.py:13-27`

### 3. Cursor pagination functions are dead code

`encode_cursor` and `decode_cursor` in `pagination.py` are defined and tested but never called. `UserSQLAlchemyRepository.list_paginated()` uses raw `user_id` strings as cursors (`UserModel.user_id > params.cursor`) instead of the opaque base64 tokens. This means cursors expose user IDs directly to API consumers, backward pagination does not work (`previous_cursor` just echoes back the input), and `InvalidCursorError` is unreachable.

**File:** `src/contexts/auth/infrastructure/persistence/user_repository.py:139-167`

### 4. `CheckHealthUseCase` imports SQLAlchemy in the Application layer

CLAUDE.md defines the architecture as "Application (use cases, inject ports)" with no infrastructure deps. `check_health.py` imports `from sqlalchemy.orm import sessionmaker` directly, leaking infrastructure into the application layer. This should use an abstract port instead.

**File:** `src/contexts/shared/application/use_cases/check_health.py:4-15`
