import pytest

from src.contexts.shared.application.use_cases.check_health import (
    CheckHealthUseCase,
)
from src.contexts.shared.domain.health_checker import HealthChecker


class FakeHealthyChecker(HealthChecker):
    async def check(self) -> dict[str, object]:
        return {"status": "healthy", "latency_ms": 1.5}


class FakeUnhealthyChecker(HealthChecker):
    async def check(self) -> dict[str, object]:
        return {"status": "unhealthy", "latency_ms": 0}


@pytest.mark.unit
class TestCheckHealthUseCase:
    async def test_returns_healthy_when_db_responds(self) -> None:
        use_case = CheckHealthUseCase(database_checker=FakeHealthyChecker())

        result = await use_case.execute()

        assert result.status == "healthy"
        assert "database" in result.components
        assert result.components["database"]["status"] == "healthy"
        assert isinstance(result.components["database"]["latency_ms"], float)

    async def test_returns_unhealthy_when_db_fails(self) -> None:
        use_case = CheckHealthUseCase(database_checker=FakeUnhealthyChecker())

        result = await use_case.execute()

        assert result.status == "unhealthy"
        assert "database" in result.components
        assert result.components["database"]["status"] == "unhealthy"
        assert result.components["database"]["latency_ms"] == 0
