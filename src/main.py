from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from loguru import logger
from pydantic import BaseModel

from src.container import ApplicationContainer
from src.contexts.auth.infrastructure.http import verify_api_key
from src.contexts.shared.infrastructure.http import public
from src.contexts.shared.infrastructure.logger import setup_logger

container = ApplicationContainer()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    container.wire(
        modules=[
            "src.contexts.auth.infrastructure.http.api_key_middleware",
        ]
    )

    try:
        yield
    finally:
        container.unwire()
        logger.complete()


app = FastAPI(
    title="FastAPI Template",
    description=(
        "A FastAPI template with DDD, Clean Architecture, and Dependency Injection"
    ),
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)],
)

setup_logger(app)

# app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


class HealthResponseModel(BaseModel):
    status: str
    msg: str


@app.get("/health", tags=["Health"])
@public
def read_health() -> HealthResponseModel:
    return HealthResponseModel(
        status="healthy",
        msg="This endpoint is public and does not require API key authentication",
    )


@app.get("/health-protected", tags=["Health"])
def protected_endpoint() -> HealthResponseModel:
    return HealthResponseModel(
        status="healthy",
        msg="This endpoint is protected by API key authentication",
    )
