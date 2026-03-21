import base64
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.contexts.shared.domain.errors import InvalidCursorError
from src.contexts.shared.domain.pagination import Cursor, CursorParams


@pytest.mark.unit
class TestCursorParams:
    def test_defaults(self) -> None:
        params = CursorParams()

        assert params.cursor is None
        assert params.page_size == 20

    def test_page_size_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="page_size"):
            CursorParams(page_size=0)

    def test_page_size_above_max_raises(self) -> None:
        with pytest.raises(ValueError, match="page_size"):
            CursorParams(page_size=101)

    def test_page_size_one_is_valid(self) -> None:
        params = CursorParams(page_size=1)

        assert params.page_size == 1

    def test_page_size_one_hundred_is_valid(self) -> None:
        params = CursorParams(page_size=100)

        assert params.page_size == 100


@pytest.mark.unit
class TestCursor:
    def test_encode_decode_next_roundtrip(self) -> None:
        entity_id = uuid4()
        created_at = datetime(2024, 6, 15, 12, 30, 0, tzinfo=UTC)

        encoded = Cursor.for_next(created_at, entity_id).encode()
        cursor = Cursor.decode(encoded)

        assert cursor.direction == "next"
        assert cursor.created_at == created_at
        assert cursor.entity_id == entity_id

    def test_encode_decode_previous_roundtrip(self) -> None:
        entity_id = uuid4()
        created_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)

        encoded = Cursor.for_previous(created_at, entity_id).encode()
        cursor = Cursor.decode(encoded)

        assert cursor.direction == "previous"
        assert cursor.created_at == created_at
        assert cursor.entity_id == entity_id

    def test_is_previous_property(self) -> None:
        cursor = Cursor.for_previous(datetime.now(UTC), uuid4())

        assert cursor.is_previous is True

    def test_is_previous_false_for_next(self) -> None:
        cursor = Cursor.for_next(datetime.now(UTC), uuid4())

        assert cursor.is_previous is False

    def test_decode_malformed_base64_raises(self) -> None:
        with pytest.raises(InvalidCursorError):
            Cursor.decode("not-valid-base64!!!")

    def test_decode_valid_base64_invalid_content_raises(self) -> None:
        garbage = base64.b64encode(b"garbage").decode()

        with pytest.raises(InvalidCursorError):
            Cursor.decode(garbage)

    def test_decode_wrong_direction_raises(self) -> None:
        entity_id = uuid4()
        created_at = datetime(2024, 1, 1, tzinfo=UTC)
        raw = f"sideways|{created_at.isoformat()}|{entity_id}"
        encoded = base64.b64encode(raw.encode()).decode()

        with pytest.raises(InvalidCursorError):
            Cursor.decode(encoded)

    def test_decode_naive_datetime_gets_utc(self) -> None:
        entity_id = uuid4()
        raw = f"next|2024-03-10T08:00:00|{entity_id}"
        encoded = base64.b64encode(raw.encode()).decode()

        cursor = Cursor.decode(encoded)

        assert cursor.created_at.tzinfo is not None
        assert cursor.created_at == datetime(2024, 3, 10, 8, 0, 0, tzinfo=UTC)
