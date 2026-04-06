from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_merchant_id, get_uow
from app.core.enums import PaymentStatus
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

    async def get_by_merchant_id_for_update(self, merchant_id: UUID) -> FakeBalance | None:
        return self.balance if merchant_id == self.balance.merchant_id else None

    async def reserve_amount(self, merchant_id: UUID, amount: int) -> bool:
        if merchant_id != self.balance.merchant_id:
            return False
        if self.balance.available_amount < amount:
            return False
        self.balance.reserved_amount += amount
        return True


class FakePaymentRepository:
    def __init__(self) -> None:
        self._orders: set[tuple[UUID, str]] = set()
        self.items: list[FakePayment] = []

    async def exists_by_merchant_order_id(self, merchant_id: UUID, merchant_order_id: str) -> bool:
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
        self._orders.add((merchant_id, merchant_order_id))
        payment = FakePayment(
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
        self.items.append(payment)
        return payment


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, object]]] = []

    async def create_message(self, topic: str, payload: dict[str, object]) -> None:
        self.messages.append((topic, payload))


class FakeUoW:
    def __init__(self, merchant_id: UUID, initial_amount: int) -> None:
        self.merchant_id = merchant_id
        self.balances = FakeBalanceRepository(
            FakeBalance(merchant_id=merchant_id, amount=initial_amount)
        )
        self.payments = FakePaymentRepository()
        self.outbox = FakeOutboxRepository()
        self.commit_calls = 0

    async def __aenter__(self) -> "FakeUoW":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        _ = (exc_type, exc, tb)

    async def commit(self) -> None:
        self.commit_calls += 1


def test_create_payment_endpoint_returns_201_and_creates_outbox_event() -> None:
    merchant_id = uuid4()
    fake_uow = FakeUoW(merchant_id=merchant_id, initial_amount=20_000)

    async def override_merchant_id() -> UUID:
        return merchant_id

    async def override_uow() -> FakeUoW:
        return fake_uow

    app.dependency_overrides[get_current_merchant_id] = override_merchant_id
    app.dependency_overrides[get_uow] = override_uow

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/payments",
                json={"merchant_order_id": "ord-201", "amount": 10_000},
                headers={"X-API-Key": "devbypass001"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["status"] == PaymentStatus.CREATED
    assert fake_uow.balances.balance.reserved_amount == 10_000
    assert fake_uow.commit_calls == 1
    assert len(fake_uow.outbox.messages) == 1
    assert fake_uow.outbox.messages[0][0] == "payment.created"


def test_create_payment_endpoint_returns_400_on_insufficient_balance() -> None:
    merchant_id = uuid4()
    fake_uow = FakeUoW(merchant_id=merchant_id, initial_amount=1_000)

    async def override_merchant_id() -> UUID:
        return merchant_id

    async def override_uow() -> FakeUoW:
        return fake_uow

    app.dependency_overrides[get_current_merchant_id] = override_merchant_id
    app.dependency_overrides[get_uow] = override_uow

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/payments",
                json={"merchant_order_id": "ord-400", "amount": 10_000},
                headers={"X-API-Key": "devbypass001"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "insufficient balance" in response.json()["detail"]
    assert fake_uow.balances.balance.reserved_amount == 0
    assert fake_uow.commit_calls == 0
    assert fake_uow.outbox.messages == []
