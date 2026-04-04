from typing import Any
from uuid import UUID

from app.uow import UnitOfWork


class OutboxService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create_event(self, topic: str, payload: dict[str, Any]) -> None:
        async with self.uow as uow:
            await uow.outbox.create_message(topic=topic, payload=payload)
            await uow.commit()

    async def get_pending_events(self, limit: int = 100) -> list[Any]:
        async with self.uow as uow:
            messages = await uow.outbox.get_pending_messages(limit=limit)
            return list(messages)

    async def mark_as_sent(self, message_id: UUID) -> None:
        async with self.uow as uow:
            await uow.outbox.mark_as_sent(message_id)
            await uow.commit()

    async def mark_as_failed(self, message_id: UUID, error: str | None = None) -> None:
        async with self.uow as uow:
            await uow.outbox.mark_as_failed(message_id, error_message=error)
            await uow.commit()
