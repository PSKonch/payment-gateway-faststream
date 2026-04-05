from fastapi import FastAPI, HTTPException, status

from provider.schemas import ProviderCreatePaymentRequest, ProviderPaymentResponse
from provider.service import ProviderService

app = FastAPI(
    title="Mock Payment Provider",
    version="0.1.0",
    description="Minimal provider emulator for payment gateway integration",
)

provider_service = ProviderService()


@app.post(
    "/api/v1/payments",
    response_model=ProviderPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)  # type: ignore[misc]
async def create_payment(payload: ProviderCreatePaymentRequest) -> ProviderPaymentResponse:
    try:
        return provider_service.create_payment(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/health")  # type: ignore[misc]
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
