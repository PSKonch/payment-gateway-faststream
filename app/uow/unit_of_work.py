from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories import (
    BalanceRepository,
    MerchantCredentialRepository,
    MerchantRepository,
    OutboxRepository,
    PaymentRepository,
)


class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.merchants = MerchantRepository(self._session)
        self.merchant_credentials = MerchantCredentialRepository(self._session)
        self.balances = BalanceRepository(self._session)
        self.payments = PaymentRepository(self._session)
        self.outbox = OutboxRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    @property
    def session(self) -> AsyncSession:
        return self._session
