import importlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.broker.outbox_publisher import OutboxPublisher
from app.core.enums import OutboxStatus

outbox_publisher_module = importlib.import_module("app.broker.outbox_publisher")


@dataclass
class FakeOutboxMessage:
    id: UUID
    topic: str
    payload: dict[str, Any]
    status: str = OutboxStatus.PENDING
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None
    error_message: str | None = None


class FakeOutboxRepository:
    def __init__(self, messages: list[FakeOutboxMessage]) -> None:
        self.messages = messages

    async def get_pending_messages(self, limit: int = 100) -> list[FakeOutboxMessage]:
        return [m for m in self.messages if m.status == OutboxStatus.PENDING][:limit]

    async def mark_as_processing(self, message_id: UUID) -> FakeOutboxMessage | None:
        for message in self.messages:
            if message.id == message_id:
                message.status = OutboxStatus.PROCESSING
                return message
        return None

    async def mark_as_sent(self, message_id: UUID) -> FakeOutboxMessage | None:
        for message in self.messages:
            if message.id == message_id:
                message.status = OutboxStatus.SENT
                message.processed_at = datetime.now(UTC)
                return message
        return None

    async def mark_as_failed(
        self, message_id: UUID, error_message: str | None = None
    ) -> FakeOutboxMessage | None:
        for message in self.messages:
            if message.id == message_id:
                message.status = OutboxStatus.FAILED
                message.retry_count += 1
                message.error_message = error_message
                message.processed_at = datetime.now(UTC)
                return message
        return None


class FakeUoW:
    def __init__(self, messages: list[FakeOutboxMessage]) -> None:
        self.outbox = FakeOutboxRepository(messages)
        self.commit_calls = 0

    async def __aenter__(self) -> "FakeUoW":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        _ = (exc_type, exc, tb)

    async def commit(self) -> None:
        self.commit_calls += 1


async def test_outbox_publisher_marks_message_as_sent(monkeypatch) -> None:
    message = FakeOutboxMessage(
        id=uuid4(),
        topic="payment.created",
        payload={"payment_id": "p-1"},
    )
    fake_uow = FakeUoW([message])
    published: list[tuple[str, dict[str, Any]]] = []

    async def fake_publish(topic: str, payload: dict[str, Any]) -> None:
        published.append((topic, payload))

    monkeypatch.setattr(outbox_publisher_module, "UnitOfWork", lambda _session_factory: fake_uow)
    monkeypatch.setattr(outbox_publisher_module.producer, "publish", fake_publish)

    publisher = OutboxPublisher()
    await publisher._process_pending_messages()

    assert message.status == OutboxStatus.SENT
    assert fake_uow.commit_calls == 2
    assert published == [("payment.created", {"payment_id": "p-1"})]


async def test_outbox_publisher_marks_message_as_failed_on_publish_error(monkeypatch) -> None:
    message = FakeOutboxMessage(
        id=uuid4(),
        topic="payment.created",
        payload={"payment_id": "p-2"},
    )
    fake_uow = FakeUoW([message])

    async def fake_publish(topic: str, payload: dict[str, Any]) -> None:
        _ = (topic, payload)
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(outbox_publisher_module, "UnitOfWork", lambda _session_factory: fake_uow)
    monkeypatch.setattr(outbox_publisher_module.producer, "publish", fake_publish)

    publisher = OutboxPublisher()
    await publisher._process_pending_messages()

    assert message.status == OutboxStatus.FAILED
    assert message.retry_count == 1
    assert message.error_message == "broker unavailable"
    assert fake_uow.commit_calls == 2
