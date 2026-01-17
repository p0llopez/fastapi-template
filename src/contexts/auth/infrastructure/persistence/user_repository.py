from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload, sessionmaker

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.auth.infrastructure.persistence.models import ApiKeyModel, UserModel
from src.contexts.shared.domain.cache_client import CacheClient


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
                        self.cache_client.delete(f"api_key:{old_key.api_key}")

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
                        api_key_model.api_key = api_key.api_key
                        api_key_model.is_active = api_key.is_active
                        api_key_model.updated_at = api_key.updated_at
                    else:
                        new_api_key = ApiKeyModel.from_domain(api_key)
                        session.add(new_api_key)

                    self.cache_client.set(f"api_key:{api_key.api_key}", api_key)
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
                    self.cache_client.set(f"api_key:{api_key.api_key}", api_key)

            await session.commit()

            self.cache_client.delete(f"user:{user.user_id}")

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

    async def find_by_email(self, email: str) -> User | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserModel)
                .where(UserModel.email == email)
                .options(selectinload(UserModel.api_keys))
            )
            model = result.scalar_one_or_none()

            if model:
                return model.to_domain()
            return None

    async def find_by_api_key(self, api_key: str) -> User | None:
        cached_api_key = self.cache_client.get(f"api_key:{api_key}")
        if cached_api_key:
            return await self.find_by_id(cached_api_key.user_id)

        async with self.session_factory() as session:
            result = await session.execute(
                select(UserModel)
                .join(ApiKeyModel, UserModel.user_id == ApiKeyModel.user_id)
                .where(ApiKeyModel.api_key == api_key)
                .options(selectinload(UserModel.api_keys))
            )
            model = result.scalar_one_or_none()

            if model:
                user = model.to_domain()
                self.cache_client.set(f"user:{user.user_id}", user)
                return user
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
                    self.cache_client.delete(f"api_key:{api_key.api_key}")

                await session.delete(model)
                await session.commit()

    async def list_all(self) -> list[User]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserModel).options(selectinload(UserModel.api_keys))
            )
            models = result.scalars().all()

            return [model.to_domain() for model in models]
