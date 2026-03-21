from collections import defaultdict

from src.contexts.shared.domain.events import (
    DomainEvent,
    EventBus,
    EventHandler,
)


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: defaultdict[type[DomainEvent], list[EventHandler]] = (
            defaultdict(list)
        )

    async def publish(self, events: list[DomainEvent]) -> None:
        for event in events:
            for handler in self._handlers[type(event)]:
                await handler(event)

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        self._handlers[event_type].append(handler)
