from app.services import SignatureService


def test_signature_depends_on_method_path_and_body() -> None:
    secret = "test-secret-merchant-1"
    body = b'{"merchant_order_id":"order-1001","amount":10000}'

    post_signature = SignatureService.sign_request(
        method="POST",
        path="/api/v1/payments",
        body=body,
        secret=secret,
    )
    get_signature = SignatureService.sign_request(
        method="GET",
        path="/api/v1/payments",
        body=body,
        secret=secret,
    )

    assert post_signature != get_signature


def test_signature_uses_raw_body_bytes_without_normalization() -> None:
    secret = "test-secret-merchant-1"
    compact_body = b'{"amount":10000,"merchant_order_id":"order-1001"}'
    spaced_body = b'{"amount":10000, "merchant_order_id":"order-1001"}'

    compact_signature = SignatureService.sign_request(
        method="POST",
        path="/api/v1/payments",
        body=compact_body,
        secret=secret,
    )
    spaced_signature = SignatureService.sign_request(
        method="POST",
        path="/api/v1/payments",
        body=spaced_body,
        secret=secret,
    )

    assert compact_signature != spaced_signature


def test_verify_signature_matches_expected_value() -> None:
    secret = "test-secret-merchant-1"
    method = "GET"
    path = "/api/v1/me"
    body = b""

    signature = SignatureService.sign_request(
        method=method,
        path=path,
        body=body,
        secret=secret,
    )

    assert SignatureService.verify_signature(
        method=method,
        path=path,
        body=body,
        signature=signature,
        secret=secret,
    )


def test_provider_webhook_signature_is_verifiable() -> None:
    secret = "change-me-provider-webhook-secret"
    method = "POST"
    path = "/api/v1/webhooks/provider"
    body = b'{"external_invoice_id":"inv-1","id":"p-1","status":"Completed"}'

    signature = SignatureService.sign_request(
        method=method,
        path=path,
        body=body,
        secret=secret,
    )

    assert SignatureService.verify_signature(
        method=method,
        path=path,
        body=body,
        signature=signature,
        secret=secret,
    )


def test_provider_webhook_signature_rejects_wrong_path() -> None:
    secret = "change-me-provider-webhook-secret"
    body = b'{"external_invoice_id":"inv-1","id":"p-1","status":"Completed"}'

    signature = SignatureService.sign_request(
        method="POST",
        path="/api/v1/webhooks/provider",
        body=body,
        secret=secret,
    )

    assert not SignatureService.verify_signature(
        method="POST",
        path="/api/v1/webhooks/provider/other",
        body=body,
        signature=signature,
        secret=secret,
    )
