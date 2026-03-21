from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from src.contexts.auth.application.use_cases.create_user import (
    CreateUserDTO,
    CreateUserUseCase,
)
from src.contexts.auth.application.use_cases.delete_user import (
    DeleteUserDTO,
    DeleteUserUseCase,
)
from src.contexts.auth.application.use_cases.get_user import GetUserDTO, GetUserUseCase
from src.contexts.auth.application.use_cases.list_users import (
    ListUsersDTO,
    ListUsersUseCase,
)
from src.contexts.shared.infrastructure.http import public

router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str | None
    is_active: bool
    created_at: str


class PaginatedUsersResponse(BaseModel):
    items: list[UserResponse]
    next_cursor: str | None
    previous_cursor: str | None


@router.post("/users", status_code=201)
@public
@inject
async def create_user(
    request: CreateUserRequest,
    use_case: Annotated[
        CreateUserUseCase,
        Depends(Provide["auth_container.create_user_use_case"]),
    ],
) -> UserResponse:
    user = await use_case.execute(
        CreateUserDTO(
            username=request.username,
            password=request.password,
            email=request.email,
        )
    )
    return UserResponse(
        id=user.user_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.get("/users")
@inject
async def list_users(
    use_case: Annotated[
        ListUsersUseCase,
        Depends(Provide["auth_container.list_users_use_case"]),
    ],
    cursor: str | None = None,
    page_size: int = 20,
) -> PaginatedUsersResponse:
    result = await use_case.execute(ListUsersDTO(cursor=cursor, page_size=page_size))
    return PaginatedUsersResponse(
        items=[
            UserResponse(
                id=user.user_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
            )
            for user in result.items
        ],
        next_cursor=result.next_cursor,
        previous_cursor=result.previous_cursor,
    )


@router.get("/users/{user_id}")
@inject
async def get_user(
    user_id: UUID,
    use_case: Annotated[
        GetUserUseCase,
        Depends(Provide["auth_container.get_user_use_case"]),
    ],
) -> UserResponse:
    user = await use_case.execute(GetUserDTO(user_id=user_id))
    return UserResponse(
        id=user.user_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.delete("/users/{user_id}", status_code=204)
@inject
async def delete_user(
    user_id: UUID,
    use_case: Annotated[
        DeleteUserUseCase,
        Depends(Provide["auth_container.delete_user_use_case"]),
    ],
) -> Response:
    await use_case.execute(DeleteUserDTO(user_id=user_id))
    return Response(status_code=204)
