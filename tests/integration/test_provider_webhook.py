import json

from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.main import app
from app.services.webhook_service import WebhookService


class DummyUoW:
    pass


async def override_get_uow() -> DummyUoW:
    return DummyUoW()


def _make_webhook_body(status: str = "Completed") -> bytes:
    payload = {
        "id": "provider-1",
        "external_invoice_id": "external-1001",
        "status": status,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def test_provider_webhook_accepts_valid_payload(monkeypatch) -> None:
    async def fake_handle(
        self,
        external_invoice_id: str,
        provider_payment_id: str,
        provider_status: str,
    ) -> bool:
        _ = (external_invoice_id, provider_payment_id, provider_status)
        return True

    monkeypatch.setattr(WebhookService, "handle_provider_webhook", fake_handle)
    app.dependency_overrides[get_uow] = override_get_uow

    body = _make_webhook_body("Completed")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/webhooks/provider",
            data=body,
            headers={"Content-Type": "application/json"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_provider_webhook_rejects_invalid_payload() -> None:
    app.dependency_overrides[get_uow] = override_get_uow
    body = b'{"id":"provider-1","external_invoice_id":"external-1001"}'

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/webhooks/provider",
            data=body,
            headers={"Content-Type": "application/json"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid webhook payload"
