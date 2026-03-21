from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.settings import settings


@pytest.fixture(scope="session")
def test_engine() -> AsyncEngine:
    return create_async_engine(settings.database_url, poolclass=NullPool)


@pytest.fixture
async def test_transaction(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()


@pytest.fixture
def test_session_factory(
    test_transaction: AsyncSession,
) -> async_sessionmaker:
    return async_sessionmaker(
        bind=test_transaction,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
