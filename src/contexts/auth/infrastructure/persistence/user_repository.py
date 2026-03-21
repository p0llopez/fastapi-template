from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload, sessionmaker

from src.contexts.auth.domain.aggregates import ApiKey, User
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.auth.infrastructure.persistence.models import ApiKeyModel, UserModel
from src.contexts.shared.domain.cache_client import CacheClient
from src.contexts.shared.domain.pagination import (
    CursorParams,
    CursorResult,
    decode_cursor,
    encode_cursor,
)


class UserSQLAlchemyRepository(UserRepository):
    def __init__(
        self, session_factory: sessionmaker, cache_client: CacheClient
    ) -> None:
        self.session_factory = session_factory
        self.cache_client = cache_client

    async def save(self, user: User) -> None:
        async with self.session_factory() as session:
            existing = await session.execute(
                select(UserModel)
                .where(UserModel.user_id == str(user.user_id))
                .options(selectinload(UserModel.api_keys))
            )
            existing_model = existing.scalar_one_or_none()

            if existing_model:
                existing_model.username = user.username
                existing_model.email = user.email
                existing_model.password = user.password
                existing_model.is_active = user.is_active
                existing_model.updated_at = user.updated_at

                new_api_key_ids = {str(key.api_key_id) for key in user.api_keys}

                for old_key in existing_model.api_keys:
                    if old_key.api_key_id not in new_api_key_ids:
                        await session.delete(old_key)
                        await self.cache_client.delete(
                            f"api_key:{old_key.key_hash}"
                        )

                for api_key in user.api_keys:
                    api_key_model = next(
                        (
                            k
                            for k in existing_model.api_keys
                            if k.api_key_id == str(api_key.api_key_id)
                        ),
                        None,
                    )

                    if api_key_model:
                        api_key_model.key_hash = api_key.key_hash
                        api_key_model.is_active = api_key.is_active
                        api_key_model.updated_at = api_key.updated_at
                    else:
                        new_api_key = ApiKeyModel.from_domain(api_key)
                        session.add(new_api_key)

                    await self.cache_client.set(
                        f"api_key:{api_key.key_hash}", api_key
                    )
            else:
                user_model = UserModel(
                    user_id=str(user.user_id),
                    username=user.username,
                    email=user.email,
                    password=user.password,
                    is_active=user.is_active,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
                session.add(user_model)

                for api_key in user.api_keys:
                    api_key_model = ApiKeyModel.from_domain(api_key)
                    session.add(api_key_model)
                    await self.cache_client.set(
                        f"api_key:{api_key.key_hash}", api_key
                    )

            await session.commit()

    async def find_by_id(self, user_id: UUID) -> User | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserModel)
                .where(UserModel.user_id == str(user_id))
                .options(selectinload(UserModel.api_keys))
            )
            model = result.scalar_one_or_none()

            if model:
                return model.to_domain()
            return None

    async def find_by_username(self, username: str) -> User | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserModel)
                .where(UserModel.username == username)
                .options(selectinload(UserModel.api_keys))
            )
            model = result.scalar_one_or_none()

            if model:
                return model.to_domain()
            return None

    async def delete(self, user_id: UUID) -> None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserModel)
                .where(UserModel.user_id == str(user_id))
                .options(selectinload(UserModel.api_keys))
            )
            model = result.scalar_one_or_none()

            if model:
                for api_key in model.api_keys:
                    await self.cache_client.delete(
                        f"api_key:{api_key.key_hash}"
                    )

                await session.delete(model)
                await session.commit()

    async def list_all(self) -> list[User]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserModel).options(selectinload(UserModel.api_keys))
            )
            models = result.scalars().all()

            return [model.to_domain() for model in models]

    async def list_paginated(
        self, params: CursorParams
    ) -> CursorResult[User]:
        async with self.session_factory() as session:
            query = select(UserModel).options(
                selectinload(UserModel.api_keys)
            )

            is_previous = False
            if params.cursor:
                direction, cursor_ts, cursor_id = decode_cursor(params.cursor)
                is_previous = direction == "previous"
                if is_previous:
                    query = query.where(
                        (UserModel.created_at, UserModel.user_id)
                        > (cursor_ts, str(cursor_id))
                    ).order_by(
                        UserModel.created_at.asc(), UserModel.user_id.asc()
                    )
                else:
                    query = query.where(
                        (UserModel.created_at, UserModel.user_id)
                        < (cursor_ts, str(cursor_id))
                    ).order_by(
                        UserModel.created_at.desc(), UserModel.user_id.desc()
                    )
            else:
                query = query.order_by(
                    UserModel.created_at.desc(), UserModel.user_id.desc()
                )

            query = query.limit(params.page_size + 1)
            result = await session.execute(query)
            models = list(result.scalars().all())

            has_more = len(models) > params.page_size
            models = models[: params.page_size]

            if is_previous:
                models.reverse()

            items = [m.to_domain() for m in models]

            next_cursor = None
            previous_cursor = None

            if items:
                last = items[-1]
                first = items[0]

                if (not is_previous and has_more) or is_previous:
                    next_cursor = encode_cursor(
                        "next", last.created_at, last.user_id
                    )

                if (not is_previous and params.cursor) or (
                    is_previous and has_more
                ):
                    previous_cursor = encode_cursor(
                        "previous", first.created_at, first.user_id
                    )

            return CursorResult(
                items=items,
                next_cursor=next_cursor,
                previous_cursor=previous_cursor,
            )

    async def find_api_key_by_hash(self, key_hash: str) -> ApiKey | None:
        cached_api_key = await self.cache_client.get(f"api_key:{key_hash}")
        if cached_api_key:
            return cached_api_key

        async with self.session_factory() as session:
            result = await session.execute(
                select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
            )
            model = result.scalar_one_or_none()

            if model:
                api_key_domain = model.to_domain()
                await self.cache_client.set(
                    f"api_key:{key_hash}", api_key_domain
                )
                return api_key_domain
            return None
