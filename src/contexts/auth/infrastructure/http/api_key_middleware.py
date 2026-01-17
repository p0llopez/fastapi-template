from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from src.contexts.auth.application.use_cases.authenticate_with_api_key import (
    AuthenticateWithApiKeyDTO,
    AuthenticateWithApiKeyUseCase,
)
from src.contexts.auth.domain.errors import InactiveApiKeyError, InvalidApiKeyError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@inject
async def verify_api_key(
    request: Request,
    authenticate_use_case: Annotated[
        AuthenticateWithApiKeyUseCase,
        Depends(Provide["auth_container.authenticate_with_api_key_use_case"]),
    ],
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> str | None:
    endpoint = request.scope.get("endpoint")
    if endpoint and getattr(endpoint, "is_public", False):
        return None

    if not api_key:
        raise HTTPException(status_code=401, detail="API key missing")

    try:
        await authenticate_use_case.execute(AuthenticateWithApiKeyDTO(api_key=api_key))
    except InvalidApiKeyError as err:
        raise HTTPException(status_code=401, detail="Invalid API key") from err
    except InactiveApiKeyError as err:
        raise HTTPException(status_code=403, detail="API key inactive") from err
    else:
        request.state.api_key = api_key
        return api_key
