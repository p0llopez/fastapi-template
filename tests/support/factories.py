from faker import Faker

from src.contexts.auth.domain.aggregates import User
from src.contexts.auth.domain.repositories import UserRepository

fake = Faker()


class UserFactory:
    @staticmethod
    def build(**overrides: object) -> User:
        defaults: dict[str, object] = {
            "username": f"user-{fake.unique.user_name()}",
            "password": fake.sha256(),
            "email": fake.unique.email(),
        }
        defaults.update(overrides)
        return User.create(**defaults)

    @staticmethod
    def with_api_key(**overrides: object) -> tuple[User, str]:
        user = UserFactory.build(**overrides)
        _api_key, plain_key = user.create_api_key()
        return user, plain_key

    @staticmethod
    def with_n_api_keys(
        n: int, **overrides: object
    ) -> tuple[User, list[str]]:
        user = UserFactory.build(**overrides)
        keys = [user.create_api_key()[1] for _ in range(n)]
        return user, keys


class PersistentUserFactory:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def create(self, **overrides: object) -> User:
        user = UserFactory.build(**overrides)
        await self.repo.save(user)
        return user

    async def create_with_api_key(
        self, **overrides: object
    ) -> tuple[User, str]:
        user, plain_key = UserFactory.with_api_key(**overrides)
        await self.repo.save(user)
        return user, plain_key

    async def create_batch(
        self, count: int, **overrides: object
    ) -> list[User]:
        users = [UserFactory.build(**overrides) for _ in range(count)]
        for u in users:
            await self.repo.save(u)
        return users
