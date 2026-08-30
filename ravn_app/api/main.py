"""
ravn_app/api/main.py — FastAPI application factory and entry point.

Run standalone (development):
    uvicorn ravn_app.api.main:app --reload --port 7842

Run as Tauri sidecar (production):
    The Tauri build bundles the PyInstaller-compiled executable.
    The executable calls serve() which blocks until SIGINT/SIGTERM.

Architecture:
    This file wires together the router modules and the WebSocket event bus.
    It does NOT contain business logic.  All media, library, and queue
    behaviour lives in ravn_app.core.

Port selection:
    Default: 7842  (chosen to avoid common dev-tool collisions)
    Override: set the RAVN_API_PORT environment variable.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ravn_app.api.routers import downloads, history, library, queue, settings, studio
from ravn_app.api.ws import event_bus
from ravn_app.api.ws import router as ws_router
from ravn_app.core.logging_config import setup_logging

logger = logging.getLogger(__name__)

DEFAULT_PORT = 7842


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background services on startup; tear them down on shutdown."""
    # Import here to avoid circular imports at module level
    from ravn_app.api.deps import _task_queue  # type: ignore[import]

    tq = _task_queue()
    port = getattr(app.state, "port", DEFAULT_PORT)
    logger.info("RAVN API server starting up (port=%s)", port)

    yield  # Application runs here

    logger.info("RAVN API server shutting down")
    tq.stop(wait=False)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title="RAVN API",
        description=(
            "Local HTTP/WebSocket transport layer for the RAVN desktop application.\n\n"
            "This API is consumed by the Tauri frontend and exposes the same core "
            "functionality available via the `ravn` CLI.  The backend remains "
            "completely UI-agnostic."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — the Tauri WebView origin is null/localhost; allow it in development.
    # In production the sidecar and the WebView run on the same machine so this
    # is a low-risk setting.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- HTTP routers ---
    app.include_router(downloads.router, prefix="/api/v1")
    app.include_router(queue.router,     prefix="/api/v1")
    app.include_router(history.router,   prefix="/api/v1")
    app.include_router(library.router,   prefix="/api/v1")
    app.include_router(settings.router,  prefix="/api/v1")
    app.include_router(studio.router,    prefix="/api/v1")


    # --- WebSocket ---
    app.include_router(ws_router)

    # --- Health / meta ---
    @app.get("/health", tags=["meta"], summary="Server and tool health check")
    @app.get("/api/v1/health", tags=["meta"], summary="Server and tool health check")
    async def health() -> Dict[str, Any]:
        from ravn_app.core.tool_health import get_tool_health_checker

        checker = get_tool_health_checker()
        tool_summary = checker.get_health_summary()
        return {
            "status": "ok",
            "ws_clients": event_bus.client_count,
            "tools": tool_summary,
        }

    @app.get("/", tags=["meta"], include_in_schema=False)
    async def root() -> Dict[str, str]:
        return {"service": "RAVN API", "docs": "/docs"}

    return app


# Module-level app instance (uvicorn uses this)
app = create_app()


# ---------------------------------------------------------------------------
# CLI entry point (used by PyInstaller sidecar executable)
# ---------------------------------------------------------------------------

def serve(port: int | None = None, host: str = "127.0.0.1") -> None:
    """
    Start the uvicorn server synchronously.

    Called by the PyInstaller entry point when RAVN runs as a Tauri sidecar.
    The Tauri process captures stdout to discover which port the server bound
    on (useful when port=0 / OS-assigned).
    """
    setup_logging()

    resolved_port = port or int(os.environ.get("RAVN_API_PORT", DEFAULT_PORT))

    print(f"RAVN_API_PORT={resolved_port}", flush=True)  # Tauri sidecar reads this
    logger.info("Starting RAVN API on %s:%s", host, resolved_port)

    uvicorn.run(
        "ravn_app.api.main:app",
        host=host,
        port=resolved_port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    serve(port=port_arg)
