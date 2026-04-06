from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: UUID | str) -> ModelT | None:
        return await self._session.get(self.model, entity_id)

    async def get_all(
        self,
        *,
        cursor: UUID | None = None,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        stmt = select(self.model).order_by(
            self.model.id  # type: ignore[attr-defined]
        )

        if cursor is not None:
            stmt = stmt.where(
                self.model.id > cursor  # type: ignore[attr-defined]
            )

        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def update_by_id(self, entity_id: UUID | str, **kwargs: Any) -> ModelT | None:
        stmt = (
            update(self.model)
            .where(self.model.id == entity_id)  # type: ignore[attr-defined]
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_id(self, entity_id: UUID | str) -> bool:
        stmt = delete(self.model).where(
            self.model.id == entity_id  # type: ignore[attr-defined]
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0  # type: ignore[attr-defined, no-any-return]

    async def exists(self, entity_id: UUID | str) -> bool:
        stmt = select(self.model.id).where(  # type: ignore[attr-defined]
            self.model.id == entity_id  # type: ignore[attr-defined]
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
