from typing import Any
from uuid import UUID

from app.broker.schemas import PaymentCreatedEvent
from app.core.enums import PaymentStatus
from app.models import PaymentModel
from app.services.outbox_service import OutboxService
from app.uow import UnitOfWork


class PaymentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create_payment(
        self,
        merchant_id: UUID,
        merchant_order_id: str,
        amount: int,
    ) -> PaymentModel | None:
        async with self.uow as uow:
            if await uow.payments.exists_by_merchant_order_id(merchant_id, merchant_order_id):
                return None

            balance = await uow.balances.get_by_merchant_id_for_update(merchant_id)
            if balance is None or balance.available_amount < amount:
                return None

            if not await uow.balances.reserve_amount(merchant_id, amount):
                return None

            external_invoice_id = f"{merchant_id}_{merchant_order_id}".replace("-", "")

            payment = await uow.payments.create(
                merchant_id=merchant_id,
                merchant_order_id=merchant_order_id,
                external_invoice_id=external_invoice_id,
                amount=amount,
                status=PaymentStatus.CREATED,
            )

            outbox = OutboxService(uow)
            await outbox.enqueue_event(
                topic="payment.created",
                payload=PaymentCreatedEvent(
                    payment_id=str(payment.id),
                    merchant_id=str(merchant_id),
                    external_invoice_id=external_invoice_id,
                    amount=amount,
                    status=payment.status,
                ).model_dump(mode="json"),
            )

            await uow.commit()
            return payment

    async def get_merchant_payments(
        self,
        merchant_id: UUID,
        status: str | None = None,
        cursor: Any = None,
        limit: int = 100,
    ) -> list[PaymentModel]:
        async with self.uow as uow:
            payment_status = None
            if status and status in [s.value for s in PaymentStatus]:
                payment_status = PaymentStatus(status)

            payments = await uow.payments.get_by_merchant_id(
                merchant_id,
                status=payment_status,
                cursor=cursor,
                limit=limit,
            )
            return list(payments)
