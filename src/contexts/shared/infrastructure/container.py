from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.contexts.shared.application.use_cases.check_health import CheckHealthUseCase
from src.contexts.shared.infrastructure.cache import InMemoryCacheClient
from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
    InMemoryEventBus,
)
from src.contexts.shared.infrastructure.persistence.database_health_checker import (
    DatabaseHealthChecker,
)
from src.settings import settings


class SharedContainer(containers.DeclarativeContainer):
    engine = providers.Singleton(
        create_async_engine,
        url=settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    session_factory = providers.Singleton(
        sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    cache_client = providers.Singleton(
        InMemoryCacheClient,
    )

    event_bus = providers.Singleton(
        InMemoryEventBus,
    )

    database_health_checker = providers.Factory(
        DatabaseHealthChecker,
        session_factory=session_factory,
    )

    check_health_use_case = providers.Factory(
        CheckHealthUseCase,
        database_checker=database_health_checker,
    )
