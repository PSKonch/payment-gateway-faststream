from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from .merchant import MerchantModel  # noqa: F401


class BalanceModel(Base):
    merchant_id: Mapped[UUID] = mapped_column(
        ForeignKey("merchant_model.id", ondelete="CASCADE"), primary_key=True
    )
    amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    reserved_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    merchant = relationship("MerchantModel", back_populates="balance")

    @property
    def available_amount(self) -> int:
        return self.amount - self.reserved_amount
