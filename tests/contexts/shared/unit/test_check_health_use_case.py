from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.shared.application.use_cases.check_health import (
    CheckHealthUseCase,
)


def _make_session_factory(raise_exception: bool = False) -> MagicMock:
    session = AsyncMock()
    if raise_exception:
        session.execute.side_effect = Exception("DB connection failed")
    else:
        session.execute.return_value = None

    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = session
    context_manager.__aexit__.return_value = None

    session_factory = MagicMock()
    session_factory.return_value = context_manager
    return session_factory


@pytest.mark.unit
class TestCheckHealthUseCase:
    async def test_returns_healthy_when_db_responds(self) -> None:
        session_factory = _make_session_factory(raise_exception=False)
        use_case = CheckHealthUseCase(session_factory)

        result = await use_case.execute()

        assert result.status == "healthy"
        assert "database" in result.components
        assert result.components["database"]["status"] == "healthy"
        assert isinstance(result.components["database"]["latency_ms"], float)

    async def test_returns_unhealthy_when_db_fails(self) -> None:
        session_factory = _make_session_factory(raise_exception=True)
        use_case = CheckHealthUseCase(session_factory)

        result = await use_case.execute()

        assert result.status == "unhealthy"
        assert "database" in result.components
        assert result.components["database"]["status"] == "unhealthy"
        assert result.components["database"]["latency_ms"] == 0
