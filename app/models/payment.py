from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from .merchant import MerchantModel  # noqa: F401


class PaymentModel(Base):
    __table_args__ = (
        Index("ix_payments_merchant_id", "merchant_id"),
        Index("ix_payments_status", "status"),
        Index("ix_payments_external_invoice_id", "external_invoice_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(
        ForeignKey("merchant_model.id", ondelete="RESTRICT"), nullable=False
    )
    merchant_order_id: Mapped[str] = mapped_column(nullable=False)
    external_invoice_id: Mapped[str] = mapped_column(unique=True, nullable=False)
    provider_payment_id: Mapped[str] = mapped_column(unique=True, nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    provider_status: Mapped[str] = mapped_column(nullable=True)
    failure_reason: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    processed_at: Mapped[datetime] = mapped_column(nullable=True)

    merchant = relationship("MerchantModel", back_populates="payments")
