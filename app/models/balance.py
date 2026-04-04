from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.core.db import Base

if TYPE_CHECKING:
    from .merchant import MerchantModel  # noqa: F401

class BalanceModel(Base):
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchant_model.id", ondelete="CASCADE"), primary_key=True)
    total_amount: Mapped[float] = mapped_column(nullable=False)
    reserved_amount: Mapped[float] = mapped_column(default=0, nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    merchant = relationship("MerchantModel", back_populates="balance")