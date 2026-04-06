from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models import MerchantCredentialModel, MerchantModel
from app.repositories.base import BaseRepository


class MerchantRepository(BaseRepository[MerchantModel]):
    model = MerchantModel

    async def get_by_id_with_balance(self, merchant_id: UUID) -> MerchantModel | None:
        stmt = (
            select(MerchantModel)
            .options(joinedload(MerchantModel.balance))
            .where(MerchantModel.id == merchant_id)
            .where(MerchantModel.is_active.is_(True))
            .where(MerchantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_active_by_id(self, merchant_id: UUID) -> MerchantModel | None:
        stmt = (
            select(MerchantModel)
            .where(MerchantModel.id == merchant_id)
            .where(MerchantModel.is_active.is_(True))
            .where(MerchantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> MerchantModel | None:
        stmt = select(MerchantModel).where(MerchantModel.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class MerchantCredentialRepository(BaseRepository[MerchantCredentialModel]):
    model = MerchantCredentialModel

    async def get_by_api_key_prefix(self, prefix: str) -> MerchantCredentialModel | None:
        stmt = (
            select(MerchantCredentialModel)
            .options(joinedload(MerchantCredentialModel.merchant))
            .where(MerchantCredentialModel.api_key_prefix == prefix)
            .where(MerchantCredentialModel.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_active_by_merchant_id(self, merchant_id: UUID) -> list[MerchantCredentialModel]:
        stmt = (
            select(MerchantCredentialModel)
            .where(MerchantCredentialModel.merchant_id == merchant_id)
            .where(MerchantCredentialModel.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_last_used(self, credential_id: UUID) -> None:
        await self.update_by_id(credential_id, last_used_at=func.now())
