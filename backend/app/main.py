"""
KnowledgeHub — FastAPI Application Entry Point
===============================================
Defines the FastAPI app, lifespan (startup/shutdown), and all routes
for Milestone 0.

Routes:
  GET /         — redirect to /docs (developer convenience)
  GET /health   — structured health check (app + database)
"""

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import settings
from app.database import (
    check_database_connectivity,
    clear_pool,
    create_pool,
    set_pool,
)

# Record when the process started so /health can report uptime
_START_TIME = time.time()


# =============================================================================
# Lifespan — runs once at startup and once at shutdown
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """
    Manage resources that need to be created before requests are served
    and cleaned up when the server shuts down.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    print("[KnowledgeHub] Starting backend...")
    print(f"   Environment : {settings.app_env}")
    print(f"   Debug mode  : {settings.app_debug}")

    try:
        pool = await create_pool()
        set_pool(pool)
        print("[KnowledgeHub] Database pool created successfully.")
    except Exception as exc:  # noqa: BLE001
        # Log clearly but do not crash — /health will report the error
        print(f"[KnowledgeHub] WARNING: Database pool creation failed: {exc}")
        print("   The app will start, but /health will report DB as disconnected.")

    yield  # ← application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("[KnowledgeHub] Shutting down...")
    from app.database import _pool  # noqa: PLC0415

    if _pool is not None:
        await _pool.close()
        clear_pool()
        print("[KnowledgeHub] Database pool closed.")


# =============================================================================
# App instance
# =============================================================================

app = FastAPI(
    title="KnowledgeHub API",
    description="AI-powered personal knowledge platform — backend API.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# In development the Vite dev server runs on a different port (5173).
# Add production origin here when deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Routes
# =============================================================================


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root to interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    summary="Health Check",
    tags=["System"],
    response_model=dict[str, Any],
)
async def health() -> dict[str, Any]:
    """
    Return structured information about the application's current state.

    Checks:
    - Application is running
    - Uptime in seconds
    - Database connectivity
    - pgvector availability

    This endpoint is intentionally cheap and can be called frequently
    by monitoring tools, load balancers, or test suites.
    """
    db_status = await check_database_connectivity()

    uptime_seconds = round(time.time() - _START_TIME, 2)

    return {
        "status": "ok",
        "environment": settings.app_env,
        "uptime_seconds": uptime_seconds,
        "database": {
            "connected": db_status["connected"],
            "postgres_version": db_status["postgres_version"],
            "pgvector_version": db_status["pgvector_version"],
            "error": db_status["error"],
        },
    }
