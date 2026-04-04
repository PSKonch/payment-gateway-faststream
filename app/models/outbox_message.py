from uuid import uuid4

from sqlalchemy import UUID, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

class OutboxMessageModel(Base):
    __table_args__ = (
        Index('ix_outbox_messages_status_created_at', 'status', 'created_at'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, unique=True, nullable=False)
    topic: Mapped[str] = mapped_column(nullable=False)
    payload: Mapped[dict] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    processed_at: Mapped[str] = mapped_column(nullable=True)
    error_message: Mapped[str] = mapped_column(nullable=True)
