from collections.abc import AsyncGenerator

import pytest
from _pytest.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.main import app as fastapi_app


@pytest.fixture
def app() -> FastAPI:
    return fastapi_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def pytest_configure(config: Config) -> None:
    config.addinivalue_line("markers", "unit: Unit tests (fast, no I/O)")
    config.addinivalue_line("markers", "integration: Integration tests (with DB)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full HTTP flow)")
    config.addinivalue_line("markers", "slow: Slow running tests")
