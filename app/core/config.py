from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Payment API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "A simple payment API built with FastAPI and SQLAlchemy with RabbitMQ for message queuing"
    APP_HOST: str = "localhost"
    APP_PORT: int = 8000
    APP_WORKERS: int = 4

    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "payment_db"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "password"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
    
    BROKER_HOST: str = "localhost"
    BROKER_PORT: int = 5672
    BROKER_USER: str = "guest"
    BROKER_PASSWORD: str = "guest"

    @property
    def BROKER_URL(self) -> str:
        return f"amqp://{self.BROKER_USER}:{self.BROKER_PASSWORD}@{self.BROKER_HOST}:{self.BROKER_PORT}/"
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()