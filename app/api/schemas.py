from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreateRequest(BaseModel):
    merchant_order_id: str = Field(..., min_length=1, max_length=100)
    amount: int = Field(..., gt=0, description="Amount in kopeks/cents")


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    next_cursor: datetime | None = None


class MerchantProfileResponse(BaseModel):
    id: str
    name: str
    balance: int
    reserved_amount: int
    available_amount: int


class WebhookPaymentRequest(BaseModel):
    id: str
    external_invoice_id: str
    status: str


class ErrorResponse(BaseModel):
    detail: str
