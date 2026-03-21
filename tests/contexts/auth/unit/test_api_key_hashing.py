import pytest

from src.contexts.auth.domain.services import ApiKeyHasher


@pytest.mark.unit
class TestApiKeyHashing:
    def test_returns_sha256_hex_digest(self) -> None:
        result = ApiKeyHasher.hash("test-key")

        assert (
            result == "62af8704764faf8ea82fc61ce9c4c3908b6cb97d463a634e9e587d7c885db0ef"
        )

    def test_is_deterministic(self) -> None:
        first = ApiKeyHasher.hash("same-key")
        second = ApiKeyHasher.hash("same-key")

        assert first == second

    def test_produces_64_char_hex_string(self) -> None:
        result = ApiKeyHasher.hash("any-key")

        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)
