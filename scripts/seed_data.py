import argparse
import asyncio

from sqlalchemy import select

from app.core.db import async_session
from app.models import BalanceModel, MerchantCredentialModel, MerchantModel
from app.services import SignatureService


async def seed_merchant(merchant_name: str, balance_amount: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(MerchantModel).where(MerchantModel.name == merchant_name)
        )
        merchant = result.scalar_one_or_none()

        if merchant is None:
            merchant = MerchantModel(name=merchant_name, is_active=True)
            session.add(merchant)
            await session.flush()

            session.add(
                BalanceModel(
                    merchant_id=merchant.id,
                    amount=balance_amount,
                    reserved_amount=0,
                )
            )

        prefix, full_api_key = SignatureService.generate_api_key()
        api_key = f"{prefix}:{full_api_key}"
        api_key_hash = SignatureService.hash_api_key(api_key)
        secret_encrypted = SignatureService.encrypt_secret(full_api_key)

        session.add(
            MerchantCredentialModel(
                merchant_id=merchant.id,
                api_key_prefix=prefix,
                api_key_hash=api_key_hash,
                secret_key_encrypted=secret_encrypted,
                is_active=True,
            )
        )
        await session.commit()

    signature_for_get = SignatureService.sign_request(b"", full_api_key)

    print("Merchant credentials created")
    print(f"merchant_name: {merchant_name}")
    print(f"x-api-key: {api_key}")
    print(f"x-signature (for GET with empty body): {signature_for_get}")
    print(f"secret (for signing request body): {full_api_key}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed merchant data and print auth headers")
    parser.add_argument("--merchant-name", default="demo-merchant", help="Merchant name to create")
    parser.add_argument(
        "--balance",
        type=int,
        default=100000,
        help="Initial merchant balance in minimal currency units",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(seed_merchant(args.merchant_name, args.balance))


if __name__ == "__main__":
    main()
