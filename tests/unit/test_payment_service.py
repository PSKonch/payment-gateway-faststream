from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.enums import PaymentStatus
from app.services.payment_service import PaymentService


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
        self.reserve_calls = 0

    async def get_by_merchant_id_for_update(self, merchant_id: UUID) -> FakeBalance | None:
        return self.balance if merchant_id == self.balance.merchant_id else None

    async def reserve_amount(self, merchant_id: UUID, amount: int) -> bool:
        self.reserve_calls += 1

        if merchant_id != self.balance.merchant_id:
            return False
        if self.balance.available_amount < amount:
            return False

        self.balance.reserved_amount += amount
        return True


class FakePaymentRepository:
    def __init__(self) -> None:
        self.orders: set[tuple[UUID, str]] = set()
        self.items: list[FakePayment] = []

    async def exists_by_merchant_order_id(self, merchant_id: UUID, merchant_order_id: str) -> bool:
        return (merchant_id, merchant_order_id) in self.orders

    async def create(
        self,
        *,
        merchant_id: UUID,
        merchant_order_id: str,
        external_invoice_id: str,
        amount: int,
        status: str,
    ) -> FakePayment:
        self.orders.add((merchant_id, merchant_order_id))
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

    async def get_by_merchant_id(self, merchant_id: UUID, **kwargs) -> list[FakePayment]:  # type: ignore[no-untyped-def]
        _ = kwargs
        return [p for p in self.items if p.merchant_id == merchant_id]


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, object]]] = []

    async def create_message(self, topic: str, payload: dict[str, object]) -> None:
        self.messages.append((topic, payload))


class FakeUoW:
    def __init__(self, merchant_id: UUID, initial_amount: int) -> None:
        self.payments = FakePaymentRepository()
        self.balances = FakeBalanceRepository(
            FakeBalance(merchant_id=merchant_id, amount=initial_amount)
        )
        self.outbox = FakeOutboxRepository()
        self.commit_calls = 0

    async def __aenter__(self) -> "FakeUoW":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        _ = (exc_type, exc, tb)

    async def commit(self) -> None:
        self.commit_calls += 1


async def test_create_payment_success_creates_outbox_event_and_reservation() -> None:
    merchant_id = uuid4()
    uow = FakeUoW(merchant_id=merchant_id, initial_amount=20_000)
    service = PaymentService(uow)  # type: ignore[arg-type]

    payment = await service.create_payment(
        merchant_id=merchant_id,
        merchant_order_id="ord-1",
        amount=10_000,
    )

    assert payment is not None
    assert payment.status == PaymentStatus.CREATED
    assert uow.balances.balance.reserved_amount == 10_000
    assert uow.commit_calls == 1
    assert len(uow.outbox.messages) == 1
    assert uow.outbox.messages[0][0] == "payment.created"


async def test_create_payment_returns_none_for_duplicate_order() -> None:
    merchant_id = uuid4()
    uow = FakeUoW(merchant_id=merchant_id, initial_amount=20_000)
    uow.payments.orders.add((merchant_id, "ord-dup"))
    service = PaymentService(uow)  # type: ignore[arg-type]

    payment = await service.create_payment(
        merchant_id=merchant_id,
        merchant_order_id="ord-dup",
        amount=1_000,
    )

    assert payment is None
    assert uow.balances.reserve_calls == 0
    assert uow.commit_calls == 0
    assert uow.outbox.messages == []


async def test_create_payment_returns_none_when_balance_is_insufficient() -> None:
    merchant_id = uuid4()
    uow = FakeUoW(merchant_id=merchant_id, initial_amount=500)
    service = PaymentService(uow)  # type: ignore[arg-type]

    payment = await service.create_payment(
        merchant_id=merchant_id,
        merchant_order_id="ord-low-balance",
        amount=1_000,
    )

    assert payment is None
    assert uow.balances.balance.reserved_amount == 0
    assert uow.commit_calls == 0
    assert uow.outbox.messages == []
