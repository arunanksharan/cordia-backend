from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    APP_NAME: str = "prm"
    ENV: Literal["local", "dev", "prod"] = "local"
    API_PREFIX: str = "/api/v1"

    # DB
    POSTGRES_DSN: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prm"

    # Auth (for demo HS256) — in prod, use OIDC/JWKS
    JWT_ALG: str = "HS256"
    JWT_SECRET: str = "dev-secret-change-me"
    REQUIRED_AUDIENCE: str | None = None

    # Multitenancy default org (for local dev)
    DEFAULT_ORG_ID: str = "00000000-0000-0000-0000-000000000001"

    # Object storage provider
    OBJECT_STORAGE_PROVIDER: Literal["local", "s3"] = "local"

    # Local storage
    LOCAL_STORAGE_ROOT: str = "./media"

    # S3/MinIO
    S3_ENDPOINT_URL: str | None = None  # e.g. http://127.0.0.1:9000 for MinIO
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = "prm-media"
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None

    EVENT_BUS_PROVIDER: str = "noop"  # noop | redis
    REDIS_URL: str | None = None
    REDIS_STREAM: str | None = None  # default "prm.events" if None
    REDIS_STREAM_MAXLEN: int = 10000
    
    EMBEDDINGS_PROVIDER: str = "hashing"  # hashing | openai | <add yours>
    EMBEDDINGS_DIM: int = 384

    @field_validator("POSTGRES_DSN")
    @classmethod
    def _must_asyncpg(cls, v: str):
        if "+asyncpg" not in v:
            raise ValueError("POSTGRES_DSN must use asyncpg driver (postgresql+asyncpg://...)")
        return v

settings = Settings()