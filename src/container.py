from dependency_injector import containers, providers

from src.contexts.auth.infrastructure.container import AuthContainer
from src.contexts.shared.infrastructure.container import SharedContainer


class ApplicationContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["src.contexts"],
        auto_wire=False,
    )

    shared_container = providers.Container(SharedContainer)

    auth_container = providers.Container(
        AuthContainer,
        shared=shared_container,
    )
