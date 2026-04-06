from pydantic import BaseModel, Field


class ProviderCreatePaymentRequest(BaseModel):
    external_invoice_id: str = Field(..., min_length=1, max_length=200)
    amount: str = Field(..., pattern=r"^\d+\.\d{2}$")
    callback_url: str = Field(..., min_length=1, max_length=1000)


class ProviderPaymentResponse(BaseModel):
    id: str
    external_invoice_id: str
    amount: int
    callback_url: str
    status: str


class ProviderWebhookPayload(BaseModel):
    id: str
    external_invoice_id: str
    status: str
