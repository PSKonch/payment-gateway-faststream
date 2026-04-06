import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.api.dependencies import get_current_merchant_id, get_uow
from app.main import app


@dataclass
class FakeBalance:
    merchant_id: UUID
    amount: int
    reserved_amount: int = 0

    @property
    def available_amount(self) -> int:
        return self.amount - self.reserved_amount


@dataclass
class FakePayment:
    id: UUID
    merchant_id: UUID
    merchant_order_id: str
    external_invoice_id: str
    provider_payment_id: str | None
    amount: int
    status: str
    provider_status: str | None
    failure_reason: str | None
    created_at: datetime


class FakeBalanceRepository:
    def __init__(self, balance: FakeBalance) -> None:
        self.balance = balance
        self._lock = asyncio.Lock()

    async def get_by_merchant_id_for_update(self, merchant_id: UUID) -> FakeBalance | None:
        return self.balance if merchant_id == self.balance.merchant_id else None

    async def reserve_amount(self, merchant_id: UUID, amount: int) -> bool:
        if merchant_id != self.balance.merchant_id:
            return False

        async with self._lock:
            if self.balance.available_amount < amount:
                return False
            self.balance.reserved_amount += amount
            return True


class FakePaymentRepository:
    def __init__(self) -> None:
        self._orders: set[tuple[UUID, str]] = set()
        self._lock = asyncio.Lock()

    async def exists_by_merchant_order_id(self, merchant_id: UUID, merchant_order_id: str) -> bool:
        async with self._lock:
            return (merchant_id, merchant_order_id) in self._orders

    async def create(
        self,
        *,
        merchant_id: UUID,
        merchant_order_id: str,
        external_invoice_id: str,
        amount: int,
        status: str,
    ) -> FakePayment:
        async with self._lock:
            self._orders.add((merchant_id, merchant_order_id))

        return FakePayment(
            id=uuid4(),
            merchant_id=merchant_id,
            merchant_order_id=merchant_order_id,
            external_invoice_id=external_invoice_id,
            provider_payment_id=None,
            amount=amount,
            status=status,
            provider_status=None,
            failure_reason=None,
            created_at=datetime.now(UTC),
        )


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, object]]] = []

    async def create_message(self, topic: str, payload: dict[str, object]) -> None:
        self.messages.append((topic, payload))


class FakeUoW:
    def __init__(self, merchant_id: UUID, initial_amount: int) -> None:
        self.balances = FakeBalanceRepository(
            FakeBalance(merchant_id=merchant_id, amount=initial_amount)
        )
        self.payments = FakePaymentRepository()
        self.outbox = FakeOutboxRepository()

    async def __aenter__(self) -> "FakeUoW":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        _ = (exc_type, exc, tb)

    async def commit(self) -> None:
        return None


async def test_concurrent_payment_requests_do_not_exceed_available_balance() -> None:
    merchant_id = uuid4()
    fake_uow = FakeUoW(merchant_id=merchant_id, initial_amount=5_000)

    async def override_merchant_id() -> UUID:
        return merchant_id

    async def override_uow() -> FakeUoW:
        return fake_uow

    app.dependency_overrides[get_current_merchant_id] = override_merchant_id
    app.dependency_overrides[get_uow] = override_uow

    async def create_payment(client: httpx.AsyncClient, idx: int) -> int:
        response = await client.post(
            "/api/v1/payments",
            json={"merchant_order_id": f"burst-{idx}", "amount": 1_000},
            headers={"X-API-Key": "devbypass001"},
        )
        return int(response.status_code)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            statuses = await asyncio.gather(*[create_payment(client, i) for i in range(10)])
    finally:
        app.dependency_overrides.clear()

    assert statuses.count(201) == 5
    assert statuses.count(400) == 5
    assert fake_uow.balances.balance.reserved_amount == 5_000
    assert len(fake_uow.outbox.messages) == 5
