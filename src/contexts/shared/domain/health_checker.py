from abc import ABC, abstractmethod


class HealthChecker(ABC):
    @abstractmethod
    async def check(self) -> dict[str, object]: ...
