from uuid import UUID

from sqlalchemy import select

from app.models import BalanceModel
from app.repositories.base import BaseRepository


class BalanceRepository(BaseRepository[BalanceModel]):
    model = BalanceModel

    async def get_by_merchant_id(self, merchant_id: UUID) -> BalanceModel | None:
        return await self._session.get(BalanceModel, merchant_id)

    async def get_by_merchant_id_for_update(
        self,
        merchant_id: UUID,
        *,
        nowait: bool = False,
        skip_locked: bool = False,
    ) -> BalanceModel | None:
        stmt = (
            select(BalanceModel)
            .where(BalanceModel.merchant_id == merchant_id)
            .with_for_update(nowait=nowait, skip_locked=skip_locked)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def reserve_amount(
        self,
        merchant_id: UUID,
        amount: int,
        *,
        nowait: bool = False,
    ) -> bool:
        balance = await self.get_by_merchant_id_for_update(merchant_id, nowait=nowait)
        if balance is None:
            return False

        if balance.available_amount < amount:
            return False

        balance.reserved_amount += amount
        return True

    async def confirm_reservation(
        self,
        merchant_id: UUID,
        amount: int,
        *,
        nowait: bool = False,
    ) -> bool:
        balance = await self.get_by_merchant_id_for_update(merchant_id, nowait=nowait)
        if balance is None:
            return False

        if balance.reserved_amount < amount or balance.amount < amount:
            return False

        balance.amount -= amount
        balance.reserved_amount -= amount
        return True

    async def release_reservation(
        self,
        merchant_id: UUID,
        amount: int,
        *,
        nowait: bool = False,
    ) -> bool:
        balance = await self.get_by_merchant_id_for_update(merchant_id, nowait=nowait)
        if balance is None:
            return False

        if balance.reserved_amount < amount:
            return False

        balance.reserved_amount -= amount
        return True

    async def add_amount(
        self,
        merchant_id: UUID,
        amount: int,
        *,
        nowait: bool = False,
    ) -> bool:
        balance = await self.get_by_merchant_id_for_update(merchant_id, nowait=nowait)
        if balance is None:
            return False

        balance.amount += amount
        return True
