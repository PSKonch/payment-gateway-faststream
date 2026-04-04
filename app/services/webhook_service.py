from typing import Any
from uuid import UUID

from app.uow import UnitOfWork


class WebhookService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

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
