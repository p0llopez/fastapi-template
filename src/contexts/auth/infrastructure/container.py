from dependency_injector import containers, providers

from src.contexts.auth.application.use_cases.authenticate_with_api_key import (
    AuthenticateWithApiKeyUseCase,
)
from src.contexts.auth.application.use_cases.create_api_key import (
    CreateApiKeyUseCase,
)
from src.contexts.auth.application.use_cases.create_user import CreateUserUseCase
from src.contexts.auth.application.use_cases.delete_user import DeleteUserUseCase
from src.contexts.auth.application.use_cases.get_user import GetUserUseCase
from src.contexts.auth.application.use_cases.list_users import ListUsersUseCase
from src.contexts.auth.application.use_cases.revoke_api_key import RevokeApiKeyUseCase
from src.contexts.auth.infrastructure.persistence.user_repository import (
    UserSQLAlchemyRepository,
)


class AuthContainer(containers.DeclarativeContainer):
    shared = providers.DependenciesContainer()

    # Repositories
    user_repository = providers.Factory(
        UserSQLAlchemyRepository,
        session_factory=shared.session_factory,
        cache_client=shared.cache_client,
    )

    # Use cases
    create_api_key_use_case = providers.Factory(
        CreateApiKeyUseCase,
        user_repository=user_repository,
        event_bus=shared.event_bus,
    )
    authenticate_with_api_key_use_case = providers.Factory(
        AuthenticateWithApiKeyUseCase, user_repository=user_repository
    )
    create_user_use_case = providers.Factory(
        CreateUserUseCase,
        user_repository=user_repository,
        event_bus=shared.event_bus,
    )
    list_users_use_case = providers.Factory(
        ListUsersUseCase, user_repository=user_repository
    )
    revoke_api_key_use_case = providers.Factory(
        RevokeApiKeyUseCase,
        user_repository=user_repository,
        event_bus=shared.event_bus,
    )
    get_user_use_case = providers.Factory(
        GetUserUseCase, user_repository=user_repository
    )
    delete_user_use_case = providers.Factory(
        DeleteUserUseCase, user_repository=user_repository
    )
