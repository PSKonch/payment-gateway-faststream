from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Payment API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Payment gateway with provider integration"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_WORKERS: int = 4
    DEBUG: bool = False

    DATABASE_HOST: str = "127.0.0.1"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "payment_db"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "password"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    BROKER_HOST: str = "localhost"
    BROKER_PORT: int = 5672
    BROKER_USER: str = "guest"
    BROKER_PASSWORD: str = "guest"

    @property
    def BROKER_URL(self) -> str:
        return f"amqp://{self.BROKER_USER}:{self.BROKER_PASSWORD}@{self.BROKER_HOST}:{self.BROKER_PORT}/"

    PROVIDER_URL: str = "http://provider:8001"
    WEBHOOK_BASE_URL: str = "http://app:8000"
    PROVIDER_WEBHOOK_SECRET: str = "change-me-provider-webhook-secret"

    PROVIDER_DELAY_MIN: float = 1.0
    PROVIDER_DELAY_MAX: float = 2.0

    ENCRYPTION_KEY: str = "change-me-in-production-32-chars!"
    API_KEY_PREFIX_LENGTH: int = 8
    CACHE_TTL_SECONDS: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
