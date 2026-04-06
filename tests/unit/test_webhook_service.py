from dataclasses import dataclass
from uuid import uuid4

from app.core.enums import PaymentStatus
from app.services.webhook_service import WebhookService


@dataclass
class FakePayment:
    id: object
    merchant_id: object
    amount: int
    status: str
    provider_payment_id: str | None = None


class FakePaymentRepository:
    def __init__(self, payment: FakePayment | None) -> None:
        self.payment = payment
        self.updates: list[dict[str, object]] = []

    async def get_by_external_invoice_id_for_update(
        self, external_invoice_id: str
    ) -> FakePayment | None:
        _ = external_invoice_id
        return self.payment

    async def update_status(
        self,
        payment_id: object,
        status: str,
        *,
        provider_status: str | None = None,
        provider_payment_id: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        self.updates.append(
            {
                "payment_id": payment_id,
                "status": status,
                "provider_status": provider_status,
                "provider_payment_id": provider_payment_id,
                "failure_reason": failure_reason,
            }
        )


class FakeBalanceRepository:
    def __init__(
        self,
        *,
        confirm_result: bool = True,
        release_result: bool = True,
    ) -> None:
        self.confirm_result = confirm_result
        self.release_result = release_result
        self.confirm_calls = 0
        self.release_calls = 0

    async def confirm_reservation(self, merchant_id: object, amount: int) -> bool:
        _ = (merchant_id, amount)
        self.confirm_calls += 1
        return self.confirm_result

    async def release_reservation(self, merchant_id: object, amount: int) -> bool:
        _ = (merchant_id, amount)
        self.release_calls += 1
        return self.release_result


class FakeUoW:
    def __init__(
        self, payment_repo: FakePaymentRepository, balance_repo: FakeBalanceRepository
    ) -> None:
        self.payments = payment_repo
        self.balances = balance_repo
        self.commit_calls = 0

    async def __aenter__(self) -> "FakeUoW":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        _ = (exc_type, exc, tb)

    async def commit(self) -> None:
        self.commit_calls += 1


async def test_created_webhook_moves_payment_to_processing() -> None:
    payment = FakePayment(
        id=uuid4(),
        merchant_id=uuid4(),
        amount=10000,
        status=PaymentStatus.CREATED,
    )
    payments = FakePaymentRepository(payment)
    balances = FakeBalanceRepository()
    service = WebhookService(FakeUoW(payments, balances))  # type: ignore[arg-type]

    result = await service.handle_provider_webhook(
        external_invoice_id="inv-1001",
        provider_payment_id="provider-1",
        provider_status="Created",
    )

    assert result is True
    assert len(payments.updates) == 1
    assert payments.updates[0]["status"] == PaymentStatus.PROCESSING
    assert payments.updates[0]["provider_status"] == "Created"
    assert payments.updates[0]["provider_payment_id"] == "provider-1"
    assert balances.confirm_calls == 0
    assert balances.release_calls == 0


async def test_completed_webhook_confirms_reservation_and_completes_payment() -> None:
    payment = FakePayment(
        id=uuid4(),
        merchant_id=uuid4(),
        amount=10000,
        status=PaymentStatus.PROCESSING,
        provider_payment_id="provider-existing",
    )
    payments = FakePaymentRepository(payment)
    balances = FakeBalanceRepository(confirm_result=True)
    service = WebhookService(FakeUoW(payments, balances))  # type: ignore[arg-type]

    result = await service.handle_provider_webhook(
        external_invoice_id="inv-1002",
        provider_payment_id="provider-existing",
        provider_status="Completed",
    )

    assert result is True
    assert len(payments.updates) == 1
    assert payments.updates[0]["status"] == PaymentStatus.COMPLETED
    assert balances.confirm_calls == 1
    assert balances.release_calls == 0


async def test_canceled_webhook_releases_reservation_and_cancels_payment() -> None:
    payment = FakePayment(
        id=uuid4(),
        merchant_id=uuid4(),
        amount=10000,
        status=PaymentStatus.PROCESSING,
        provider_payment_id="provider-3",
    )
    payments = FakePaymentRepository(payment)
    balances = FakeBalanceRepository(release_result=True)
    service = WebhookService(FakeUoW(payments, balances))  # type: ignore[arg-type]

    result = await service.handle_provider_webhook(
        external_invoice_id="inv-1003",
        provider_payment_id="provider-3",
        provider_status="Canceled",
    )

    assert result is True
    assert len(payments.updates) == 1
    assert payments.updates[0]["status"] == PaymentStatus.CANCELED
    assert balances.confirm_calls == 0
    assert balances.release_calls == 1
