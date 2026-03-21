from dataclasses import dataclass, field

from src.contexts.shared.domain.health_checker import HealthChecker


@dataclass
class HealthResult:
    status: str = "healthy"
    components: dict[str, dict[str, object]] = field(default_factory=dict)


class CheckHealthUseCase:
    def __init__(self, database_checker: HealthChecker) -> None:
        self.database_checker = database_checker

    async def execute(self) -> HealthResult:
        result = HealthResult()
        db_status = await self.database_checker.check()
        result.components["database"] = db_status
        if db_status["status"] == "unhealthy":
            result.status = "unhealthy"
        return result
