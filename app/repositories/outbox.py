from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.core.enums import OutboxStatus
from app.models import OutboxMessageModel
from app.repositories.base import BaseRepository


class OutboxRepository(BaseRepository[OutboxMessageModel]):
    model = OutboxMessageModel

    async def create_message(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> OutboxMessageModel:
        return await self.create(
            topic=topic,
            payload=payload,
            status=OutboxStatus.PENDING,
        )

    async def get_pending_messages(
        self,
        limit: int = 100,
    ) -> Sequence[OutboxMessageModel]:
        stmt = (
            select(OutboxMessageModel)
            .where(OutboxMessageModel.status == OutboxStatus.PENDING)
            .order_by(OutboxMessageModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_failed_messages(
        self,
        max_retries: int = 3,
        limit: int = 100,
    ) -> Sequence[OutboxMessageModel]:
        stmt = (
            select(OutboxMessageModel)
            .where(OutboxMessageModel.status == OutboxStatus.FAILED)
            .where(OutboxMessageModel.retry_count < max_retries)
            .order_by(OutboxMessageModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def mark_as_processing(self, message_id: UUID) -> OutboxMessageModel | None:
        return await self.update_by_id(message_id, status=OutboxStatus.PROCESSING)

    async def mark_as_sent(self, message_id: UUID) -> OutboxMessageModel | None:
        return await self.update_by_id(
            message_id,
            status=OutboxStatus.SENT,
            processed_at=func.now(),
        )

    async def mark_as_failed(
        self, message_id: UUID, error_message: str | None = None
    ) -> OutboxMessageModel | None:
        message = await self.get_by_id(message_id)
        if message is None:
            return None

        return await self.update_by_id(
            message_id,
            status=OutboxStatus.FAILED,
            error_message=error_message,
            retry_count=message.retry_count + 1,
            processed_at=func.now(),
        )

    async def reset_to_pending(self, message_id: UUID) -> OutboxMessageModel | None:
        return await self.update_by_id(message_id, status=OutboxStatus.PENDING)
