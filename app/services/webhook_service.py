from typing import Any
from uuid import UUID

from app.core.enums import PaymentStatus, ProviderStatus
from app.repositories import BalanceRepository, PaymentRepository
from app.uow import UnitOfWork


class WebhookService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def handle_provider_webhook(
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

            if payment.provider_payment_id is None:
                payment.provider_payment_id = provider_payment_id

            try:
                new_status = ProviderStatus(provider_status)
            except ValueError:
                return False

            if payment.status in (
                PaymentStatus.COMPLETED,
                PaymentStatus.CANCELED,
                PaymentStatus.FAILED,
            ):
                return True

            if new_status == ProviderStatus.COMPLETED:
                if await balance_repo.confirm_reservation(payment.merchant_id, payment.amount):
                    await payment_repo.update_status(
                        payment.id,
                        PaymentStatus.COMPLETED,
                        provider_status=provider_status,
                        provider_payment_id=payment.provider_payment_id or provider_payment_id,
                    )
                    await uow.commit()
                    return True
                return False

            if new_status == ProviderStatus.CANCELED:
                if await balance_repo.release_reservation(payment.merchant_id, payment.amount):
                    await payment_repo.update_status(
                        payment.id,
                        PaymentStatus.CANCELED,
                        provider_status=provider_status,
                        provider_payment_id=payment.provider_payment_id or provider_payment_id,
                    )
                    await uow.commit()
                    return True
                return False

            return False

    async def verify_merchant(self, merchant_id: UUID) -> bool:
        async with self.uow as uow:
            merchant = await uow.merchants.get_active_by_id(merchant_id)
            return merchant is not None

    async def get_merchant_data(self, merchant_id: UUID) -> dict[str, Any] | None:
        async with self.uow as uow:
            merchant = await uow.merchants.get_by_id_with_balance(merchant_id)
            if merchant is None:
                return None

            balance = merchant.balance
            return {
                "id": str(merchant.id),
                "name": merchant.name,
                "balance": balance.amount if balance else 0,
                "reserved_amount": balance.reserved_amount if balance else 0,
                "available_amount": balance.available_amount if balance else 0,
            }
