import hashlib
import hmac
import secrets
from base64 import b64encode
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import settings


class SignatureService:
    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        prefix = secrets.token_hex(settings.API_KEY_PREFIX_LENGTH // 2)
        secret = secrets.token_urlsafe(32)
        return prefix, secret

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def encrypt_secret(secret: str) -> Any:
        fernet = Fernet(
            b64encode(hashlib.pbkdf2_hmac("sha256", settings.ENCRYPTION_KEY.encode(), b"", 1, 32))
        )
        return fernet.encrypt(secret.encode()).decode()

    @staticmethod
    def decrypt_secret(encrypted: str) -> Any:
        fernet = Fernet(
            b64encode(hashlib.pbkdf2_hmac("sha256", settings.ENCRYPTION_KEY.encode(), b"", 1, 32))
        )
        return fernet.decrypt(encrypted.encode()).decode()

    @staticmethod
    def sign_request(data: bytes, secret: str) -> str:
        signature = hmac.new(
            secret.encode(),
            data,
            hashlib.sha256,
        ).hexdigest()
        return signature

    @staticmethod
    def verify_signature(data: bytes, signature: str, secret: str) -> bool:
        expected = SignatureService.sign_request(data, secret)
        return hmac.compare_digest(expected, signature)
