from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, UUID, Index
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.core.db import Base

if TYPE_CHECKING:
    from .balance import BalanceModel  # noqa: F401
    from .payment import PaymentModel  # noqa: F401
    

class MerchantModel(Base):
    __table_args__ = (
        Index('ix_merchant_is_active', 'is_active'),
        Index('ix_merchant_deleted_at', 'deleted_at'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)
    deleted_at: Mapped[str] = mapped_column(nullable=True)

    balance = relationship("BalanceModel", back_populates="merchant", uselist=False, cascade="all, delete-orphan")
    payments = relationship("PaymentModel", back_populates="merchant", cascade="all, delete-orphan")
    credentials = relationship("MerchantCredentialModel", back_populates="merchant", cascade="all, delete-orphan")


class MerchantCredentialModel(Base):
    __table_args__ = (
        Index('ix_merchant_credential_merchant_id', 'merchant_id'),
        Index('ix_merchant_credential_is_active', 'is_active'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, unique=True, nullable=False)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchant_model.id", ondelete="CASCADE"), nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(unique=True, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(unique=True, nullable=False)
    secret_key_encrypted: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    last_used_at: Mapped[str] = mapped_column(nullable=True)

    merchant = relationship("MerchantModel", back_populates="credentials")