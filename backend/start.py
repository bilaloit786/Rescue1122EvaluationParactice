import os
import sys
import traceback
from urllib.parse import urlsplit

import uvicorn


def _presence(name: str) -> str:
    value = os.getenv(name)
    return "set" if value else "missing"


def _database_summary() -> str:
    value = os.getenv("DATABASE_URL", "")
    if not value:
        return "missing"
    try:
        parts = urlsplit(value)
        return f"{parts.scheme}://{parts.hostname or 'unknown-host'}{parts.path or ''}"
    except Exception:
        return "set but unreadable"


def main() -> int:
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WEB_CONCURRENCY", "1"))

    print("Starting Rescue 1122 API", flush=True)
    print(f"Python: {sys.version.split()[0]}", flush=True)
    print(f"Working directory: {os.getcwd()}", flush=True)
    print(f"PORT: {port}", flush=True)
    print(f"WEB_CONCURRENCY: {workers}", flush=True)
    print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'development')}", flush=True)
    print(f"DATABASE_URL: {_database_summary()}", flush=True)
    print(f"SECRET_KEY: {_presence('SECRET_KEY')}", flush=True)
    print(f"FRONTEND_URL: {_presence('FRONTEND_URL')}", flush=True)
    print(f"ALLOWED_HOSTS: {_presence('ALLOWED_HOSTS')}", flush=True)

    try:
        import main as app_module
        assert app_module.app is not None
        print("Application import: ok", flush=True)
    except Exception:
        print("Application import failed:", flush=True)
        traceback.print_exc()
        return 1

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
