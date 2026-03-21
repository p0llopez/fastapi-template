import time

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.contexts.shared.domain.health_checker import HealthChecker


class DatabaseHealthChecker(HealthChecker):
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    async def check(self) -> dict[str, object]:
        try:
            start = time.perf_counter()
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000
            return {"status": "healthy", "latency_ms": round(latency, 2)}
        except Exception:
            return {"status": "unhealthy", "latency_ms": 0}
