from datetime import UTC, datetime, timedelta

from src.contexts.shared.domain.cache_client import CacheClient


class InMemoryCacheClient(CacheClient):
    def __init__(self) -> None:
        self._cache = {}

    def set(self, key: str, value: object, ttl: int = 600) -> None:
        self._cache[key] = {
            "value": value,
            "expires_at": (datetime.now(tz=UTC) + timedelta(seconds=ttl)).timestamp(),
        }

    def get(self, key: str) -> object | None:
        item = self._cache.get(key)
        if item:
            if item["expires_at"] > datetime.now(tz=UTC).timestamp():
                return item["value"]
            self.delete(key)
        return None

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()
