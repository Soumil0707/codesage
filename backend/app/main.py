"""CodeSage – AI Software Development Intelligence.

Main FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.database import async_engine, Base
import app.models  # noqa: F401
from app.api import auth, repositories, chat, review, interview, docs, analytics

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("codesage")


def _is_database_online() -> bool:
    """Non-blocking socket check to see if MySQL is accessible."""
    import socket
    try:
        host = async_engine.url.host or "127.0.0.1"
        port = async_engine.url.port or 3306
        with socket.create_connection((host, port), timeout=2.0):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("Starting CodeSage v%s", settings.APP_VERSION)
    if _is_database_online():
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Connected to MySQL: tables verified/created successfully.")
        except Exception as e:
            logger.warning("Database initialization notice: %s", str(e))
    else:
        logger.warning(
            "MySQL 8.x is not running on localhost:3306. "
            "CodeSage API server is starting in offline/docs mode. "
            "To connect database, start MySQL (or run 'docker compose up mysql')."
        )
    yield
    # Shutdown
    try:
        await async_engine.dispose()
    except Exception:
        pass
    logger.info("CodeSage shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Software Development Intelligence Platform",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware – strict origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=600,
)

# Custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Register API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(repositories.router, prefix="/api/repositories", tags=["Repositories"])
app.include_router(chat.router, prefix="/api/chat", tags=["RAG Chat"])
app.include_router(review.router, prefix="/api/review", tags=["Code Review"])
app.include_router(interview.router, prefix="/api/interview", tags=["Interview"])
app.include_router(docs.router, prefix="/api/docs-gen", tags=["Documentation"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
