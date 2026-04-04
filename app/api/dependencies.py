from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.db import async_session
from app.services import SignatureService
from app.uow import UnitOfWork


async def get_uow() -> UnitOfWork:
    return UnitOfWork(async_session)


async def get_current_merchant_id(
    request: Request,
    x_api_key: Annotated[str, Header()],
    x_signature: Annotated[str, Header()],
    uow: UnitOfWork = Depends(get_uow),
) -> UUID:
    try:
        api_key_prefix = x_api_key.split(":")[0]
    except (IndexError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        ) from e

    async with uow as u:
        credential = await u.merchant_credentials.get_by_api_key_prefix(api_key_prefix)

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

        body = await request.body()

        try:
            secret = SignatureService.decrypt_secret(credential.secret_key_encrypted)

            if not SignatureService.verify_signature(body, x_signature, secret):
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
