from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.contexts.shared.domain.aggregate_root import AggregateRoot


class ApiKey(BaseModel):
    api_key_id: UUID = Field(..., alias="id")
    user_id: UUID
    api_key: str
    updated_at: datetime
    created_at: datetime
    is_active: bool = True

    model_config = {"populate_by_name": True}

    @staticmethod
    def create(
        user_id: UUID,
    ) -> "ApiKey":
        now = datetime.now(UTC)
        return ApiKey(
            id=uuid4(),
            user_id=user_id,
            api_key=str(uuid4()),
            is_active=True,
            created_at=now,
            updated_at=now,
        )


class User(AggregateRoot):
    user_id: UUID = Field(..., alias="id")
    email: str | None
    username: str
    password: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    api_keys: list[ApiKey] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @staticmethod
    def create(
        username: str,
        password: str,
        email: str | None = None,
    ) -> "User":
        user_id = uuid4()
        now = datetime.now(UTC)
        return User(
            id=user_id,
            username=username,
            password=password,
            is_active=True,
            created_at=now,
            updated_at=now,
            email=email,
            api_keys=[],
        )

    def create_api_key(self) -> ApiKey:
        api_key = ApiKey.create(user_id=self.user_id)
        self.api_keys.append(api_key)
        self.updated_at = datetime.now(UTC)
        return api_key

    def revoke_api_key(self, api_key_id: UUID) -> bool:
        for api_key in self.api_keys:
            if api_key.api_key_id == api_key_id:
                api_key.is_active = False
                api_key.updated_at = datetime.now(UTC)
                self.updated_at = datetime.now(UTC)
                return True
        return False

    def get_active_api_keys(self) -> list[ApiKey]:
        return [key for key in self.api_keys if key.is_active]

    def find_api_key(self, api_key: str) -> ApiKey | None:
        for key in self.api_keys:
            if key.api_key == api_key:
                return key
        return None
