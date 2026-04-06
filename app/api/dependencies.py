import hmac
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config import settings
from app.core.db import async_session
from app.services import SignatureService
from app.uow import UnitOfWork


async def get_uow() -> UnitOfWork:
    return UnitOfWork(async_session)


def _is_dev_bypass_key_id(key_id: str) -> bool:
    if not settings.AUTH_DEV_BYPASS_ENABLED:
        return False

    allowed = {
        value.strip() for value in settings.AUTH_DEV_BYPASS_KEY_IDS.split(",") if value.strip()
    }
    return key_id in allowed


def _parse_api_key(x_api_key: str) -> tuple[str, str | None]:
    value = x_api_key.strip()
    key_id, separator, provided_secret = value.partition(":")

    if separator == ":" and key_id and provided_secret:
        return key_id, provided_secret

    if _is_dev_bypass_key_id(value):
        return value, None

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key format",
    )


async def get_current_merchant_id(
    request: Request,
    x_api_key: Annotated[
        str,
        Header(
            description="API ключ мерчанта в формате '<key_id>:<secret>'. "
            "Для dev-bypass key_id допускается формат '<key_id>'",
            example="testm001:test-secret-merchant-1",
            alias="X-API-Key",
        ),
    ],
    x_signature: Annotated[
        str | None,
        Header(
            description="HMAC-SHA256 подпись запроса. "
            "Вычисляется как: HMAC-SHA256(METHOD\\nPATH\\nBODY_SHA256_HEX, secret). "
            "PATH должен быть без query string. "
            "Для разрешенных dev-bypass key_id подпись может не передаваться. "
            "Используйте скрипт: python scripts/sign_request.py",
            example="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
            alias="X-Signature",
        ),
    ] = None,
    uow: UnitOfWork = Depends(get_uow),
) -> UUID:
    key_id, provided_secret = _parse_api_key(x_api_key)

    async with uow as u:
        credential = await u.merchant_credentials.get_by_api_key_prefix(key_id)

        if not credential:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        if not credential.merchant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Merchant is not active",
            )

        try:
            stored_secret = SignatureService.decrypt_secret(credential.secret_key_encrypted)
            if provided_secret is not None and not hmac.compare_digest(
                stored_secret, provided_secret
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                )

            if _is_dev_bypass_key_id(key_id):
                await u.merchant_credentials.update_last_used(credential.id)
                await u.commit()
                return credential.merchant_id

            body = await request.body()
            method = request.method
            path = request.url.path

            if not x_signature:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing signature",
                )

            if not SignatureService.verify_signature(
                method=method,
                path=path,
                body=body,
                signature=x_signature,
                secret=stored_secret,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature verification failed",
            ) from e

        await u.merchant_credentials.update_last_used(credential.id)
        await u.commit()

        return credential.merchant_id
