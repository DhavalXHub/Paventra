"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.db.database import init_db
from app.api.v1.auth import router as auth_router
from app.api.v1.reports import router as reports_router
from app.api.v1.inspections import router as inspections_router
from app.api.v1.misc import (
    teams_router, notifications_router, analytics_router, audit_router
)

logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB. Shutdown: nothing needed for SQLite."""
    logger.info("Starting Paventra API...")
    # Ensure upload directories exist
    for subdir in ("reports", "completions", "inspections"):
        Path(settings.UPLOAD_DIR, subdir).mkdir(parents=True, exist_ok=True)
    # Create tables (idempotent; Alembic is preferred for production)
    await init_db()
    logger.info("Database ready")
    # Pre-warm CV model if enabled
    if settings.MODEL_ENABLED:
        from app.services.vision.inference import detector
        detector.is_available()
    # Pre-warm fuzzy engine
    from app.services.prioritization.fuzzy_engine import _engine
    _engine.initialize()
    logger.info("Paventra API ready")
    yield
    logger.info("Shutting down Paventra API")


app = FastAPI(
    title="Paventra API",
    version=settings.APP_VERSION,
    description="AI-Powered Road Damage Intelligence and Repair Management",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
PREFIX = "/api/v1"
app.include_router(auth_router, prefix=PREFIX)
app.include_router(reports_router, prefix=PREFIX)
app.include_router(inspections_router, prefix=PREFIX)
app.include_router(teams_router, prefix=PREFIX)
app.include_router(notifications_router, prefix=PREFIX)
app.include_router(analytics_router, prefix=PREFIX)
app.include_router(audit_router, prefix=PREFIX)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/ready")
async def ready():
    from app.db.database import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Database not ready: {exc}")


# Serve uploaded files (for development — use nginx/CDN in production)
uploads_path = Path(settings.UPLOAD_DIR)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")
