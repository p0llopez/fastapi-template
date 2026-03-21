from collections.abc import Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from src.container import ApplicationContainer
from src.contexts.shared.infrastructure.cache import InMemoryCacheClient
from src.main import container
from tests.support.factories import PersistentUserFactory


@pytest.fixture
def override_container(
    test_engine: AsyncEngine,
    test_session_factory: async_sessionmaker,
) -> Generator[ApplicationContainer]:
    with (
        container.shared_container.session_factory.override(test_session_factory),
        container.shared_container.engine.override(test_engine),
        container.shared_container.cache_client.override(InMemoryCacheClient()),
    ):
        yield container


@pytest.fixture
def user_factory(override_container: ApplicationContainer) -> PersistentUserFactory:
    repo = override_container.auth_container.user_repository()
    return PersistentUserFactory(repo)
