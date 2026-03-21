import pytest
from fastapi import FastAPI

from src.main import app as fastapi_app


@pytest.fixture
def app() -> FastAPI:
    return fastapi_app
