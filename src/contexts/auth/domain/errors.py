from uuid import UUID


class AuthError(Exception):
    pass


class InvalidApiKeyError(AuthError):
    def __init__(self, message: str = "The provided API key is invalid.") -> None:
        super().__init__(message)


class InactiveApiKeyError(AuthError):
    def __init__(self, message: str = "The provided API key is inactive.") -> None:
        super().__init__(message)


class UserNotFoundError(AuthError):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User with id {user_id} not found")
        self.user_id = user_id


class ApiKeyNotFoundError(AuthError):
    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(
            f"API key not found: {api_key}" if api_key else "API key not found"
        )
        self.api_key = api_key
