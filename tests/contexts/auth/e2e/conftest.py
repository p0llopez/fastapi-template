from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.main import container


@pytest.fixture(scope="session", autouse=True)
def _wire_container() -> None:
    container.wire()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    container.shared_container.engine.reset()
    container.shared_container.session_factory.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
