from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.core.enums import PaymentStatus
from app.models import PaymentModel
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[PaymentModel]):
    model = PaymentModel

    async def get_by_external_invoice_id(self, external_invoice_id: str) -> PaymentModel | None:
        stmt = select(PaymentModel).where(PaymentModel.external_invoice_id == external_invoice_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> PaymentModel | None:
        stmt = select(PaymentModel).where(PaymentModel.provider_payment_id == provider_payment_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_merchant_id(
        self,
        merchant_id: UUID,
        *,
        status: PaymentStatus | None = None,
        cursor: datetime | None = None,
        limit: int = 100,
    ) -> Sequence[PaymentModel]:
        stmt = select(PaymentModel).where(PaymentModel.merchant_id == merchant_id)

        if status is not None:
            stmt = stmt.where(PaymentModel.status == status)

        if cursor is not None:
            stmt = stmt.where(PaymentModel.created_at < cursor)

        stmt = stmt.order_by(PaymentModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_id_for_update(self, payment_id: UUID) -> PaymentModel | None:
        stmt = select(PaymentModel).where(PaymentModel.id == payment_id).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_external_invoice_id_for_update(
        self, external_invoice_id: str
    ) -> PaymentModel | None:
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.external_invoice_id == external_invoice_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        *,
        provider_status: str | None = None,
        provider_payment_id: str | None = None,
        failure_reason: str | None = None,
    ) -> PaymentModel | None:
        update_data: dict[str, Any] = {"status": status}

        if provider_status is not None:
            update_data["provider_status"] = provider_status
        if provider_payment_id is not None:
            update_data["provider_payment_id"] = provider_payment_id
        if failure_reason is not None:
            update_data["failure_reason"] = failure_reason
        if status in (PaymentStatus.COMPLETED, PaymentStatus.CANCELED, PaymentStatus.FAILED):
            update_data["processed_at"] = func.now()

        return await self.update_by_id(payment_id, **update_data)

    async def exists_by_merchant_order_id(self, merchant_id: UUID, merchant_order_id: str) -> bool:
        stmt = select(PaymentModel.id).where(
            PaymentModel.merchant_id == merchant_id,
            PaymentModel.merchant_order_id == merchant_order_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
