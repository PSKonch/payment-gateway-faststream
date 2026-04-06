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
    def body_sha256_hex(body: bytes) -> str:
        return hashlib.sha256(body).hexdigest()

    @staticmethod
    def build_canonical_request(method: str, path: str, body: bytes) -> str:
        normalized_method = method.upper()
        normalized_path = path or "/"
        body_sha = SignatureService.body_sha256_hex(body)
        return f"{normalized_method}\\n{normalized_path}\\n{body_sha}"

    @staticmethod
    def sign_canonical_request(canonical_request: str, secret: str) -> str:
        return hmac.new(
            secret.encode(),
            canonical_request.encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def sign_request(method: str, path: str, body: bytes, secret: str) -> str:
        canonical_request = SignatureService.build_canonical_request(method, path, body)
        return SignatureService.sign_canonical_request(canonical_request, secret)

    @staticmethod
    def verify_signature(
        method: str,
        path: str,
        body: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        expected = SignatureService.sign_request(method, path, body, secret)
        return hmac.compare_digest(expected, signature)
