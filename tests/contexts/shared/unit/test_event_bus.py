from dataclasses import dataclass

import pytest

from src.contexts.shared.domain.events import DomainEvent
from src.contexts.shared.infrastructure.events.in_memory_event_bus import (
    InMemoryEventBus,
)


@dataclass(frozen=True, slots=True)
class OrderPlaced(DomainEvent):
    order_id: str


@dataclass(frozen=True, slots=True)
class OrderCancelled(DomainEvent):
    order_id: str


def _make_event(order_id: str = "1") -> OrderPlaced:
    return OrderPlaced(order_id=order_id)


@pytest.mark.unit
class TestInMemoryEventBus:
    async def test_publish_invokes_subscribed_handler(self) -> None:
        bus = InMemoryEventBus()
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        event = _make_event()
        bus.subscribe(OrderPlaced, handler)

        await bus.publish([event])

        assert received == [event]

    async def test_handler_not_invoked_for_different_event_type(self) -> None:
        bus = InMemoryEventBus()
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe(OrderCancelled, handler)

        await bus.publish([_make_event()])

        assert received == []

    async def test_multiple_handlers_for_same_event(self) -> None:
        bus = InMemoryEventBus()
        calls: list[str] = []

        async def first_handler(_event: DomainEvent) -> None:
            calls.append("first")

        async def second_handler(_event: DomainEvent) -> None:
            calls.append("second")

        bus.subscribe(OrderPlaced, first_handler)
        bus.subscribe(OrderPlaced, second_handler)

        await bus.publish([_make_event()])

        assert calls == ["first", "second"]

    async def test_publish_empty_list_does_nothing(self) -> None:
        bus = InMemoryEventBus()
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe(OrderPlaced, handler)

        await bus.publish([])

        assert received == []
