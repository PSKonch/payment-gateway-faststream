from typing import Any
from uuid import UUID

from app.core.enums import PaymentStatus
from app.models import PaymentModel
from app.repositories import BalanceRepository, PaymentRepository
from app.services.provider_service import ProviderService
from app.uow import UnitOfWork


class PaymentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.provider = ProviderService()

    async def create_payment(
        self,
        merchant_id: UUID,
        merchant_order_id: str,
        amount: int,
        webhook_url: str,
    ) -> PaymentModel | None:
        async with self.uow as uow:
            balance_repo: BalanceRepository = uow.balances
            payment_repo: PaymentRepository = uow.payments

            if await payment_repo.exists_by_merchant_order_id(merchant_id, merchant_order_id):
                return None

            balance = await balance_repo.get_by_merchant_id_for_update(merchant_id)
            if balance is None or balance.available_amount < amount:
                return None

            if not await balance_repo.reserve_amount(merchant_id, amount):
                return None

            external_invoice_id = f"{merchant_id}_{merchant_order_id}".replace("-", "")

            payment = await payment_repo.create(
                merchant_id=merchant_id,
                merchant_order_id=merchant_order_id,
                external_invoice_id=external_invoice_id,
                amount=amount,
                status=PaymentStatus.CREATED,
            )

            amount_str = f"{amount / 100:.2f}"
            provider_result = await self.provider.create_payment(
                external_invoice_id=external_invoice_id,
                amount=amount_str,
                callback_url=webhook_url,
            )

            if provider_result:
                payment.provider_payment_id = provider_result.get("id", "")
                payment.status = PaymentStatus.PROCESSING
            else:
                await balance_repo.release_reservation(merchant_id, amount)
                await payment_repo.delete_by_id(payment.id)
                return None

            await uow.commit()
            return payment

    async def handle_webhook(
        self,
        external_invoice_id: str,
        provider_payment_id: str,
        provider_status: str,
    ) -> bool:
        async with self.uow as uow:
            payment_repo: PaymentRepository = uow.payments
            balance_repo: BalanceRepository = uow.balances

            payment = await payment_repo.get_by_external_invoice_id_for_update(external_invoice_id)
            if payment is None:
                return False

            new_status = ProviderService.map_provider_status(provider_status)

            if new_status == PaymentStatus.COMPLETED:
                if await balance_repo.confirm_reservation(payment.merchant_id, payment.amount):
                    await payment_repo.update_status(
                        payment.id,
                        new_status,
                        provider_status=provider_status,
                    )
                    await uow.commit()
                    return True
            elif new_status in (PaymentStatus.CANCELED, PaymentStatus.FAILED):
                await balance_repo.release_reservation(payment.merchant_id, payment.amount)
                await payment_repo.update_status(
                    payment.id,
                    new_status,
                    provider_status=provider_status,
                )
                await uow.commit()
                return True

            return False

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
