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
