from pydantic import BaseModel


class PaymentCreatedEvent(BaseModel):
    payment_id: str
    merchant_id: str
    external_invoice_id: str
    amount: int
    status: str


class PaymentStatusChangedEvent(BaseModel):
    payment_id: str
    merchant_id: str
    external_invoice_id: str
    old_status: str
    new_status: str
    provider_status: str | None = None
