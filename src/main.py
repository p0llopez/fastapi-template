from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from loguru import logger

from src.container import ApplicationContainer
from src.contexts.auth.infrastructure.http import verify_api_key
from src.contexts.auth.infrastructure.http.router import router as auth_router
from src.contexts.shared.application.use_cases.check_health import CheckHealthUseCase
from src.contexts.shared.infrastructure.events.subscriber_registry import (
    register_event_subscribers,
)
from src.contexts.shared.infrastructure.http import public
from src.contexts.shared.infrastructure.http.exception_handlers import (
    register_exception_handlers,
)
from src.contexts.shared.infrastructure.http.rate_limit_middleware import (
    create_rate_limit_middleware,
)
from src.contexts.shared.infrastructure.logger import setup_logger
from src.settings import settings

container = ApplicationContainer()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    container.wire()
    register_event_subscribers(container.shared_container.event_bus())

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
register_exception_handlers(app)

app.middleware("http")(
    create_rate_limit_middleware(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        exclude_paths=settings.rate_limit_exclude_paths,
    )
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


@app.get("/health", tags=["Health"])
@public
@inject
async def read_health(
    check_health: Annotated[
        CheckHealthUseCase,
        Depends(Provide["shared_container.check_health_use_case"]),
    ],
) -> JSONResponse:
    result = await check_health.execute()
    status_code = 200 if result.status == "healthy" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": result.status,
            "components": result.components,
        },
    )
