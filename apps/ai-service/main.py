"""
SwipeHire AI Service — FastAPI entry point.
Runs on port 8000. Handles: auth, jobs, swipes, applications, profile, ML.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from database import engine
from models import User, UserProfile, Job, Swipe, Application  # noqa: F401 — ensures models registered
from routers import auth, jobs, swipes, profile, applications, auto_apply, payments, ai_features, gmail, push

log = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address)


# ─── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("SwipeHire AI service starting up")
    # Warm up ML model on startup to avoid cold-start on first request
    from ml.embeddings import _get_model
    _get_model()
    log.info("Embedding model loaded")

    # Initialise Meilisearch index
    try:
        from services.search import ensure_index
        await ensure_index()
        log.info("Meilisearch index ready")
    except Exception as e:
        log.warning("Meilisearch not available at startup: %s", e)

    # Initialise Qdrant collections
    try:
        from services.vector_store import ensure_collections
        await ensure_collections()
        log.info("Qdrant collections ready")
    except Exception as e:
        log.warning("Qdrant not available at startup (will retry on first request): %s", e)

    yield
    log.info("SwipeHire AI service shutting down")
    await engine.dispose()


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SwipeHire AI API",
    description="India-first AI-powered job discovery platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request logging middleware ────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(swipes.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(auto_apply.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(ai_features.router, prefix="/api/v1")
app.include_router(gmail.router, prefix="/api/v1")
app.include_router(push.router, prefix="/api/v1")


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "swipehire-ai"}


# ─── Global error handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
