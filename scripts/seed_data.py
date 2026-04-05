import argparse
import asyncio
from dataclasses import dataclass

from sqlalchemy import select

from app.core.db import async_session
from app.models import BalanceModel, MerchantCredentialModel, MerchantModel
from app.services import SignatureService


@dataclass(frozen=True)
class MerchantSeed:
    name: str
    balance: int
    api_key_prefix: str
    api_secret: str


MERCHANTS: tuple[MerchantSeed, ...] = (
    MerchantSeed(
        name="Test Merchant 1",
        balance=100000,
        api_key_prefix="testm001",
        api_secret="test-secret-merchant-1",
    ),
    MerchantSeed(
        name="Test Merchant 2",
        balance=50000,
        api_key_prefix="testm002",
        api_secret="test-secret-merchant-2",
    ),
)


async def seed_merchant(seed: MerchantSeed) -> None:
    async with async_session() as session:
        result = await session.execute(select(MerchantModel).where(MerchantModel.name == seed.name))
        merchant = result.scalar_one_or_none()

        if merchant is None:
            merchant = MerchantModel(name=seed.name, is_active=True)
            session.add(merchant)
            await session.flush()

            session.add(
                BalanceModel(
                    merchant_id=merchant.id,
                    amount=seed.balance,
                    reserved_amount=0,
                )
            )

        credential_result = await session.execute(
            select(MerchantCredentialModel).where(
                MerchantCredentialModel.api_key_prefix == seed.api_key_prefix
            )
        )
        existing_credential = credential_result.scalar_one_or_none()

        if existing_credential is None:
            api_key = f"{seed.api_key_prefix}:{seed.api_secret}"
            api_key_hash = SignatureService.hash_api_key(api_key)
            secret_encrypted = SignatureService.encrypt_secret(seed.api_secret)

            session.add(
                MerchantCredentialModel(
                    merchant_id=merchant.id,
                    api_key_prefix=seed.api_key_prefix,
                    api_key_hash=api_key_hash,
                    secret_key_encrypted=secret_encrypted,
                    is_active=True,
                )
            )
            await session.commit()

            signature_for_get = SignatureService.sign_request(b"", seed.api_secret)

            print("Merchant credentials created")
            print(f"merchant_name: {seed.name}")
            print(f"x-api-key: {api_key}")
            print(f"x-signature (for GET with empty body): {signature_for_get}")
            print(f"secret (for signing request body): {seed.api_secret}")
        else:
            await session.commit()
            print(f"Merchant already seeded: {seed.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed merchant data and print auth headers")
    return parser.parse_args()


def main() -> None:
    _ = parse_args()

    async def run() -> None:
        for seed in MERCHANTS:
            await seed_merchant(seed)

    asyncio.run(run())


if __name__ == "__main__":
    main()
