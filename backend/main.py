import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import inspect, text
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, test, admin, materials
from app.models import user  # ensure models are imported for table creation
from app.models.user import LearningMaterial, MasterTestPaper

logger = logging.getLogger(__name__)


def _question_bank_has_valid_column(sync_conn) -> bool:
    inspector = inspect(sync_conn)
    if "question_bank" not in inspector.get_table_names():
        return True
    return any(column["name"] == "is_valid" for column in inspector.get_columns("question_bank"))


async def ensure_question_bank_quality_column(conn) -> None:
    has_column = await conn.run_sync(_question_bank_has_valid_column)
    if has_column:
        return
    default_value = "1" if conn.dialect.name == "sqlite" else "TRUE"
    await conn.execute(text(f"ALTER TABLE question_bank ADD COLUMN is_valid BOOLEAN NOT NULL DEFAULT {default_value}"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT == "production":
        logger.info("Ensuring learning materials table exists")
        async with engine.begin() as conn:
            await conn.run_sync(LearningMaterial.__table__.create, checkfirst=True)
            await conn.run_sync(MasterTestPaper.__table__.create, checkfirst=True)
            await ensure_question_bank_quality_column(conn)
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await ensure_question_bank_quality_column(conn)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}))
app.add_middleware(SlowAPIMiddleware)

if settings.ENVIRONMENT == "production":
    allowed_hosts = [host.strip() for host in settings.ALLOWED_HOSTS.split(",") if host.strip()]
    if "*.onrender.com" not in allowed_hosts:
        allowed_hosts.append("*.onrender.com")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

frontend_origins = [origin.strip() for origin in settings.FRONTEND_URL.split(",") if origin.strip()]
for origin in ("http://localhost:5173", "http://localhost:3000"):
    if origin not in frontend_origins:
        frontend_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled application error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(test.router)
app.include_router(admin.router)
app.include_router(materials.router)


@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
