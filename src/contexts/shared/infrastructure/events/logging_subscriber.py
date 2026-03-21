from loguru import logger

from src.contexts.shared.domain.events import DomainEvent


async def log_domain_event(event: DomainEvent) -> None:
    logger.info(
        "Domain event: {} at {}",
        type(event).__name__,
        event.occurred_on,
    )
