import os
import sys
from urllib.parse import urlsplit

from pydantic import ValidationError
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BCRYPT_ROUNDS: int = 12

    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@rescue1122.gov.pk"

    APP_NAME: str = "Rescue 1122 Evaluation System"
    # Supports comma-separated origins.
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_HOSTS: str = "rescue1122-api.onrender.com,*.onrender.com,localhost,127.0.0.1"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


def _presence(name: str) -> str:
    return "set" if os.getenv(name) else "missing"


def _database_summary() -> str:
    value = os.getenv("DATABASE_URL", "")
    if not value:
        return "missing"
    try:
        parts = urlsplit(value)
        return f"{parts.scheme}://{parts.hostname or 'unknown-host'}{parts.path or ''}"
    except Exception:
        return "set but unreadable"


def _load_settings() -> Settings:
    try:
        loaded = Settings()
        print(
            "Settings loaded: "
            f"ENVIRONMENT={loaded.ENVIRONMENT}, "
            f"DATABASE_URL={_database_summary()}, "
            f"SECRET_KEY={_presence('SECRET_KEY')}, "
            f"FRONTEND_URL={_presence('FRONTEND_URL')}, "
            f"ALLOWED_HOSTS={_presence('ALLOWED_HOSTS')}",
            flush=True,
        )
        return loaded
    except ValidationError as exc:
        print("Settings validation failed.", file=sys.stderr, flush=True)
        print(
            "Safe env status: "
            f"DATABASE_URL={_database_summary()}, "
            f"SECRET_KEY={_presence('SECRET_KEY')}, "
            f"FRONTEND_URL={_presence('FRONTEND_URL')}, "
            f"ALLOWED_HOSTS={_presence('ALLOWED_HOSTS')}",
            file=sys.stderr,
            flush=True,
        )
        for error in exc.errors():
            loc = ".".join(str(part) for part in error.get("loc", []))
            print(f"Settings error: {loc}: {error.get('msg')}", file=sys.stderr, flush=True)
        raise


settings = _load_settings()
