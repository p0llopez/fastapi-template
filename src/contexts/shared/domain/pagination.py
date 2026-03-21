import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.contexts.shared.domain.errors import InvalidCursorError


class Cursor:
    _VALID_DIRECTIONS = {"next", "previous"}
    _EXPECTED_PARTS = 3

    def __init__(self, direction: str, created_at: datetime, entity_id: UUID) -> None:
        self.direction = direction
        self.created_at = created_at
        self.entity_id = entity_id

    def encode(self) -> str:
        raw = f"{self.direction}|{self.created_at.isoformat()}|{self.entity_id}"
        return base64.b64encode(raw.encode()).decode()

    @classmethod
    def decode(cls, raw: str) -> Cursor:
        try:
            payload = base64.b64decode(raw.encode()).decode()
        except Exception as exc:
            raise InvalidCursorError("Cursor is not valid base64") from exc

        parts = payload.split("|")
        if len(parts) != cls._EXPECTED_PARTS:
            raise InvalidCursorError("Cursor has unexpected format")

        direction, raw_dt, raw_id = parts

        if direction not in cls._VALID_DIRECTIONS:
            raise InvalidCursorError(f"Unknown cursor direction: {direction!r}")

        try:
            created_at = datetime.fromisoformat(raw_dt)
        except ValueError as exc:
            raise InvalidCursorError("Cursor datetime is invalid") from exc

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        try:
            entity_id = UUID(raw_id)
        except ValueError as exc:
            raise InvalidCursorError("Cursor entity ID is not a valid UUID") from exc

        return cls(direction, created_at, entity_id)

    @classmethod
    def for_next(cls, created_at: datetime, entity_id: UUID) -> Cursor:
        return cls("next", created_at, entity_id)

    @classmethod
    def for_previous(cls, created_at: datetime, entity_id: UUID) -> Cursor:
        return cls("previous", created_at, entity_id)

    @property
    def is_previous(self) -> bool:
        return self.direction == "previous"


@dataclass(frozen=True, slots=True)
class CursorParams:
    _MIN_PAGE_SIZE = 1
    _MAX_PAGE_SIZE = 100

    cursor: str | None = None
    page_size: int = 20

    def __post_init__(self) -> None:
        if not (self._MIN_PAGE_SIZE <= self.page_size <= self._MAX_PAGE_SIZE):
            raise ValueError(
                f"page_size must be between {self._MIN_PAGE_SIZE}"
                f" and {self._MAX_PAGE_SIZE}, got {self.page_size}"
            )


@dataclass(frozen=True, slots=True)
class CursorResult[T]:
    items: list[T]
    next_cursor: str | None
    previous_cursor: str | None
